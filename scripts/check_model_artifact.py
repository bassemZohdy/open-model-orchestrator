"""Validate one immutable, evidence-bound OMO model artifact bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OBJECTIVE = "omo-routing-proposal-v1"
SHA1_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_FORMAT = "safetensors"
ALLOWED_QUANTIZATIONS = frozenset({"fp16", "Q8_0", "Q4_K_M"})
MAX_MANIFEST_BYTES = 128_000


def _load(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if len(raw) > MAX_MANIFEST_BYTES:
        raise ValueError("model artifact manifest exceeds 128 KB")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("model artifact manifest must be an object")
    return value


def _required_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _required_sha(value: Any, field: str, pattern: re.Pattern[str]) -> str:
    result = _required_string(value, field).lower()
    if pattern.fullmatch(result) is None:
        raise ValueError(f"{field} has an invalid checksum")
    return result


def _safe_relative_path(value: Any, field: str) -> Path:
    raw = _required_string(value, field)
    path = Path(raw)
    if path.is_absolute() or ".." in path.parts or raw.endswith("/"):
        raise ValueError(f"{field} must be a safe relative file path")
    return path


def _validate_file(descriptor: Any, field: str, artifact_root: Path) -> dict[str, Any]:
    if not isinstance(descriptor, dict):
        raise ValueError(f"{field} must be an object")
    relative_path = _safe_relative_path(descriptor.get("path"), f"{field}.path")
    expected_size = descriptor.get("size_bytes")
    if isinstance(expected_size, bool) or not isinstance(expected_size, int) or expected_size <= 0:
        raise ValueError(f"{field}.size_bytes must be a positive integer")
    expected_sha = _required_sha(descriptor.get("sha256"), f"{field}.sha256", SHA256_PATTERN)

    root = artifact_root.resolve()
    actual_path = (root / relative_path).resolve()
    try:
        actual_path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{field}.path escapes the artifact root") from exc
    if not actual_path.is_file():
        raise ValueError(f"{field}.path does not identify a file")

    data = actual_path.read_bytes()
    actual_sha = hashlib.sha256(data).hexdigest()
    if len(data) != expected_size or actual_sha != expected_sha:
        raise ValueError(f"{field} does not match the recorded size and SHA-256")
    return {
        "path": relative_path.as_posix(),
        "size_bytes": expected_size,
        "sha256": expected_sha,
    }


def validate(manifest_path: Path, artifact_root: Path) -> dict[str, Any]:
    manifest = _load(manifest_path)
    if manifest.get("schema_version") != "1":
        raise ValueError("unsupported model artifact manifest")
    if manifest.get("kind") != "omo-fine-tuned-model":
        raise ValueError("artifact kind must identify an OMO fine-tuned model")
    if manifest.get("objective") != OBJECTIVE:
        raise ValueError("artifact objective differs from the runtime contract")
    if manifest.get("fine_tuned_by_omo") is not True:
        raise ValueError("artifact must explicitly identify an OMO fine-tune")

    artifact = manifest.get("artifact")
    if not isinstance(artifact, dict):
        raise ValueError("artifact metadata is required")
    if artifact.get("format") != ALLOWED_FORMAT:
        raise ValueError("artifact format must be safetensors")
    quantization = _required_string(artifact.get("quantization"), "artifact.quantization")
    if quantization not in ALLOWED_QUANTIZATIONS:
        raise ValueError("artifact quantization is not approved")
    template = _required_string(artifact.get("template"), "artifact.template")
    files = {
        name: _validate_file(artifact.get(name), f"artifact.{name}", artifact_root)
        for name in ("weights", "tokenizer", "config", "model_card")
    }

    lineage = manifest.get("lineage")
    if not isinstance(lineage, dict):
        raise ValueError("lineage is required")
    code_commit = _required_sha(lineage.get("code_commit"), "lineage.code_commit", SHA1_PATTERN)
    dataset_sha = _required_sha(
        lineage.get("dataset_sha256"), "lineage.dataset_sha256", SHA256_PATTERN
    )
    training_config_sha = _required_sha(
        lineage.get("training_config_sha256"),
        "lineage.training_config_sha256",
        SHA256_PATTERN,
    )
    training_manifest_sha = _required_sha(
        lineage.get("training_manifest_sha256"),
        "lineage.training_manifest_sha256",
        SHA256_PATTERN,
    )
    base_model = lineage.get("base_model")
    if not isinstance(base_model, dict):
        raise ValueError("lineage.base_model is required")
    base_model_repository = _required_string(
        base_model.get("repository"), "lineage.base_model.repository"
    )
    base_model_revision = _required_sha(
        base_model.get("revision"), "lineage.base_model.revision", SHA1_PATTERN
    )

    evaluation = manifest.get("evaluation")
    if not isinstance(evaluation, dict):
        raise ValueError("evaluation evidence is required")
    evaluation_program_sha = _required_sha(
        evaluation.get("program_sha256"),
        "evaluation.program_sha256",
        SHA256_PATTERN,
    )
    heldout_sha = _required_sha(
        evaluation.get("heldout_cases_sha256"),
        "evaluation.heldout_cases_sha256",
        SHA256_PATTERN,
    )
    if evaluation.get("protected_test_excluded") is not True:
        raise ValueError("protected test data must be excluded")
    metrics = evaluation.get("metrics")
    if not isinstance(metrics, dict) or not metrics:
        raise ValueError("evaluation.metrics must contain measured results")
    if evaluation.get("human_review") != "approved":
        raise ValueError("human review approval is required")

    license_data = manifest.get("license")
    if not isinstance(license_data, dict):
        raise ValueError("license provenance is required")
    model_license = _required_string(license_data.get("model"), "license.model")
    dataset_license = _required_string(license_data.get("dataset"), "license.dataset")
    source_provenance = _required_string(license_data.get("source"), "license.source")

    rollback = manifest.get("rollback")
    if not isinstance(rollback, dict):
        raise ValueError("rollback metadata is required")
    if rollback.get("manifest") != "models/manifest.json":
        raise ValueError("rollback must point to the upstream model manifest")
    if rollback.get("upstream_model") is not True:
        raise ValueError("rollback target must remain an upstream model")
    rollback_revision = _required_sha(rollback.get("revision"), "rollback.revision", SHA1_PATTERN)

    return {
        "status": "validated",
        "schema_version": manifest["schema_version"],
        "objective": OBJECTIVE,
        "fine_tuned_by_omo": True,
        "artifact": {
            "format": ALLOWED_FORMAT,
            "quantization": quantization,
            "template": template,
            "files": files,
        },
        "lineage": {
            "code_commit": code_commit,
            "dataset_sha256": dataset_sha,
            "training_config_sha256": training_config_sha,
            "training_manifest_sha256": training_manifest_sha,
            "base_model": {
                "repository": base_model_repository,
                "revision": base_model_revision,
            },
        },
        "evaluation": {
            "program_sha256": evaluation_program_sha,
            "heldout_cases_sha256": heldout_sha,
            "protected_test_excluded": True,
            "metrics": metrics,
            "human_review": "approved",
        },
        "license": {
            "model": model_license,
            "dataset": dataset_license,
            "source": source_provenance,
        },
        "rollback": {
            "manifest": "models/manifest.json",
            "upstream_model": True,
            "revision": rollback_revision,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(validate(args.manifest, args.artifact_root), sort_keys=True))


if __name__ == "__main__":
    main()
