"""Bounded serialization and strict parsing for model routing proposals."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any, Final

from .contracts import Message, Proposal

CLASSIFICATION_OBJECTIVE: Final = "omo-routing-classification-v1"
MODEL_ACTIONS: Final = frozenset({"external_model", "helper", "clarify"})
MAX_MESSAGES: Final = 24
MAX_SERIALIZED_BYTES: Final = 16000
MAX_PROPOSAL_BYTES: Final = 16000


def serialize_messages(messages: Sequence[Message]) -> str:
    """Serialize the complete ordered conversation for classification."""
    if not 1 <= len(messages) <= MAX_MESSAGES:
        raise ValueError("conversation must contain between 1 and 24 messages")
    if messages[-1].role != "user":
        raise ValueError("the final message must be a user message")
    for index, message in enumerate(messages):
        if message.role == "system" and index != 0:
            raise ValueError("system role is only supported at conversation start")

    serialized = json.dumps(
        [message.model_dump(mode="json") for message in messages],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    if len(serialized.encode("utf-8")) > MAX_SERIALIZED_BYTES:
        raise ValueError("serialized conversation exceeds byte budget")
    return serialized


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def parse_proposal(raw: str) -> Proposal:
    """Parse one strict Proposal object and reject ambiguous JSON."""
    if not raw or len(raw.encode("utf-8")) > MAX_PROPOSAL_BYTES:
        raise ValueError("proposal exceeds byte budget")
    try:
        payload = json.loads(raw, object_pairs_hook=_object_without_duplicates)
        if not isinstance(payload, dict):
            raise ValueError("proposal must be a JSON object")
        return Proposal.model_validate(payload)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("invalid classification proposal") from exc
