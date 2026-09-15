import json
from pathlib import Path

import pytest

from evaluation.build_dataset import build_dataset
from evaluation.dataset import validate


SOURCE = Path("evaluation/seed.jsonl")


def test_training_build_is_deterministic_and_excludes_protected_test(tmp_path: Path) -> None:
    first_output = tmp_path / "one" / "train.jsonl"
    first_card = tmp_path / "one" / "DATASET_CARD.json"
    second_output = tmp_path / "two" / "train.jsonl"
    second_card = tmp_path / "two" / "DATASET_CARD.json"

    first = build_dataset(SOURCE, first_output, first_card)
    second = build_dataset(SOURCE, second_output, second_card)

    assert first == second
    assert first_output.read_bytes() == second_output.read_bytes()
    records, _ = validate(first_output)
    assert records
    assert {record.split for record in records} == {"train"}
    assert first["protected_test_labels_in_output"] is False
    assert json.loads(first_card.read_text()) == first
    assert "omo-019" not in first_output.read_text()


def test_source_cannot_be_overwritten(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="overwrite"):
        build_dataset(SOURCE, SOURCE, tmp_path / "card.json")
