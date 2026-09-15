"""Validate original JSONL examples; no pickle or dataset-supplied execution."""

import argparse
import hashlib
import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, model_validator

from omo.classification import POLICY_OWNED_ACTIONS, PROPOSAL_ACTIONS
from omo.contracts import Action, Capability, Message, Proposal, StrictModel


class IntentRecord(StrictModel):
    schema_version: Literal["1"] = "1"
    id: str
    family: str
    split: Literal["train", "validation", "calibration", "test", "development"]
    source: Literal["omo-original-synthetic"] = "omo-original-synthetic"
    license: Literal["Apache-2.0"] = "Apache-2.0"
    language: str
    messages: list[Message]
    required_capability: Capability
    expected_action: Action
    expected_proposal: Proposal | None = None
    reference_terms: list[str] = Field(default_factory=list)
    label_provenance: str = "bootstrap author; development-only label"

    @model_validator(mode="after")
    def proposal_matches_runtime_boundary(self) -> Self:
        if self.expected_action in PROPOSAL_ACTIONS:
            if self.expected_proposal is None:
                raise ValueError("model-routed record requires expected_proposal")
            if self.expected_proposal.action != self.expected_action:
                raise ValueError("expected proposal action mismatch")
            if self.expected_proposal.capability != self.required_capability:
                raise ValueError("expected proposal capability mismatch")
        elif self.expected_action in POLICY_OWNED_ACTIONS and self.expected_proposal is not None:
            raise ValueError("policy-owned action must not have an expected proposal")
        return self


class OutcomeRecord(StrictModel):
    schema_version: Literal["1"] = "1"
    prompt_id: str
    model_revision: str
    policy_version: str
    response: str
    evaluation_method: str
    passed: bool
    latency_ms: float = Field(ge=0, allow_inf_nan=False)
    observed_cost_usd: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    timestamp: str = Field(min_length=1, max_length=80)


def _normalise(text: str) -> str:
    return re.sub(r"\W+", " ", text.lower()).strip()


def validate(path):
    raw = Path(path).read_bytes()
    if len(raw) > 1_000_000:
        raise ValueError("seed import exceeds 1 MB budget")
    records = [IntentRecord.model_validate_json(line) for line in raw.splitlines() if line.strip()]
    ids = set()
    families = {}
    normalized: dict[str, tuple[str, str]] = {}
    for r in records:
        if r.id in ids:
            raise ValueError("duplicate prompt id")
        ids.add(r.id)
        if r.family in families and families[r.family] != r.split:
            raise ValueError("family split leakage")
        families[r.family] = r.split
        text = _normalise(" ".join(m.content for m in r.messages))
        if text in normalized:
            raise ValueError("duplicate prompt content")
        for other, (split, _) in normalized.items():
            if r.split != split and SequenceMatcher(None, text, other).ratio() >= 0.9:
                raise ValueError("near-duplicate across dataset splits")
        normalized[text] = (r.split, r.family)
    return records, hashlib.sha256(raw).hexdigest()


def validate_outcomes(path: str) -> tuple[list[OutcomeRecord], str]:
    """Validate machine-readable outcomes without accepting raw prompt data."""
    raw = Path(path).read_bytes()
    if len(raw) > 1_000_000:
        raise ValueError("outcome import exceeds 1 MB budget")
    records = [OutcomeRecord.model_validate_json(line) for line in raw.splitlines() if line.strip()]
    seen: set[tuple[str, str, str]] = set()
    for record in records:
        key = (record.prompt_id, record.model_revision, record.policy_version)
        if key in seen:
            raise ValueError("duplicate outcome key")
        seen.add(key)
    return records, hashlib.sha256(raw).hexdigest()


def selective_curve(
    records: list[OutcomeRecord], thresholds: tuple[float, ...] = (0.0, 0.5, 0.8, 0.9)
) -> list[dict[str, float]]:
    """Return risk/coverage observations for confidence thresholds.

    Confidence is an observed evaluator score, not a model authorization signal.
    """
    if not records:
        return []
    curve = []
    for threshold in thresholds:
        accepted = [r for r in records if r.confidence >= threshold]
        curve.append(
            {
                "threshold": threshold,
                "coverage": len(accepted) / len(records),
                "risk": (sum(not r.passed for r in accepted) / len(accepted)) if accepted else 0.0,
            }
        )
    return curve


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--validate")
    group.add_argument("--validate-outcomes")
    args = p.parse_args()
    if args.validate:
        rows, digest = validate(args.validate)
        result = {
            "records": len(rows),
            "sha256": digest,
            "status": "validated",
            "protected_test_not_evaluated": True,
        }
    else:
        rows, digest = validate_outcomes(args.validate_outcomes)
        result = {
            "records": len(rows),
            "sha256": digest,
            "status": "validated",
            "selective_curve": selective_curve(rows),
        }
    print(json.dumps(result))
