import json

import pytest

from omo.inference_worker import _parse_request


def valid_request(**updates):
    request = {
        "messages": [{"role": "user", "content": "hello"}],
        "max_tokens": 32,
    }
    request.update(updates)
    return json.dumps(request)


def test_worker_protocol_accepts_only_bounded_messages():
    assert _parse_request(valid_request())["max_tokens"] == 32
    assert _parse_request(valid_request(messages=[{"role": "tool", "content": "x"}])) is None
    assert (
        _parse_request(valid_request(messages=[{"role": "user", "content": "x", "url": "evil"}]))
        is None
    )
    assert (
        _parse_request(valid_request(messages=[{"role": "user", "content": "x" * 60001}])) is None
    )


@pytest.mark.parametrize(
    "line",
    [
        "",
        "not-json",
        json.dumps({"messages": [], "max_tokens": 32}),
        valid_request(max_tokens=True),
        valid_request(schema="not-an-object"),
        valid_request(count_only=1),
    ],
)
def test_worker_protocol_rejects_malformed_or_wrongly_typed_input(line):
    assert _parse_request(line) is None
