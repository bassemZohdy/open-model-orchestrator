import hashlib
import json
from pathlib import Path

import pytest

from scripts.check_model_artifact import validate


def _file(root: Path, name: str, content: bytes) -> dict[str, object]:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return {
        "path": name,
        "size_bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def _manifest(root: Path) -> dict[str, object]:
    files = {
        "weights": _file(root, "model.safetensors", b"weights"),
        "tokenizer": _file(root, "tokenizer.json", b"{}"),
        "config": _file(root, "config.json", b"{}"),
        "model_card": _file(root, "README.md", b"# OMO model\n"),
    }
    return {
        "schema_version": "1",
        "kind": "omo-fine-tuned-model",
        "objective": "omo-routing-proposal-v1",
        "fine_tuned_by_omo": True,
        "artifact": {
            "format": "safetensors",
            "quantization": "Q4_K_M",
            "template": "chatml-explicit-v1",
            **files,
        },
        "lineage": {
            "code_commit": "a" * 40,
            "dataset_sha256": "b" * 64,
            "training_config_sha256": "c" * 64,
            "training_manifest_sha256": "d" * 64,
            "base_model": {
                "repository": "HuggingFaceTB/SmolLM2-360M-Instruct",
                "revision": "e" * 40,
            },
        },
        "evaluation": {
            "program_sha256": "f" * 64,
            "heldout_cases_sha256": "0" * 64,
            "protected_test_excluded": True,
            "metrics": {"validation_accuracy": 0.9},
            "human_review": "approved",
        },
        "license": {
            "model": "Apache-2.0",
            "dataset": "Apache-2.0",
            "source": "original-synthetic-reviewed-v1",
        },
        "rollback": {
            "manifest": "models/manifest.json",
            "upstream_model": True,
            "revision": "1" * 40,
        },
    }


def test_valid_model_artifact_is_evidence_bound(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))

    result = validate(manifest_path, tmp_path)

    assert result["status"] == "validated"
    assert (
        result["artifact"]["files"]["weights"]["sha256"] == hashlib.sha256(b"weights").hexdigest()
    )
    assert result["lineage"]["base_model"]["revision"] == "e" * 40


def test_artifact_rejects_modified_file(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    (tmp_path / "model.safetensors").write_bytes(b"changed")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))

    with pytest.raises(ValueError, match="size and SHA-256"):
        validate(manifest_path, tmp_path)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("fine_tuned_by_omo", False, "fine-tune"),
        ("protected_test_excluded", False, "protected test"),
        ("human_review", "pending", "human review"),
    ],
)
def test_artifact_rejects_unapproved_release_evidence(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    manifest = _manifest(tmp_path)
    if field in {"fine_tuned_by_omo"}:
        manifest[field] = value
    else:
        manifest["evaluation"][field] = value  # type: ignore[index]
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))

    with pytest.raises(ValueError, match=message):
        validate(manifest_path, tmp_path)


def test_artifact_rejects_path_traversal(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    manifest["artifact"]["weights"]["path"] = "../outside.safetensors"  # type: ignore[index]
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))

    with pytest.raises(ValueError, match="safe relative"):
        validate(manifest_path, tmp_path)
