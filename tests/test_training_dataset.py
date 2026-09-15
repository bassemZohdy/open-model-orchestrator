import json

import pytest

from omo.classification import ANALYSIS_INSTRUCTION, CLASSIFICATION_OBJECTIVE_ID
from training.dataset import build_sft_records


def test_training_builder_uses_exact_runtime_contract_and_excludes_policy_actions():
    records, manifest = build_sft_records("evaluation/seed.jsonl")

    assert [record.source_record_id for record in records] == [
        "omo-015",
        "omo-016",
        "omo-017",
        "omo-018",
    ]
    assert all(record.objective == CLASSIFICATION_OBJECTIVE_ID for record in records)
    assert all(record.prompt[0].content == ANALYSIS_INSTRUCTION for record in records)
    assert manifest["records"] == 4
    assert manifest["protected_test_included"] is False

    helper = next(record for record in records if record.source_record_id == "omo-018")
    target = json.loads(helper.completion[0].content)
    assert target == {
        "schema_version": "1",
        "action": "helper",
        "capability": "text",
        "helper": {
            "id": "decimal",
            "operation": "add",
            "a": "12.5",
            "b": "2.5",
            "unit": "",
        },
    }


def test_training_builder_is_deterministic():
    first, first_manifest = build_sft_records("evaluation/seed.jsonl")
    second, second_manifest = build_sft_records("evaluation/seed.jsonl")

    assert first == second
    assert first_manifest == second_manifest


def test_training_builder_never_accepts_protected_test_split():
    with pytest.raises(ValueError):
        build_sft_records("evaluation/seed.jsonl", "test")  # type: ignore[arg-type]
