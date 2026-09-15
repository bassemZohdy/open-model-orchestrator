"""Check deterministic OMO dataset generation without external services."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluation.build_dataset import build_dataset  # noqa: E402
from evaluation.dataset import validate  # noqa: E402

SOURCE = ROOT / "evaluation/seed.jsonl"


def main() -> None:
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
