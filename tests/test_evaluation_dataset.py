import pytest

from evaluation.dataset import (
    IntentRecord,
    OutcomeRecord,
    selective_curve,
    validate,
    validate_outcomes,
)


def test_dataset_rejects_duplicate_prompt_content(tmp_path):
    path = tmp_path / "seed.jsonl"
    row = (
        '{"id":"one","family":"one","split":"test","language":"en",'
        '"messages":[{"role":"user","content":"same prompt"}],'
        '"required_capability":"text","expected_action":"reject"}\n'
    )
    path.write_text(row + row.replace('"one"', '"two"', 2))
    with pytest.raises(ValueError, match="duplicate prompt content"):
        validate(str(path))


def test_outcomes_and_selective_curve_are_bounded(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    path.write_text(
        "\n".join(
            [
                '{"prompt_id":"one","model_revision":"m","policy_version":"p","response":"ok","evaluation_method":"human","passed":true,"latency_ms":1,"confidence":0.9,"timestamp":"now"}',
                '{"prompt_id":"two","model_revision":"m","policy_version":"p","response":"bad","evaluation_method":"human","passed":false,"latency_ms":2,"confidence":0.4,"timestamp":"now"}',
            ]
        )
        + "\n"
    )
    records, _ = validate_outcomes(str(path))
    assert len(records) == 2
    assert selective_curve(records)[-1]["coverage"] == 0.5


def test_outcome_model_rejects_unbounded_values():
    with pytest.raises(ValueError):
        OutcomeRecord(
            prompt_id="one",
            model_revision="m",
            policy_version="p",
            response="ok",
            evaluation_method="human",
            passed=True,
            latency_ms=-1,
            confidence=0.5,
            timestamp="now",
        )


def test_model_routed_record_requires_a_matching_proposal():
    common = {
        "id": "one",
        "family": "one",
        "split": "train",
        "language": "en",
        "messages": [{"role": "user", "content": "Write an email"}],
        "required_capability": "text",
        "expected_action": "external_model",
    }
    with pytest.raises(ValueError, match="requires expected_proposal"):
        IntentRecord.model_validate(common)
    with pytest.raises(ValueError, match="capability mismatch"):
        IntentRecord.model_validate(
            {
                **common,
                "expected_proposal": {
                    "action": "external_model",
                    "capability": "coding",
                },
            }
        )


def test_policy_owned_record_rejects_a_model_proposal():
    with pytest.raises(ValueError, match="policy-owned action"):
        IntentRecord.model_validate(
            {
                "id": "one",
                "family": "one",
                "split": "validation",
                "language": "en",
                "messages": [{"role": "user", "content": "unsafe"}],
                "required_capability": "text",
                "expected_action": "reject",
                "expected_proposal": {"action": "clarify", "capability": "text"},
            }
        )
