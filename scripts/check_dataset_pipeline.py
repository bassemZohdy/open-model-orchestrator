"""Check deterministic OMO dataset generation without external services."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluation.build_dataset import build_dataset  # noqa: E402
from evaluation.dataset import validate  # noqa: E402

SOURCE = ROOT / "evaluation/seed.jsonl"
MANIFEST = ROOT / "evaluation/dataset_manifest.yaml"


def _validate_manifest() -> dict[str, Any]:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("dataset manifest must be a mapping")
    if manifest.get("schema_version") != "1":
        raise ValueError("dataset manifest schema is not supported")
    if manifest.get("objective") != "omo-routing-proposal-v1":
        raise ValueError("dataset objective is not pinned")
    source = manifest.get("source")
    if not isinstance(source, dict):
        raise ValueError("dataset source is required")
    if source != {
        "path": "evaluation/seed.jsonl",
        "name": "omo-original-synthetic",
        "license": "Apache-2.0",
    }:
        raise ValueError("dataset source or license changed")
    if manifest.get("training_splits") != ["train"]:
        raise ValueError("only the train split may be emitted")
    if manifest.get("protected_test_split") != "test":
        raise ValueError("protected test split is not pinned")
    output = manifest.get("output")
    if output != {
        "format": "canonical-jsonl",
        "record_order": "id-ascending",
        "card_filename": "DATASET_CARD.json",
    }:
        raise ValueError("dataset output format is not pinned")
    publication = manifest.get("publication")
    if publication != {"hub_revision_required": True, "status": "blocked-pending-omo-006"}:
        raise ValueError("dataset publication must remain blocked")
    return manifest


def main() -> None:
    _validate_manifest()
    with tempfile.TemporaryDirectory(prefix="omo-dataset-") as temporary:
        root = Path(temporary)
        first_output = root / "first" / "train.jsonl"
        first_card = root / "first" / "DATASET_CARD.json"
        second_output = root / "second" / "train.jsonl"
        second_card = root / "second" / "DATASET_CARD.json"

        first = build_dataset(SOURCE, first_output, first_card)
        second = build_dataset(SOURCE, second_output, second_card)
        if first != second:
            raise ValueError("dataset cards are not deterministic")
        if first_output.read_bytes() != second_output.read_bytes():
            raise ValueError("dataset output is not deterministic")

        records, _ = validate(first_output)
        if not records or {record.split for record in records} != {"train"}:
            raise ValueError("training output contains a non-training split")
        if first["protected_test_labels_in_output"] is not False:
            raise ValueError("protected test labels were exposed")
        card = json.loads(first_card.read_text(encoding="utf-8"))
        if card != first:
            raise ValueError("written dataset card differs from the returned card")
        print(
            json.dumps(
                {
                    "status": "validated",
                    "records": len(records),
                    "protected_test_not_written": True,
                    "output_sha256": first["output_sha256"],
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
