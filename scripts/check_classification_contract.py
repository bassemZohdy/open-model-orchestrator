"""Validate the OMO-012 proposal/label contract and policy boundary."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from omo.contracts import Proposal  # noqa: E402

CONFIG = ROOT / "config/classification.yaml"
MODEL_ACTIONS = {"external_model", "helper", "clarify"}
MODEL_CAPABILITIES = {"text", "coding", "current_information"}
DETERMINISTIC_ACTIONS = {"local_answer", "reject"}
REQUIRED_POLICY_OWNERS = {
    "target_eligibility",
    "authorization",
    "policy_denials",
    "execution",
}
REQUIRED_INVALID_EXAMPLES = {
    "malformed_json",
    "duplicate_keys",
    "extra_field",
    "unknown_action",
    "unknown_capability",
    "helper_without_typed_arguments",
    "external_model_with_helper_arguments",
    "ambiguous_reference",
    "missing_final_user_turn",
}


def _string_set(value: Any, field: str) -> set[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{field} must be a list of strings")
    return set(value)


def validate(path: Path = CONFIG) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != "1":
        raise ValueError("unsupported classification contract")

    if data.get("objective") != "omo-routing-classification-v1":
        raise ValueError("classification objective is not pinned")

    model_output = data.get("model_output")
    if not isinstance(model_output, dict):
        raise ValueError("model_output section is required")
    if model_output.get("kind") != "proposal" or model_output.get("schema") != "Proposal":
        raise ValueError("the model must emit Proposal objects")
    if _string_set(model_output.get("actions"), "model actions") != MODEL_ACTIONS:
        raise ValueError("model action labels are incomplete or over-broad")
    if _string_set(model_output.get("capabilities"), "capabilities") != MODEL_CAPABILITIES:
        raise ValueError("capability labels are incomplete")
    if model_output.get("includes_typed_helper_arguments") is not True:
        raise ValueError("helper proposals must carry typed arguments")

    boundary = data.get("deterministic_boundary")
    if not isinstance(boundary, dict):
        raise ValueError("deterministic boundary is required")
    if _string_set(boundary.get("actions"), "deterministic actions") != DETERMINISTIC_ACTIONS:
        raise ValueError("local_answer and reject must remain deterministic")
    if boundary.get("model_output_is_authoritative") is not False:
        raise ValueError("model output cannot authorize requests")
    if _string_set(boundary.get("owns"), "policy owners") != REQUIRED_POLICY_OWNERS:
        raise ValueError("deterministic policy ownership is incomplete")

    multi_turn = data.get("multi_turn")
    if not isinstance(multi_turn, dict):
        raise ValueError("multi-turn serialization is required")
    if multi_turn.get("serialization") != "ordered-json-messages-v1":
        raise ValueError("multi-turn serialization is not pinned")
    for field in ("include_roles", "preserve_order", "preserve_system_message"):
        if multi_turn.get(field) is not True:
            raise ValueError(f"multi-turn field {field} must be preserved")
    if multi_turn.get("max_messages") != 24:
        raise ValueError("multi-turn message bound must match the request contract")

    if _string_set(data.get("invalid_examples"), "invalid examples") != REQUIRED_INVALID_EXAMPLES:
        raise ValueError("invalid and ambiguous examples are incomplete")

    separation = data.get("record_separation")
    if not isinstance(separation, dict):
        raise ValueError("training record separation is required")
    if _string_set(
        separation.get("classification_expected_actions"), "classification actions"
    ) != MODEL_ACTIONS:
        raise ValueError("classification records must target model proposal actions")
    if _string_set(separation.get("local_answer_expected_actions"), "local actions") != {
        "local_answer"
    }:
        raise ValueError("local-answer records must remain separately labeled")
    if separation.get("local_answer_records_in_classification_training") is not False:
        raise ValueError("local-answer records cannot enter classification training")

    training = data.get("training")
    if not isinstance(training, dict):
        raise ValueError("training status is required")
    if training.get("enabled") is not False or training.get("execution") != "dry-run-only":
        raise ValueError("classification training must remain disabled")
    if training.get("max_cost_usd") != 0:
        raise ValueError("classification contract must remain zero-cost")

    examples = (
        {"schema_version": "1", "action": "external_model", "capability": "text"},
        {"schema_version": "1", "action": "clarify", "capability": "text"},
        {
            "schema_version": "1",
            "action": "helper",
            "capability": "text",
            "helper": {"id": "even_squares", "values": [2, 4]},
        },
    )
    for example in examples:
        Proposal.model_validate(example)

    invalid = (
        {"schema_version": "1", "action": "helper", "capability": "text"},
        {
            "schema_version": "1",
            "action": "external_model",
            "capability": "text",
            "helper": {"id": "even_squares", "values": [2]},
        },
        {"schema_version": "1", "action": "unknown", "capability": "text"},
        {"schema_version": "1", "action": "clarify", "capability": "text", "extra": True},
    )
    for example in invalid:
        try:
            Proposal.model_validate(example)
        except ValueError:
            continue
        raise ValueError("invalid Proposal example was accepted")

    return data


if __name__ == "__main__":
    validate()
    print("OMO classification contract passed")
