"""Validate a complete signed multi-platform candidate before stable promotion.

This command only writes a stable manifest. It does not publish tags or
credentials; those mutations remain behind the protected release environment.
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any

REQUIRED_PLATFORMS = {"linux/amd64", "linux/arm64"}
DIGEST_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")
COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def _required_string(
    manifest: dict[str, Any], field: str, pattern: re.Pattern[str] | None = None
) -> str:
    value = manifest.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"candidate field {field} is required")
    if pattern is not None and pattern.fullmatch(value) is None:
        raise ValueError(f"candidate field {field} has an invalid format")
    return value


def _validate_candidate(manifest: dict[str, Any]) -> None:
    _required_string(manifest, "platform")
    _required_string(manifest, "publication_state")
    _required_string(manifest, "requested_release_version")
    _required_string(manifest, "code_commit", COMMIT_PATTERN)
    _required_string(manifest, "image")
    _required_string(manifest, "image_digest", DIGEST_PATTERN)
    for field in (
        "dataset_sha256",
        "evaluation_program_sha256",
        "policy_sha256",
        "model_manifest_sha256",
    ):
        _required_string(manifest, field, SHA256_PATTERN)
    if not isinstance(manifest.get("embedded_model"), dict):
        raise ValueError("candidate field embedded_model must be an object")


def build(manifest_paths: list[Path], evidence_path: Path) -> dict[str, Any]:
    if len(manifest_paths) != 2:
        raise ValueError("stable promotion requires exactly two platform manifests")
    manifests = [_load(path) for path in manifest_paths]
    evidence = _load(evidence_path)
    platforms = {manifest.get("platform") for manifest in manifests}
    if platforms != REQUIRED_PLATFORMS:
        raise ValueError("stable promotion requires native AMD64 and ARM64 candidates")
    for manifest in manifests:
        _validate_candidate(manifest)
        if manifest.get("publication_state") != "candidate; stable aliases unchanged":
            raise ValueError("only candidate manifests may be promoted")
        if not re.fullmatch(
            r"\d+\.\d+\.\d+(?:-rc\.\d+)?",
            manifest.get("requested_release_version", ""),
        ):
            raise ValueError("candidate version is invalid")
    identity_fields = (
        "requested_release_version",
        "code_commit",
        "embedded_model",
        "dataset_sha256",
        "evaluation_program_sha256",
        "policy_sha256",
        "model_manifest_sha256",
    )
    first = manifests[0]
    for field in identity_fields:
        if any(manifest.get(field) != first.get(field) for manifest in manifests[1:]):
            raise ValueError(f"candidate identity differs for {field}")
    if evidence != {
        "security_audit": "passed",
        "sbom_verified": True,
        "provenance_verified": True,
        "signatures_verified": True,
    }:
        raise ValueError("release evidence is incomplete or failed")
    return {
        "schema_version": "1",
        "publication_state": "stable",
        "release_version": first["requested_release_version"],
        "code_commit": first["code_commit"],
        "embedded_model": first["embedded_model"],
        "dataset_sha256": first["dataset_sha256"],
        "evaluation_program_sha256": first["evaluation_program_sha256"],
        "policy_sha256": first["policy_sha256"],
        "platforms": [
            {
                "platform": manifest["platform"],
                "image": manifest["image"],
                "image_digest": manifest["image_digest"],
            }
            for manifest in sorted(manifests, key=lambda item: item["platform"])
        ],
        "security_audit": "passed",
        "attestations": {
            "sbom_verified": True,
            "provenance_verified": True,
            "signature_verified": True,
        },
        "stable_aliases": ["latest", first["requested_release_version"]],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, action="append", required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.manifest, args.evidence)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": "validated", "publication_state": "stable"}))
