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
OUTCOMES = ROOT / "evaluation/outcomes.example.jsonl"
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
    dataset_rows, _ = validate_dataset(str(DATASET))
    if not dataset_rows:
        raise ValueError("evaluation dataset must not be empty")
    validate_outcomes(str(OUTCOMES))
    return data


if __name__ == "__main__":
    validate()
    print("Evaluation candidate and gate contract passed")
