"""Offline held-out routing evaluation contracts.

This evaluator scores observed decisions from a separately generated run. It never
authorizes execution, calls a provider, or treats confidence as a policy signal.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Literal

from omo.contracts import Action, ChatRequest, HelperCall, StrictModel

Category = Literal[
    "helper-selection",
    "argument-fidelity",
    "result-interpretation",
    "routing-contention",
]


class HeldOutCase(StrictModel):
    schema_version: Literal["1"] = "1"
    id: str
    category: Category
    request: ChatRequest
    expected_action: Action
    expected_helper: HelperCall | None = None
    expected_result: str | None = None
    expected_reason: str | None = None

    def model_post_init(self, __context: object) -> None:
        if self.expected_action != "helper" and self.expected_helper is not None:
            raise ValueError("non-helper case must not carry expected_helper")
        if self.category in {"helper-selection", "argument-fidelity"} and (
            self.expected_action != "helper" or self.expected_helper is None
        ):
            raise ValueError(f"{self.category} requires an expected helper")
        if self.category == "result-interpretation" and self.expected_result is None:
            raise ValueError("result-interpretation requires expected_result")
        if self.category == "routing-contention" and self.expected_reason is None:
            raise ValueError("routing-contention requires expected_reason")


class HeldOutObservation(StrictModel):
    schema_version: Literal["1"] = "1"
    case_id: str
    actual_action: Action
    actual_helper: HelperCall | None = None
    actual_result: str | None = None
    actual_reason: str | None = None

    def model_post_init(self, __context: object) -> None:
        if self.actual_action != "helper" and self.actual_helper is not None:
            raise ValueError("non-helper observation must not carry actual_helper")


def _read_jsonl(path: str, model: type[StrictModel]) -> tuple[list[StrictModel], str]:
    raw = Path(path).read_bytes()
    if len(raw) > 1_000_000:
        raise ValueError("held-out import exceeds 1 MB budget")
    rows = [model.model_validate_json(line) for line in raw.splitlines() if line.strip()]
    return rows, hashlib.sha256(raw).hexdigest()


def load_cases(path: str) -> tuple[list[HeldOutCase], str]:
    rows, digest = _read_jsonl(path, HeldOutCase)
    cases = [row for row in rows if isinstance(row, HeldOutCase)]
    ids = [case.id for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate held-out case id")
    return cases, digest


def load_observations(path: str) -> tuple[list[HeldOutObservation], str]:
    rows, digest = _read_jsonl(path, HeldOutObservation)
    observations = [row for row in rows if isinstance(row, HeldOutObservation)]
    ids = [observation.case_id for observation in observations]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate held-out observation case id")
    return observations, digest


def _same_helper(expected: HelperCall | None, actual: HelperCall | None) -> bool:
    if expected is None or actual is None:
        return expected is actual
    return expected.model_dump() == actual.model_dump()


def evaluate(
    cases: list[HeldOutCase], observations: list[HeldOutObservation]
) -> dict[str, object]:
    case_by_id = {case.id: case for case in cases}
    observation_by_id = {observation.case_id: observation for observation in observations}
    unknown = sorted(set(observation_by_id) - set(case_by_id))
    missing = sorted(set(case_by_id) - set(observation_by_id))
    if unknown:
        raise ValueError(f"unknown held-out observation: {unknown[0]}")
    if missing:
        raise ValueError(f"missing held-out observation: {missing[0]}")

    category_totals: dict[str, dict[str, int]] = {}
    failures: list[dict[str, object]] = []
    for case in cases:
        observation = observation_by_id[case.id]
        checks = {
            "selection": observation.actual_action == case.expected_action,
        }
        if case.category == "helper-selection":
            checks["helper_selection"] = _same_helper(
                case.expected_helper, observation.actual_helper
            )
        elif case.category == "argument-fidelity":
            checks["argument_fidelity"] = _same_helper(
                case.expected_helper, observation.actual_helper
            )
        elif case.category == "result-interpretation":
            checks["result_interpretation"] = (
                observation.actual_result == case.expected_result
            )
        else:
            checks["routing_contention"] = observation.actual_reason == case.expected_reason

        passed = all(checks.values())
        totals = category_totals.setdefault(case.category, {"cases": 0, "passed": 0})
        totals["cases"] += 1
        totals["passed"] += int(passed)
        if not passed:
            failures.append(
                {"case_id": case.id, "category": case.category, "checks": checks}
            )

    for totals in category_totals.values():
        totals["accuracy"] = totals["passed"] / totals["cases"]

    return {
        "schema_version": "1",
        "cases": len(cases),
        "passed": len(cases) - len(failures),
        "failed": len(failures),
        "by_category": category_totals,
        "failures": failures,
        "protected_test_evaluated": False,
        "external_calls": 0,
        "confidence_used_for_authorization": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default="evaluation/heldout.jsonl")
    parser.add_argument("--observations")
    parser.add_argument("--output", default="evaluation/results-local/heldout.json")
    parser.add_argument("--validate-cases", action="store_true")
    args = parser.parse_args()

    cases, cases_digest = load_cases(args.cases)
    if args.validate_cases or args.observations is None:
        print(json.dumps({"cases": len(cases), "cases_sha256": cases_digest}))
        return 0

    observations, observations_digest = load_observations(args.observations)
    report = evaluate(cases, observations)
    report["cases_sha256"] = cases_digest
    report["observations_sha256"] = observations_digest
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("cases", "passed", "failed")}))
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
