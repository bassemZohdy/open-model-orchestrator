import asyncio
import json

import httpx
import pytest

from omo.provider import OpenAIProvider, ProviderError


async def call(entry, request, handler, monkeypatch):
    monkeypatch.setenv(entry.key_env, "test-secret")
    p = OpenAIProvider(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    try:
        return await p.complete(entry, request)
    finally:
        await p.close()


@pytest.mark.parametrize(
    "status,code",
    [
        (400, "provider_bad_request"),
        (401, "provider_authentication"),
        (402, "provider_quota"),
        (403, "provider_authorization"),
        (404, "provider_model_unavailable"),
        (500, "provider_unavailable"),
        (302, "provider_unavailable"),
    ],
)
async def test_provider_statuses(entry, request_factory, monkeypatch, status, code):
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(status, headers={"Location": "https://evil.example"})

    with pytest.raises(ProviderError) as error:
        await call(entry, request_factory(), handler, monkeypatch)
    assert error.value.code == code
    assert len(seen) == 1
    assert error.value.attempts == 1


async def test_rate_limit_attempt_bound(entry, request_factory, monkeypatch):
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(429)

    with pytest.raises(ProviderError) as error:
        await call(entry, request_factory(), handler, monkeypatch)
    assert len(seen) == error.value.attempts == 2


async def test_context_roles_and_tool_suggestions(entry, request_factory, monkeypatch):
    request = request_factory()

    def handler(outgoing):
        assert json.loads(outgoing.content)["messages"] == [
            m.model_dump() for m in request.messages
        ]
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "tool_calls": [{"function": {"name": "shell", "arguments": "id"}}],
                        }
                    }
                ]
            },
        )

    with pytest.raises(ProviderError, match="provider_tools_unsupported"):
        await call(entry, request, handler, monkeypatch)


@pytest.mark.parametrize("body", [b"no json", b"{}", b"x" * 70000])
async def test_invalid_or_large_response(entry, request_factory, monkeypatch, body):
    with pytest.raises(ProviderError):
        await call(
            entry, request_factory(), lambda r: httpx.Response(200, content=body), monkeypatch
        )


async def test_timeout_not_replayed(entry, request_factory, monkeypatch):
    seen = []

    def handler(request):
        seen.append(request)
        raise httpx.ReadTimeout("contains-sensitive-data")

    with pytest.raises(ProviderError) as error:
        await call(entry, request_factory(), handler, monkeypatch)
    assert error.value.code == "provider_timeout"
    assert len(seen) == 1
    assert "sensitive" not in str(error.value)


async def test_provider_cancellation(entry, request_factory, monkeypatch):
    started = asyncio.Event()
    stopped = asyncio.Event()

    async def handler(request):
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            stopped.set()

    task = asyncio.create_task(call(entry, request_factory(), handler, monkeypatch))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert stopped.is_set()
