"""Validate the predeclared evaluation candidates and acceptance gates."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.dataset import validate as validate_dataset  # noqa: E402, I001
from evaluation.dataset import validate_outcomes  # noqa: E402, I001

CONTRACT = ROOT / "evaluation/benchmark_contract.json"
DATASET = ROOT / "evaluation/seed.jsonl"
MANIFEST = ROOT / "evaluation/dataset_manifest.json"
OUTCOMES = ROOT / "evaluation/outcomes.example.jsonl"
EXPECTED_SPLITS = {
    "development": 4,
    "validation": 12,
    "calibration": 10,
    "train": 14,
    "test": 12,
}
REQUIRED_CANDIDATES = {
    "smollm2-360m-q8",
    "granite-4.0-350m",
    "lfm2.5-350m",
    "qwen3-0.6b",
    "transformers-cpu-reference",
}
REQUIRED_GATES = {
    "policy_accuracy",
    "protected_quality",
    "incorrect_local_answers",
    "p95_latency_ms",
    "peak_tree_rss_bytes",
}


def validate(path: Path = CONTRACT) -> dict:
    data = json.loads(path.read_text())
    if data.get("schema_version") != "1":
        raise ValueError("unsupported evaluation contract")
    candidates = data.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("candidates must be a list")
    ids = {candidate.get("id") for candidate in candidates}
    if ids != REQUIRED_CANDIDATES:
        raise ValueError("candidate comparison set is incomplete")
    if len(ids) != len(candidates):
        raise ValueError("candidate identifiers must be unique")
    statuses = {candidate.get("status") for candidate in candidates}
    if not {"unmeasured", "license-review-required"}.issubset(statuses):
        raise ValueError("unmeasured candidates must remain explicit")
    gates = data.get("gates")
    if not isinstance(gates, dict) or set(gates) != REQUIRED_GATES:
        raise ValueError("acceptance gates are incomplete")
    if gates["policy_accuracy"]["minimum"] != 1.0:
        raise ValueError("policy gate must be exact")
    if not gates["protected_quality"].get("requires_human_review"):
        raise ValueError("protected quality requires human review")
    if data.get("dataset") != "evaluation/seed.jsonl":
        raise ValueError("evaluation dataset is not pinned")
    dataset_rows, dataset_digest = validate_dataset(str(DATASET))
    if not dataset_rows:
        raise ValueError("evaluation dataset must not be empty")

    manifest = json.loads(MANIFEST.read_text())
    if manifest.get("schema_version") != "1":
        raise ValueError("unsupported dataset manifest")
    if manifest.get("source_path") != "evaluation/seed.jsonl":
        raise ValueError("dataset manifest source is not pinned")
    if manifest.get("source") != "omo-original-synthetic":
        raise ValueError("dataset manifest source is not original synthetic data")
    if manifest.get("license") != "Apache-2.0":
        raise ValueError("dataset manifest license is not approved")
    if manifest.get("revision_kind") != "sha256" or manifest.get("revision") != dataset_digest:
        raise ValueError("dataset manifest revision does not match source")
    if manifest.get("record_count") != len(dataset_rows):
        raise ValueError("dataset manifest record count does not match source")
    split_counts: dict[str, int] = {}
    for row in dataset_rows:
        split_counts[row.split] = split_counts.get(row.split, 0) + 1
    if split_counts != EXPECTED_SPLITS or manifest.get("splits") != EXPECTED_SPLITS:
        raise ValueError("dataset manifest split counts do not match source")
    if manifest.get("protected_split") != "test":
        raise ValueError("dataset protected split is not pinned")
    if manifest.get("protected_test_not_in_training") is not True:
        raise ValueError("dataset manifest must exclude protected test from training")
    if "pending human review" not in manifest.get("label_status", ""):
        raise ValueError("dataset review status must remain pending")
    if "local-only" not in manifest.get("publication_status", ""):
        raise ValueError("dataset publication status must remain local-only")
    validate_outcomes(str(OUTCOMES))
    return data


if __name__ == "__main__":
    validate()
    print("Evaluation candidate and gate contract passed")
