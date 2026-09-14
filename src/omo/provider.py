from __future__ import annotations

import asyncio
import json
import os
import random
from collections.abc import AsyncIterator
from typing import Any

import httpx

from omo.contracts import ChatRequest, OmoError
from omo.registry import ModelEntry


class ProviderError(OmoError):
    def __init__(self, code: str, attempts: int) -> None:
        super().__init__(code, 502)
        self.attempts = attempts


class OpenAIProvider:
    """Pooled OpenAI-compatible adapter with bounded upstream SSE parsing.

    Only explicit 429 rejections are retried. Ambiguous transport/5xx outcomes
    are not replayed because an inference may already have been billed.
    """

    MAX_RESPONSE_BYTES = 65536
    MAX_TEXT_BYTES = 32768
    MAX_EVENT_BYTES = 16384

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(10, connect=3),
            follow_redirects=False,
            trust_env=False,
            limits=httpx.Limits(max_connections=8, max_keepalive_connections=4),
        )

    async def close(self) -> None:
        await self.client.aclose()

    @staticmethod
    def _usage(value: Any) -> dict[str, int] | None:
        if value is None:
            return None
        if not isinstance(value, dict) or any(
            type(value.get(k)) is not int or value[k] < 0
            for k in ("prompt_tokens", "completion_tokens", "total_tokens")
        ):
            raise ValueError("invalid usage")
        return {k: value[k] for k in ("prompt_tokens", "completion_tokens", "total_tokens")}

    @staticmethod
    def _status_code(status: int) -> str:
        return {
            400: "provider_bad_request",
            401: "provider_authentication",
            402: "provider_quota",
            403: "provider_authorization",
            404: "provider_model_unavailable",
        }.get(status, "provider_unavailable")

    def _request_parts(
        self, entry: ModelEntry, request: ChatRequest, stream: bool
    ) -> tuple[dict[str, str], dict[str, Any]]:
        key = os.environ.get(entry.key_env)
        if not key:
            raise ProviderError("provider_credentials_missing", 0)
        headers = {
            "Authorization": "Bearer " + key,
            "Accept": "text/event-stream" if stream else "application/json",
            "Accept-Encoding": "identity",
        }
        if entry.provider == "openrouter":
            headers["X-Title"] = "Open Model Orchestrator"
        payload = {
            "model": entry.upstream_model,
            "messages": [m.model_dump() for m in request.messages],
            "max_tokens": request.max_tokens,
            "stream": stream,
        }
        return headers, payload

    async def complete(self, entry: ModelEntry, request: ChatRequest) -> dict[str, Any]:
        headers, payload = self._request_parts(entry, request, False)
        for attempt in range(1, 3):
            try:
                async with self.client.stream(
                    "POST",
                    entry.base_url.rstrip("/") + "/chat/completions",
                    headers=headers,
                    json=payload,
                ) as response:
                    if response.status_code == 429:
                        if attempt == 2:
                            raise ProviderError("provider_rate_limited", attempt)
                        await asyncio.sleep(random.uniform(0.05, 0.15))
                        continue
                    if response.status_code != 200:
                        raise ProviderError(self._status_code(response.status_code), attempt)
                    body = bytearray()
                    async for chunk in response.aiter_bytes(4096):
                        body.extend(chunk)
                        if len(body) > self.MAX_RESPONSE_BYTES:
                            raise ProviderError("provider_response_too_large", attempt)
                result = json.loads(body)
                choices = result["choices"]
                if len(choices) != 1 or choices[0]["message"].get("tool_calls"):
                    raise ProviderError("provider_tools_unsupported", attempt)
                message = choices[0]["message"]
                text = message["content"]
                if message.get("role") != "assistant" or not isinstance(text, str) or not text:
                    raise ValueError("invalid message")
                if len(text.encode()) > self.MAX_TEXT_BYTES:
                    raise ProviderError("provider_response_too_large", attempt)
                return {
                    "text": text,
                    "usage": self._usage(result.get("usage")),
                    "attempts": attempt,
                    "finish_reason": choices[0].get("finish_reason", "stop"),
                }
            except ProviderError:
                raise
            except httpx.TimeoutException as exc:
                raise ProviderError("provider_timeout", attempt) from exc
            except httpx.HTTPError as exc:
                raise ProviderError("provider_transport", attempt) from exc
            except (ValueError, TypeError, KeyError, IndexError) as exc:
                raise ProviderError("provider_invalid_response", attempt) from exc
        raise ProviderError("provider_unavailable", 2)

    @staticmethod
    def _stream_chunk(payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict) or not isinstance(payload.get("choices"), list):
            raise ValueError("invalid stream chunk")
        choices = payload["choices"]
        if len(choices) != 1 or not isinstance(choices[0], dict):
            raise ValueError("invalid stream choices")
        choice = choices[0]
        delta = choice.get("delta")
        if not isinstance(delta, dict) or delta.get("tool_calls") is not None:
            raise ValueError("unsupported stream tool call")
        text = delta.get("content", "")
        if not isinstance(text, str):
            raise ValueError("invalid stream content")
        finish_reason = choice.get("finish_reason")
        if finish_reason is not None and not isinstance(finish_reason, str):
            raise ValueError("invalid stream finish reason")
        return {
            "text": text,
            "finish_reason": finish_reason,
            "usage": OpenAIProvider._usage(payload.get("usage")),
        }

    async def stream(
        self, entry: ModelEntry, request: ChatRequest
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield validated upstream deltas; only a pre-data 429 may retry.

        The parser requires the terminal DONE marker, bounds both the response
        and each event, and never returns partial output as a successful result.
        """
        headers, payload = self._request_parts(entry, request, True)
        for attempt in range(1, 3):
            saw_data = False
            total_bytes = 0
            text_bytes = 0
            event_data: list[str] = []
            try:
                async with self.client.stream(
                    "POST",
                    entry.base_url.rstrip("/") + "/chat/completions",
                    headers=headers,
                    json=payload,
                ) as response:
                    if response.status_code == 429:
                        if attempt == 2:
                            raise ProviderError("provider_rate_limited", attempt)
                        await asyncio.sleep(random.uniform(0.05, 0.15))
                        continue
                    if response.status_code != 200:
                        raise ProviderError(self._status_code(response.status_code), attempt)
                    async for line in response.aiter_lines():
                        total_bytes += len(line.encode()) + 1
                        if total_bytes > self.MAX_RESPONSE_BYTES:
                            raise ProviderError("provider_response_too_large", attempt)
                        if line == "":
                            if not event_data:
                                continue
                            raw = "\n".join(event_data)
                            event_data = []
                            if len(raw.encode()) > self.MAX_EVENT_BYTES:
                                raise ProviderError("provider_event_too_large", attempt)
                            if raw == "[DONE]":
                                return
                            event = self._stream_chunk(json.loads(raw))
                            saw_data = True
                            text_bytes += len(event["text"].encode())
                            if text_bytes > self.MAX_TEXT_BYTES:
                                raise ProviderError("provider_response_too_large", attempt)
                            event["attempts"] = attempt
                            yield event
                        elif line.startswith("data:"):
                            event_data.append(line[5:].lstrip())
                    if event_data:
                        raw = "\n".join(event_data)
                        if raw == "[DONE]":
                            return
                    raise ProviderError(
                        "provider_stream_incomplete" if saw_data else "provider_stream_no_data",
                        attempt,
                    )
            except ProviderError:
                raise
            except asyncio.CancelledError:
                raise
            except httpx.TimeoutException as exc:
                raise ProviderError("provider_timeout", attempt) from exc
            except httpx.HTTPError as exc:
                raise ProviderError("provider_transport", attempt) from exc
            except (ValueError, TypeError, KeyError, IndexError, UnicodeError) as exc:
                raise ProviderError("provider_invalid_response", attempt) from exc
        raise ProviderError("provider_unavailable", 2)

    async def collect_stream(self, entry: ModelEntry, request: ChatRequest) -> dict[str, Any]:
        """Collect a validated stream for the service's buffered response path."""
        parts: list[str] = []
        usage: dict[str, int] | None = None
        finish_reason: str | None = None
        attempts = 0
        async for event in self.stream(entry, request):
            parts.append(event["text"])
            usage = event["usage"] or usage
            finish_reason = event["finish_reason"] or finish_reason
            attempts = event["attempts"]
        text = "".join(parts)
        if not text:
            raise ProviderError("provider_empty_response", attempts)
        return {
            "text": text,
            "usage": usage,
            "attempts": attempts,
            "finish_reason": finish_reason or "stop",
        }
