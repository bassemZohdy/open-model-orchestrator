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


def _required_object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"release evidence field {field} must be an object")
    return value


def _required_sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
        raise ValueError(f"release evidence field {field} must be a SHA-256 digest")
    return value


def _required_true(value: Any, field: str) -> None:
    if value is not True:
        raise ValueError(f"release evidence field {field} must be true")


def _validate_evidence(evidence: dict[str, Any], manifests: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate digest-bound evidence produced by an external release verifier.

    The verifier that creates this file remains owner-controlled. This boundary
    deliberately records the identity and issuer used for signatures instead of
    accepting standalone booleans that could be detached from the candidates.
    """
    if evidence.get("schema_version") != "1":
        raise ValueError("release evidence schema_version must be 1")
    security = _required_object(evidence.get("security_audit"), "security_audit")
    if security.get("status") != "passed":
        raise ValueError("release security audit is not passed")
    report_sha256 = _required_sha256(security.get("report_sha256"), "security_audit.report_sha256")

    platform_evidence = _required_object(evidence.get("platforms"), "platforms")
    expected_platforms = {manifest["platform"] for manifest in manifests}
    if set(platform_evidence) != expected_platforms:
        raise ValueError("release evidence must cover exactly both candidate platforms")

    normalized_platforms: dict[str, dict[str, Any]] = {}
    for manifest in manifests:
        platform = manifest["platform"]
        item = _required_object(platform_evidence.get(platform), f"platforms.{platform}")
        sbom = _required_object(item.get("sbom"), f"platforms.{platform}.sbom")
        _required_true(sbom.get("verified"), f"platforms.{platform}.sbom.verified")
        sbom_sha256 = _required_sha256(sbom.get("sha256"), f"platforms.{platform}.sbom.sha256")
        sbom_format = sbom.get("format")
        if not isinstance(sbom_format, str) or not sbom_format:
            raise ValueError(f"platforms.{platform}.sbom.format is required")
        if sbom.get("image_digest") != manifest["image_digest"]:
            raise ValueError(f"platforms.{platform}.sbom.image_digest does not match image")

        provenance = _required_object(item.get("provenance"), f"platforms.{platform}.provenance")
        _required_true(provenance.get("verified"), f"platforms.{platform}.provenance.verified")
        provenance_sha256 = _required_sha256(
            provenance.get("sha256"), f"platforms.{platform}.provenance.sha256"
        )
        builder = provenance.get("builder")
        if not isinstance(builder, str) or not builder:
            raise ValueError(f"platforms.{platform}.provenance.builder is required")
        if provenance.get("source_commit") != manifest["code_commit"]:
            raise ValueError(f"platforms.{platform}.provenance.source_commit does not match code")
        if provenance.get("image_digest") != manifest["image_digest"]:
            raise ValueError(f"platforms.{platform}.provenance.image_digest does not match image")

        signature = _required_object(item.get("signature"), f"platforms.{platform}.signature")
        _required_true(signature.get("verified"), f"platforms.{platform}.signature.verified")
        identity = signature.get("identity")
        issuer = signature.get("issuer")
        if not isinstance(identity, str) or not identity:
            raise ValueError(f"platforms.{platform}.signature.identity is required")
        if not isinstance(issuer, str) or not issuer:
            raise ValueError(f"platforms.{platform}.signature.issuer is required")
        if signature.get("subject") != manifest["image_digest"]:
            raise ValueError(f"platforms.{platform}.signature.subject does not match image")

        normalized_platforms[platform] = {
            "sbom": {
                "sha256": sbom_sha256,
                "format": sbom_format,
                "image_digest": manifest["image_digest"],
            },
            "provenance": {
                "sha256": provenance_sha256,
                "builder": builder,
                "source_commit": manifest["code_commit"],
                "image_digest": manifest["image_digest"],
            },
            "signature": {
                "identity": identity,
                "issuer": issuer,
                "subject": manifest["image_digest"],
            },
        }
    return {
        "security_audit": {"status": "passed", "report_sha256": report_sha256},
        "platforms": normalized_platforms,
    }


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
    evidence_record = _validate_evidence(evidence, manifests)
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
        "security_audit": evidence_record["security_audit"],
        "attestations": evidence_record["platforms"],
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
