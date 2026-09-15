import pytest

from evaluation.audit import (
    AuditBundle,
    EvaluationBatch,
    HumanReviewRecord,
    ReviewCriteria,
    SourceAuditRecord,
    calibration_report,
)
from evaluation.dataset import OutcomeRecord

MODEL_REVISION = "a" * 40
DATASET_REVISION = "b" * 40


def _outcome(prompt_id: str, confidence: float = 0.9) -> OutcomeRecord:
    return OutcomeRecord(
        prompt_id=prompt_id,
        model_revision=MODEL_REVISION,
        policy_version="omo-policy-1",
        response="observed",
        evaluation_method="fixed-provider-contract",
        passed=True,
        latency_ms=10,
        confidence=confidence,
        timestamp="2026-09-15T00:00:00Z",
    )


def _bundle(*reviews: HumanReviewRecord) -> AuditBundle:
    source = SourceAuditRecord(
        source_id="omo-synthetic-v1",
        source_kind="omo-original-synthetic",
        license_spdx_id="Apache-2.0",
        license_status="approved",
        provenance_summary="Original synthetic prompts committed to the repository.",
        reviewer_id="repo-owner",
    )
    batch = EvaluationBatch(
        batch_id="batch-1",
        source_audit_id=source.source_id,
        dataset_revision=DATASET_REVISION,
        model_revision=MODEL_REVISION,
        provider_id="fixed-provider-test",
        provider_revision="provider-v1",
        outcomes=[_outcome("one"), _outcome("two", confidence=0.4)],
    )
    return AuditBundle(source=source, batch=batch, reviews=list(reviews))


def test_calibration_report_preserves_fixed_provider_lineage() -> None:
    review = HumanReviewRecord(
        review_id="review-1",
        batch_id="batch-1",
        prompt_id="one",
        reviewer_id="reviewer-1",
        decision="pass",
        criteria=ReviewCriteria(
            selection_correct=True,
            result_faithful=True,
            policy_respected=True,
        ),
    )
    report = calibration_report(_bundle(review))
    assert report["samples"] == 2
    assert report["provider"] == {
        "id": "fixed-provider-test",
        "revision": "provider-v1",
    }
    assert report["selective_curve"][-1]["coverage"] == 0.5
    assert report["human_review"]["decisions"]["pass"] == 1
    assert report["confidence_used_for_authorization"] is False
    assert report["external_calls"] == 0


def test_batch_rejects_mixed_model_or_policy_lineage() -> None:
    with pytest.raises(ValueError, match="model revision"):
        EvaluationBatch(
            batch_id="batch-1",
            source_audit_id="source-1",
            dataset_revision=DATASET_REVISION,
            model_revision=MODEL_REVISION,
            provider_id="fixed-provider-test",
            provider_revision="provider-v1",
            outcomes=[
                _outcome("one"),
                _outcome("two").model_copy(update={"model_revision": "c" * 40}),
            ],
        )
    with pytest.raises(ValueError, match="policy version"):
        EvaluationBatch(
            batch_id="batch-1",
            source_audit_id="source-1",
            dataset_revision=DATASET_REVISION,
            model_revision=MODEL_REVISION,
            provider_id="fixed-provider-test",
            provider_revision="provider-v1",
            outcomes=[
                _outcome("one"),
                _outcome("two").model_copy(update={"policy_version": "bad"}),
            ],
        )


def test_review_decision_must_match_criteria() -> None:
    with pytest.raises(ValueError, match="passing review"):
        HumanReviewRecord(
            review_id="review-1",
            batch_id="batch-1",
            prompt_id="one",
            reviewer_id="reviewer-1",
            decision="pass",
            criteria=ReviewCriteria(selection_correct=False),
        )
    with pytest.raises(ValueError, match="failed review"):
        HumanReviewRecord(
            review_id="review-2",
            batch_id="batch-1",
            prompt_id="one",
            reviewer_id="reviewer-1",
            decision="fail",
            criteria=ReviewCriteria(selection_correct=True),
        )


def test_audit_bundle_rejects_unknown_review_prompt() -> None:
    review = HumanReviewRecord(
        review_id="review-1",
        batch_id="batch-1",
        prompt_id="unknown",
        reviewer_id="reviewer-1",
        decision="needs-review",
        criteria=ReviewCriteria(selection_correct=None),
    )
    with pytest.raises(ValueError, match="unknown prompt"):
        _bundle(review)


def test_approved_source_requires_auditor() -> None:
    with pytest.raises(ValueError, match="reviewer_id"):
        SourceAuditRecord(
            source_id="source-1",
            source_kind="external-benchmark",
            license_spdx_id="Apache-2.0",
            license_status="approved",
            provenance_summary="Missing reviewer identity.",
        )
