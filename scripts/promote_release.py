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


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def build(manifest_paths: list[Path], evidence_path: Path) -> dict[str, Any]:
    if len(manifest_paths) != 2:
        raise ValueError("stable promotion requires exactly two platform manifests")
    manifests = [_load(path) for path in manifest_paths]
    evidence = _load(evidence_path)
    platforms = {manifest.get("platform") for manifest in manifests}
    if platforms != REQUIRED_PLATFORMS:
        raise ValueError("stable promotion requires native AMD64 and ARM64 candidates")
    for manifest in manifests:
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
