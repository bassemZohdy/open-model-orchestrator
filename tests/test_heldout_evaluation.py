import json

import pytest

from evaluation.heldout import (
    HeldOutCase,
    HeldOutObservation,
    evaluate,
    load_cases,
)


def _cases() -> list[HeldOutCase]:
    return [
        HeldOutCase(
            id="helper",
            category="helper-selection",
            request={"messages": [{"role": "user", "content": "calc 1 + 2"}]},
            expected_action="helper",
            expected_helper={"id": "decimal", "operation": "add", "a": "1", "b": "2"},
        ),
        HeldOutCase(
            id="arguments",
            category="argument-fidelity",
            request={"messages": [{"role": "user", "content": "calc -4 * 7"}]},
            expected_action="helper",
            expected_helper={
                "id": "decimal",
                "operation": "multiply",
                "a": "-4",
                "b": "7",
            },
        ),
        HeldOutCase(
            id="result",
            category="result-interpretation",
            request={"messages": [{"role": "user", "content": "calc 1.20 + 2.30"}]},
            expected_action="helper",
            expected_result="3.50",
        ),
        HeldOutCase(
            id="contention",
            category="routing-contention",
            request={
                "messages": [{"role": "user", "content": "What is the latest stock price?"}],
                "omo": {"local_only": True, "required_capability": "current_information"},
            },
            expected_action="reject",
            expected_reason="retrieval_unavailable",
        ),
    ]


def test_heldout_evaluation_reports_each_gate() -> None:
    observations = [
        HeldOutObservation(
            case_id="helper",
            actual_action="helper",
            actual_helper={"id": "decimal", "operation": "add", "a": "1", "b": "2"},
        ),
        HeldOutObservation(
            case_id="arguments",
            actual_action="helper",
            actual_helper={
                "id": "decimal",
                "operation": "multiply",
                "a": "-4",
                "b": "7",
            },
        ),
        HeldOutObservation(
            case_id="result",
            actual_action="helper",
            actual_result="3.50",
        ),
        HeldOutObservation(
            case_id="contention",
            actual_action="reject",
            actual_reason="retrieval_unavailable",
        ),
    ]
    report = evaluate(_cases(), observations)
    assert report["passed"] == 4
    assert report["failed"] == 0
    assert set(report["by_category"]) == {
        "helper-selection",
        "argument-fidelity",
        "result-interpretation",
        "routing-contention",
    }
    assert report["protected_test_evaluated"] is False
    assert report["confidence_used_for_authorization"] is False


def test_heldout_evaluation_reports_argument_and_result_failures() -> None:
    observations = [
        HeldOutObservation(
            case_id="helper",
            actual_action="helper",
            actual_helper={"id": "decimal", "operation": "subtract", "a": "1", "b": "2"},
        ),
        HeldOutObservation(
            case_id="arguments",
            actual_action="helper",
            actual_helper={
                "id": "decimal",
                "operation": "multiply",
                "a": "-4",
                "b": "8",
            },
        ),
        HeldOutObservation(case_id="result", actual_action="helper", actual_result="3.40"),
        HeldOutObservation(
            case_id="contention",
            actual_action="reject",
            actual_reason="retrieval_unavailable",
        ),
    ]
    report = evaluate(_cases(), observations)
    assert report["passed"] == 1
    assert report["failed"] == 3
    assert {failure["case_id"] for failure in report["failures"]} == {
        "helper",
        "arguments",
        "result",
    }


def test_heldout_evaluation_rejects_missing_and_unknown_observations() -> None:
    with pytest.raises(ValueError, match="missing"):
        evaluate(
            _cases(),
            [
                HeldOutObservation(case_id="helper", actual_action="helper"),
                HeldOutObservation(case_id="arguments", actual_action="helper"),
                HeldOutObservation(case_id="result", actual_action="helper"),
            ],
        )
    with pytest.raises(ValueError, match="unknown"):
        evaluate(
            _cases(),
            [
                HeldOutObservation(case_id="helper", actual_action="helper"),
                HeldOutObservation(case_id="arguments", actual_action="helper"),
                HeldOutObservation(case_id="result", actual_action="helper"),
                HeldOutObservation(case_id="contention", actual_action="reject"),
                HeldOutObservation(case_id="other", actual_action="reject"),
            ],
        )


def test_heldout_case_loader_rejects_duplicate_ids(tmp_path) -> None:
    row = {
        "id": "same",
        "category": "routing-contention",
        "request": {"messages": [{"role": "user", "content": "Current price?"}]},
        "expected_action": "reject",
        "expected_reason": "retrieval_unavailable",
    }
    path = tmp_path / "heldout.jsonl"
    path.write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n")
    with pytest.raises(ValueError, match="duplicate held-out case id"):
        load_cases(str(path))
