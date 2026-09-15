"""Offline evaluation provenance, calibration and human-review contracts.

These records describe evidence; they do not invoke a provider, store a
credential, or authorize routing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, model_validator

from evaluation.dataset import OutcomeRecord, selective_curve
from omo.contracts import StrictModel

IDENTIFIER_PATTERN = r"^[A-Za-z0-9_.:-]{1,128}$"
SHA_PATTERN = r"^[0-9a-fA-F]{40}$"


class SourceAuditRecord(StrictModel):
    schema_version: Literal["1"] = "1"
    source_id: str = Field(pattern=IDENTIFIER_PATTERN)
    source_kind: Literal[
        "omo-original-synthetic", "external-benchmark", "provider-generated"
    ]
    license_spdx_id: str = Field(min_length=1, max_length=80)
    license_status: Literal["pending", "approved", "rejected"]
    provenance_summary: str = Field(min_length=1, max_length=1000)
    reviewer_id: str | None = Field(default=None, pattern=IDENTIFIER_PATTERN)

    @model_validator(mode="after")
    def approved_source_requires_reviewer(self) -> Self:
        if self.license_status == "approved" and self.reviewer_id is None:
            raise ValueError("approved source requires reviewer_id")
        return self


class EvaluationBatch(StrictModel):
    schema_version: Literal["1"] = "1"
    batch_id: str = Field(pattern=IDENTIFIER_PATTERN)
    source_audit_id: str = Field(pattern=IDENTIFIER_PATTERN)
    dataset_revision: str = Field(pattern=SHA_PATTERN)
    model_revision: str = Field(pattern=SHA_PATTERN)
    policy_version: Literal["omo-policy-1"] = "omo-policy-1"
    provider_id: str = Field(pattern=IDENTIFIER_PATTERN)
    provider_revision: str = Field(pattern=IDENTIFIER_PATTERN)
    outcomes: list[OutcomeRecord] = Field(min_length=1, max_length=10000)

    @model_validator(mode="after")
    def outcomes_share_lineage(self) -> Self:
        if any(outcome.model_revision != self.model_revision for outcome in self.outcomes):
            raise ValueError("outcomes must share the batch model revision")
        if any(outcome.policy_version != self.policy_version for outcome in self.outcomes):
            raise ValueError("outcomes must share the batch policy version")
        prompt_ids = [outcome.prompt_id for outcome in self.outcomes]
        if len(prompt_ids) != len(set(prompt_ids)):
            raise ValueError("batch contains duplicate prompt ids")
        return self


class ReviewCriteria(StrictModel):
    selection_correct: bool | None = None
    arguments_faithful: bool | None = None
    result_faithful: bool | None = None
    policy_respected: bool | None = None

    @model_validator(mode="after")
    def at_least_one_criterion(self) -> Self:
        if not any(value is not None for value in self.model_dump().values()):
            raise ValueError("review requires at least one criterion")
        return self


class HumanReviewRecord(StrictModel):
    schema_version: Literal["1"] = "1"
    review_id: str = Field(pattern=IDENTIFIER_PATTERN)
    batch_id: str = Field(pattern=IDENTIFIER_PATTERN)
    prompt_id: str = Field(pattern=IDENTIFIER_PATTERN)
    reviewer_id: str = Field(pattern=IDENTIFIER_PATTERN)
    protocol_version: Literal["omo-human-review-v1"] = "omo-human-review-v1"
    decision: Literal["pass", "fail", "needs-review"]
    criteria: ReviewCriteria
    comments: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def decision_matches_criteria(self) -> Self:
        values = self.criteria.model_dump().values()
        if self.decision == "pass" and any(
            value is not True for value in values if value is not None
        ):
            raise ValueError("passing review requires every applicable criterion")
        if self.decision == "fail" and not any(value is False for value in values):
            raise ValueError("failed review requires a failed criterion")
        return self


class AuditBundle(StrictModel):
    schema_version: Literal["1"] = "1"
    source: SourceAuditRecord
    batch: EvaluationBatch
    reviews: list[HumanReviewRecord] = Field(default_factory=list, max_length=10000)

    @model_validator(mode="after")
    def references_are_consistent(self) -> Self:
        if self.batch.source_audit_id != self.source.source_id:
            raise ValueError("batch source audit reference mismatch")
        review_ids = [review.review_id for review in self.reviews]
        if len(review_ids) != len(set(review_ids)):
            raise ValueError("duplicate review id")
        prompt_ids = {outcome.prompt_id for outcome in self.batch.outcomes}
        for review in self.reviews:
            if review.batch_id != self.batch.batch_id:
                raise ValueError("review batch reference mismatch")
            if review.prompt_id not in prompt_ids:
                raise ValueError("review references unknown prompt id")
        return self


def load_bundle(path: str) -> tuple[AuditBundle, str]:
    raw = Path(path).read_bytes()
    if len(raw) > 2_000_000:
        raise ValueError("audit bundle exceeds 2 MB budget")
    return AuditBundle.model_validate_json(raw), hashlib.sha256(raw).hexdigest()


def calibration_report(
    bundle: AuditBundle, thresholds: tuple[float, ...] = (0.0, 0.5, 0.8, 0.9)
) -> dict[str, object]:
    if any(not 0 <= threshold <= 1 for threshold in thresholds):
        raise ValueError("calibration thresholds must be between 0 and 1")
    if tuple(sorted(set(thresholds))) != thresholds:
        raise ValueError("calibration thresholds must be sorted and unique")
    reviews = {
        decision: sum(review.decision == decision for review in bundle.reviews)
        for decision in ("pass", "fail", "needs-review")
    }
    return {
        "schema_version": "1",
        "batch_id": bundle.batch.batch_id,
        "source_audit_id": bundle.source.source_id,
        "dataset_revision": bundle.batch.dataset_revision.lower(),
        "model_revision": bundle.batch.model_revision.lower(),
        "provider": {
            "id": bundle.batch.provider_id,
            "revision": bundle.batch.provider_revision,
        },
        "samples": len(bundle.batch.outcomes),
        "selective_curve": selective_curve(list(bundle.batch.outcomes), thresholds),
        "human_review": {
            "records": len(bundle.reviews),
            "decisions": reviews,
            "protocol_version": "omo-human-review-v1",
        },
        "confidence_used_for_authorization": False,
        "external_calls": 0,
        "protected_test_evaluated": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--validate", action="store_true")
    group.add_argument("--calibrate", action="store_true")
    parser.add_argument("--output", default="evaluation/results-local/audit.json")
    args = parser.parse_args()

    bundle, digest = load_bundle(args.bundle)
    if args.validate:
        print(
            json.dumps(
                {
                    "batch_id": bundle.batch.batch_id,
                    "outcomes": len(bundle.batch.outcomes),
                    "reviews": len(bundle.reviews),
                    "bundle_sha256": digest,
                }
            )
        )
        return 0

    report = calibration_report(bundle)
    report["bundle_sha256"] = digest
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"samples": report["samples"], "reviews": report["human_review"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
