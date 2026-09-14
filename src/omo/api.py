from __future__ import annotations

import asyncio
import hmac
import json
import logging
import time
import uuid
from collections import Counter, deque
from collections.abc import AsyncIterator, Callable, Coroutine
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from omo.access import AccessStore, BudgetLedger, Caller
from omo.config import Settings
from omo.contracts import ChatRequest, Decision, OmoError
from omo.inference import LlamaModel
from omo.provider import OpenAIProvider, ProviderError
from omo.registry import RegistryStore
from omo.sandbox import MontySandbox
from omo.service import Orchestrator

LOGGER = logging.getLogger("omo.operations")


class Guard:
    def __init__(
        self, app: ASGIApp, settings: Settings, access_store: AccessStore | None = None
    ) -> None:
        self.app, self.settings, self.access_store = app, settings, access_store
        self.active = 0
        self.recent: deque[float] = deque()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] in {"/health/live", "/health/ready"}:
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers", []))
        expected = self.settings.api_key
        caller: Caller | None = None
        if self.access_store:
            prefix = b"Bearer "
            authorization = headers.get(b"authorization", b"")
            token = (
                authorization[len(prefix) :].decode(errors="ignore")
                if authorization.startswith(prefix)
                else ""
            )
            caller = self.access_store.authenticate(token)
            ok = caller is not None
        elif expected:
            ok = hmac.compare_digest(
                headers.get(b"authorization", b""),
                ("Bearer " + expected.get_secret_value()).encode(),
            )
        else:
            ok = scope.get("client", ("",))[0] in {"127.0.0.1", "::1"}
        if not ok:
            await JSONResponse({"error": {"code": "unauthorized"}}, status_code=401)(
                scope, receive, send
            )
            return
        if headers.get(b"content-encoding", b"identity") != b"identity":
            await JSONResponse(
                {"error": {"code": "content_encoding_unsupported"}}, status_code=415
            )(scope, receive, send)
            return
        now = time.monotonic()
        while self.recent and self.recent[0] < now - 60:
            self.recent.popleft()
        if (
            self.active >= self.settings.max_inflight
            or len(self.recent) >= self.settings.requests_per_minute
        ):
            await JSONResponse({"error": {"code": "busy"}}, status_code=429)(scope, receive, send)
            return
        self.active += 1
        self.recent.append(now)
        try:
            body = bytearray()
            async with asyncio.timeout(5):
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    body.extend(message.get("body", b""))
                    if len(body) > 32768:
                        await JSONResponse(
                            {"error": {"code": "request_too_large"}}, status_code=413
                        )(scope, receive, send)
                        return
                    if not message.get("more_body", False):
                        break
            delivered = False

            async def bounded_receive() -> Message:
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()

            scope.setdefault("state", {})["caller"] = (
                caller.id if caller else ("configured-api-key" if expected else "loopback-dev")
            )
            if caller:
                scope["state"]["caller_policy"] = caller
            scope["state"]["request_id"] = uuid.uuid4().hex
            await self.app(scope, bounded_receive, send)
        except TimeoutError:
            await JSONResponse({"error": {"code": "request_body_timeout"}}, status_code=408)(
                scope, receive, send
            )
        finally:
            self.active -= 1


async def cancellable(
    request: Request, operation: Callable[[], Coroutine[Any, Any, Any]], seconds: float
) -> Any:
    stop_watcher = asyncio.Event()

    async def disconnected() -> None:
        while not stop_watcher.is_set() and not await request.is_disconnected():  # noqa: ASYNC110 - ASGI polling interface
            await asyncio.sleep(0.05)

    task = asyncio.create_task(operation())
    watcher = asyncio.create_task(disconnected())
    try:
        async with asyncio.timeout(seconds):
            done, _ = await asyncio.wait({task, watcher}, return_when=asyncio.FIRST_COMPLETED)
            if task in done:
                return await task
            raise OmoError("client_disconnected", 499)
    except TimeoutError as exc:
        raise OmoError("request_deadline", 504) from exc
    finally:
        stop_watcher.set()
        for item in (task, watcher):
            if not item.done():
                item.cancel()
        await asyncio.gather(task, watcher, return_exceptions=True)


def create_app(settings: Settings | None = None, service: Orchestrator | None = None) -> FastAPI:
    settings = settings or Settings()
    counters: Counter[str] = Counter()
    access_store = (
        AccessStore.read(settings.access_policy_path) if settings.access_policy_path else None
    )
    budget_ledger = BudgetLedger()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if service is not None:
            app.state.service = service
            yield
            return
        model = LlamaModel(settings)
        provider = OpenAIProvider()
        try:
            await model.start()
            registry = RegistryStore(
                RegistryStore.read(settings.registry_path), source_path=settings.registry_path
            )
            async with MontySandbox(settings.sandbox_enabled) as sandbox:
                if settings.sandbox_enabled:
                    smoke = await sandbox.execute("1 + 1", {})
                    if smoke.value != 2:
                        raise RuntimeError("sandbox startup check failed")
                app.state.service = Orchestrator(
                    settings, model, registry, sandbox, provider, budget_ledger
                )
                yield
        finally:
            await provider.close()
            await model.close()

    app = FastAPI(
        title="Open Model Orchestrator",
        version="0.1.0.dev0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.add_middleware(Guard, settings=settings, access_store=access_store)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Pydantic's default error includes user input; expose only safe locations/types.
        errors = [{"loc": e["loc"], "type": e["type"]} for e in exc.errors()]
        return JSONResponse(
            {"error": {"code": "invalid_request", "details": errors}}, status_code=422
        )

    @app.exception_handler(OmoError)
    async def domain_error(request: Request, exc: OmoError) -> JSONResponse:
        counters["error"] += 1
        attempts = exc.attempts if isinstance(exc, ProviderError) else 0
        return JSONResponse(
            {"error": {"code": exc.code, "provider_attempts": attempts}}, status_code=exc.status
        )

    @app.get("/health/live")
    async def live() -> dict[str, str]:
        return {"status": "alive"}

    @app.get("/health/ready")
    async def ready(request: Request) -> JSONResponse:
        active = getattr(request.app.state, "service", None)
        ok = bool(active and active.model.ready)
        return JSONResponse(
            {"status": "ready" if ok else "not_ready"}, status_code=200 if ok else 503
        )

    @app.get("/admin/registry/status")
    async def registry_status(request: Request) -> dict[str, object]:
        active: Orchestrator = request.app.state.service
        return active.registry.status(settings.registry_max_age_seconds)

    @app.post("/admin/registry/reload")
    async def registry_reload(request: Request) -> JSONResponse:
        if not settings.registry_reload_enabled:
            return JSONResponse({"error": {"code": "registry_reload_disabled"}}, status_code=404)
        caller = getattr(request.state, "caller_policy", None)
        if access_store is not None and (caller is None or caller.role != "admin"):
            return JSONResponse({"error": {"code": "admin_required"}}, status_code=403)
        active: Orchestrator = request.app.state.service
        if not active.registry.try_reload(settings.registry_path):
            return JSONResponse(
                {
                    "error": {"code": "registry_reload_failed"},
                    "registry": active.registry.status(settings.registry_max_age_seconds),
                },
                status_code=422,
            )
        return JSONResponse(active.registry.status(settings.registry_max_age_seconds))

    @app.get("/v1/models")
    async def models(request: Request) -> dict[str, Any]:
        return {"object": "list", "data": [{"id": "omo", "object": "model", "owned_by": "local"}]}

    @app.get("/metrics")
    async def metrics() -> dict[str, int]:
        return dict(counters)

    @app.post("/v1/route")
    async def route(body: ChatRequest, request: Request) -> dict[str, Any]:
        active: Orchestrator = request.app.state.service
        snapshot = active.registry.snapshot
        caller = getattr(request.state, "caller_policy", None)
        decision: Decision = await cancellable(
            request, lambda: active.route(body, snapshot, caller), settings.deadline_seconds
        )
        return decision.model_dump(exclude={"helper"})

    @app.post("/v1/chat/completions")
    async def chat(body: ChatRequest, request: Request) -> Any:
        active: Orchestrator = request.app.state.service
        caller = getattr(request.state, "caller_policy", None)
        result = await cancellable(
            request, lambda: active.chat(body, caller), settings.deadline_seconds
        )
        request_id = request.state.request_id
        result.update(
            {
                "id": "chatcmpl-" + request_id,
                "object": "chat.completion",
                "created": int(time.time()),
            }
        )
        counters[result["omo"]["action"]] += 1
        LOGGER.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "action": result["omo"]["action"],
                    "status": result["omo"]["status"],
                    "total_ms": result["omo"]["total_ms"],
                }
            )
        )
        if not body.stream:
            return result

        async def chunks() -> AsyncIterator[str]:
            # Buffered delivery streaming: all computation/validation precedes
            # the first visible chunk, so there is no provider splicing.
            base = {k: result[k] for k in ("id", "created", "model")}
            base["object"] = "chat.completion.chunk"
            text = result["choices"][0]["message"]["content"]
            async with asyncio.timeout(5):
                for start in range(0, len(text), 256):
                    if await request.is_disconnected():
                        return
                    event = {
                        **base,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": text[start : start + 256]},
                                "finish_reason": None,
                            }
                        ],
                    }
                    yield "data: " + json.dumps(event) + "\n\n"
                yield (
                    "data: "
                    + json.dumps(
                        {
                            **base,
                            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                            "usage": result["usage"],
                            "omo": result["omo"],
                        }
                    )
                    + "\n\n"
                )
                yield "data: [DONE]\n\n"

        return StreamingResponse(
            chunks(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )

    return app
