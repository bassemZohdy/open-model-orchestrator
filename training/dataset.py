"""Build deterministic SFT prompt/completion records without protected-test leakage."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Literal

from pydantic import Field

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluation.dataset import IntentRecord, validate  # noqa: E402, I001
from omo.classification import CLASSIFICATION_OBJECTIVE_ID, analysis_messages  # noqa: E402
from omo.contracts import Message, StrictModel  # noqa: E402

BuildableSplit = Literal["train", "validation", "calibration"]
BUILDABLE_SPLITS: tuple[BuildableSplit, ...] = ("train", "validation", "calibration")


class SFTRecord(StrictModel):
    schema_version: Literal["1"] = "1"
    objective: Literal["omo-routing-proposal-v1"] = CLASSIFICATION_OBJECTIVE_ID
    source_record_id: str
    family: str
    split: BuildableSplit
    prompt: list[Message] = Field(min_length=2, max_length=2)
    completion: list[Message] = Field(min_length=1, max_length=1)


def _record_for_sft(record: IntentRecord) -> SFTRecord | None:
    if record.expected_proposal is None:
        return None
    if record.split not in BUILDABLE_SPLITS:
        return None
    prompt = [Message.model_validate(message) for message in analysis_messages(record.messages)]
    completion = [
        Message(
            role="assistant",
            content=record.expected_proposal.model_dump_json(exclude_none=True),
        )
    ]
    return SFTRecord(
        source_record_id=record.id,
        family=record.family,
        split=record.split,
        prompt=prompt,
        completion=completion,
    )


def build_sft_records(
    source: str | Path, split: BuildableSplit = "train"
) -> tuple[list[SFTRecord], dict[str, object]]:
    records, source_digest = validate(str(source))
    built = []
    for row in records:
        if row.split != split:
            continue
        candidate = _record_for_sft(row)
        if candidate is not None:
            built.append(candidate)
    if not built:
        raise ValueError(f"no model-routed records for split {split}")
    payload = b"".join(
        record.model_dump_json(exclude_none=True).encode() + b"\n" for record in built
    )
    return built, {
        "schema_version": "1",
        "objective": CLASSIFICATION_OBJECTIVE_ID,
        "split": split,
        "records": len(built),
        "source_sha256": source_digest,
        "artifact_sha256": hashlib.sha256(payload).hexdigest(),
        "protected_test_included": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build bounded OMO SFT records")
    parser.add_argument("--source", type=Path, default=ROOT / "evaluation/seed.jsonl")
    parser.add_argument("--split", choices=BUILDABLE_SPLITS, default="train")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    records, manifest = build_sft_records(args.source, args.split)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            "".join(record.model_dump_json(exclude_none=True) + "\n" for record in records)
        )
    print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
