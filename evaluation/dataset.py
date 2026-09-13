"""Validate original JSONL examples; no pickle or dataset-supplied execution."""

import argparse
import hashlib
import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Literal

from pydantic import Field

from omo.contracts import Action, Capability, Message, StrictModel


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
    reference_terms: list[str] = Field(default_factory=list)
    label_provenance: str = "bootstrap author; development-only label"


class OutcomeRecord(StrictModel):
    schema_version: Literal["1"] = "1"
    prompt_id: str
    model_revision: str
    policy_version: str
    response: str
    evaluation_method: str
    passed: bool
    latency_ms: float
    observed_cost_usd: float | None = None
    timestamp: str


def validate(path):
    raw = Path(path).read_bytes()
    if len(raw) > 1_000_000:
        raise ValueError("seed import exceeds 1 MB budget")
    records = [IntentRecord.model_validate_json(line) for line in raw.splitlines() if line.strip()]
    ids = set()
    families = {}
    normalized = []
    for r in records:
        if r.id in ids:
            raise ValueError("duplicate prompt id")
        ids.add(r.id)
        if r.family in families and families[r.family] != r.split:
            raise ValueError("family split leakage")
        families[r.family] = r.split
        text = re.sub(r"\W+", " ", " ".join(m.content for m in r.messages).lower()).strip()
        for other, split in normalized:
            if r.split != split and SequenceMatcher(None, text, other).ratio() >= 0.9:
                raise ValueError("near-duplicate across dataset splits")
        normalized.append((text, r.split))
    return records, hashlib.sha256(raw).hexdigest()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--validate", required=True)
    args = p.parse_args()
    rows, digest = validate(args.validate)
    print(
        json.dumps(
            {
                "records": len(rows),
                "sha256": digest,
                "status": "validated",
                "protected_test_not_evaluated": True,
            }
        )
    )
