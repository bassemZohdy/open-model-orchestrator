import pytest

from evaluation.dataset import OutcomeRecord, selective_curve, validate, validate_outcomes


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
