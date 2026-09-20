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


async def test_response_limit_is_checked_before_append(entry, request_factory, monkeypatch):
    body = b"x" * (OpenAIProvider.MAX_RESPONSE_BYTES + 1)

    with pytest.raises(ProviderError, match="provider_response_too_large"):
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


def sse(*events: str) -> bytes:
    return ("".join("data: " + event + "\n\n" for event in events)).encode()


async def test_stream_parser_collects_deltas_and_usage(entry, request_factory, monkeypatch):
    monkeypatch.setenv(entry.key_env, "test-secret")
    body = sse(
        json.dumps({"choices": [{"delta": {"role": "assistant"}, "finish_reason": None}]}),
        json.dumps({"choices": [{"delta": {"content": "hello "}, "finish_reason": None}]}),
        json.dumps(
            {
                "choices": [{"delta": {"content": "world"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6},
            }
        ),
        "[DONE]",
    )

    def handler(outgoing):
        assert json.loads(outgoing.content)["stream"] is True
        return httpx.Response(200, content=body, headers={"Content-Type": "text/event-stream"})

    provider = OpenAIProvider(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    try:
        result = await provider.collect_stream(entry, request_factory())
    finally:
        await provider.close()
    assert result == {
        "text": "hello world",
        "usage": {"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6},
        "attempts": 1,
        "finish_reason": "stop",
    }


async def test_stream_rate_limit_retries_before_first_event(entry, request_factory, monkeypatch):
    monkeypatch.setenv(entry.key_env, "test-secret")
    seen = []

    def handler(outgoing):
        seen.append(outgoing)
        if len(seen) == 1:
            return httpx.Response(429)
        return httpx.Response(
            200,
            content=sse(
                json.dumps({"choices": [{"delta": {"content": "ok"}, "finish_reason": "stop"}]}),
                "[DONE]",
            ),
            headers={"Content-Type": "text/event-stream"},
        )

    provider = OpenAIProvider(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    try:
        result = await provider.collect_stream(entry, request_factory())
    finally:
        await provider.close()
    assert result["text"] == "ok"
    assert result["attempts"] == 2
    assert len(seen) == 2


async def test_stream_midstream_failure_is_not_replayed(entry, request_factory, monkeypatch):
    monkeypatch.setenv(entry.key_env, "test-secret")
    seen = []

    async def handler(outgoing):
        seen.append(outgoing)
        if len(seen) == 1:
            return httpx.Response(
                200,
                content=sse(
                    json.dumps({"choices": [{"delta": {"content": "partial"}}]}),
                ),
                headers={"Content-Type": "text/event-stream"},
            )
        return httpx.Response(500)

    provider = OpenAIProvider(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    try:
        with pytest.raises(ProviderError, match="provider_stream_incomplete"):
            await provider.collect_stream(entry, request_factory())
    finally:
        await provider.close()
    assert len(seen) == 1


async def test_stream_cancellation_closes_request_without_retry(
    entry, request_factory, monkeypatch
):
    monkeypatch.setenv(entry.key_env, "test-secret")
    started = asyncio.Event()
    stopped = asyncio.Event()
    seen = []

    async def handler(outgoing):
        seen.append(outgoing)
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            stopped.set()

    provider = OpenAIProvider(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    task = asyncio.create_task(provider.collect_stream(entry, request_factory()))
    await started.wait()
    task.cancel()
    try:
        with pytest.raises(asyncio.CancelledError):
            await task
    finally:
        await provider.close()
    assert stopped.is_set()
    assert len(seen) == 1


@pytest.mark.parametrize(
    "body,code",
    [
        (
            sse(json.dumps({"choices": [{"delta": {"tool_calls": []}}]}), "[DONE]"),
            "provider_invalid_response",
        ),
        (sse(json.dumps({"choices": [{"delta": {"content": "x"}}]})), "provider_stream_incomplete"),
        (sse("x" * 20000, "[DONE]"), "provider_event_too_large"),
    ],
)
async def test_stream_rejects_unsafe_or_incomplete_events(
    entry, request_factory, monkeypatch, body, code
):
    monkeypatch.setenv(entry.key_env, "test-secret")
    provider = OpenAIProvider(
        httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda outgoing: httpx.Response(
                    200, content=body, headers={"Content-Type": "text/event-stream"}
                )
            )
        )
    )
    try:
        with pytest.raises(ProviderError, match=code):
            await provider.collect_stream(entry, request_factory())
    finally:
        await provider.close()
