"""Build the bounded OMO classification training dataset deterministically.

The source corpus remains versioned JSONL. This builder emits only the train
split, canonicalizes records and writes a machine-readable card with hashes.
Protected development, validation, calibration and test records are never
copied into a training output.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Final

from evaluation.dataset import IntentRecord, validate

CLASSIFICATION_OBJECTIVE: Final = "omo-routing-classification-v1"
TRAINING_SPLITS: Final = frozenset({"train"})
PROTECTED_TEST_SPLIT: Final = "test"
MODEL_PROPOSAL_ACTIONS: Final = frozenset({"external_model", "helper", "clarify"})


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_record(record: IntentRecord) -> str:
    return json.dumps(
        record.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def build_dataset(
    input_path: str | Path,
    output_path: str | Path,
    card_path: str | Path,
) -> dict[str, object]:
    """Build the training-only dataset and return its deterministic card."""
    source = Path(input_path)
    output = Path(output_path)
    card_file = Path(card_path)
    if source.resolve() == output.resolve():
        raise ValueError("training output must not overwrite the source corpus")
    if source.resolve() == card_file.resolve():
        raise ValueError("dataset card must not overwrite the source corpus")

    records, input_sha256 = validate(source)
    selected = [record for record in records if record.split in TRAINING_SPLITS]
    if not selected:
        raise ValueError("the training split must contain at least one record")
    if any(record.split == PROTECTED_TEST_SPLIT for record in selected):
        raise ValueError("protected test records cannot enter training output")
    if any(record.expected_action not in MODEL_PROPOSAL_ACTIONS for record in selected):
        raise ValueError("training records must use model proposal actions only")

    selected.sort(key=lambda record: record.id)
    output_text = "".join(_canonical_record(record) + "\n" for record in selected)
    output_bytes = output_text.encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(output_bytes)

    input_counts: dict[str, int] = {}
    for record in records:
        input_counts[record.split] = input_counts.get(record.split, 0) + 1
    output_counts: dict[str, int] = {}
    for record in selected:
        output_counts[record.split] = output_counts.get(record.split, 0) + 1

    card: dict[str, object] = {
        "schema_version": "1",
        "objective": CLASSIFICATION_OBJECTIVE,
        "source": "omo-original-synthetic",
        "license": "Apache-2.0",
        "input_sha256": input_sha256,
        "output_sha256": _sha256(output_bytes),
        "input_records": len(records),
        "output_records": len(selected),
        "input_records_by_split": dict(sorted(input_counts.items())),
        "output_records_by_split": dict(sorted(output_counts.items())),
        "training_splits": sorted(TRAINING_SPLITS),
        "protected_test_split": PROTECTED_TEST_SPLIT,
        "protected_test_labels_in_output": False,
        "record_order": "id-ascending",
        "canonical_json": "sorted-keys;compact;utf-8;one-record-per-line",
    }
    card_file.parent.mkdir(parents=True, exist_ok=True)
    card_file.write_text(json.dumps(card, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return card
