from __future__ import annotations

import asyncio
import json
import os
import random
from typing import Any

import httpx

from omo.contracts import ChatRequest, OmoError
from omo.registry import ModelEntry


class ProviderError(OmoError):
    def __init__(self, code: str, attempts: int) -> None:
        super().__init__(code, 502)
        self.attempts = attempts


class OpenAIProvider:
    """Pooled non-streaming upstream adapter; bounded delivery streaming at API.

    Only explicit 429 rejections are retried. Ambiguous transport/5xx outcomes
    are not replayed because an inference may already have been billed.
    """

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(10, connect=3),
            follow_redirects=False,
            trust_env=False,
            limits=httpx.Limits(max_connections=8, max_keepalive_connections=4),
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def complete(self, entry: ModelEntry, request: ChatRequest) -> dict[str, Any]:
        key = os.environ.get(entry.key_env)
        if not key:
            raise ProviderError("provider_credentials_missing", 0)
        headers = {
            "Authorization": "Bearer " + key,
            "Accept": "application/json",
            "Accept-Encoding": "identity",
        }
        if entry.provider == "openrouter":
            headers["X-Title"] = "Open Model Orchestrator"
        payload = {
            "model": entry.upstream_model,
            "messages": [m.model_dump() for m in request.messages],
            "max_tokens": request.max_tokens,
            "stream": False,
        }
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
                    codes = {
                        400: "provider_bad_request",
                        401: "provider_authentication",
                        403: "provider_authorization",
                        402: "provider_quota",
                        404: "provider_model_unavailable",
                    }
                    if response.status_code != 200:
                        raise ProviderError(
                            codes.get(response.status_code, "provider_unavailable"), attempt
                        )
                    body = bytearray()
                    async for chunk in response.aiter_bytes(4096):
                        body.extend(chunk)
                        if len(body) > 65536:
                            raise ProviderError("provider_response_too_large", attempt)
                result = json.loads(body)
                choices = result["choices"]
                if len(choices) != 1 or choices[0]["message"].get("tool_calls"):
                    raise ProviderError("provider_tools_unsupported", attempt)
                message = choices[0]["message"]
                text = message["content"]
                if message.get("role") != "assistant" or not isinstance(text, str) or not text:
                    raise ValueError("invalid message")
                if len(text.encode()) > 32768:
                    raise ProviderError("provider_response_too_large", attempt)
                usage = result.get("usage")
                if usage is not None:
                    if not isinstance(usage, dict) or any(
                        type(usage.get(k)) is not int or usage[k] < 0
                        for k in ("prompt_tokens", "completion_tokens", "total_tokens")
                    ):
                        raise ValueError("invalid usage")
                    usage = {
                        k: usage[k] for k in ("prompt_tokens", "completion_tokens", "total_tokens")
                    }
                return {
                    "text": text,
                    "usage": usage,
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
