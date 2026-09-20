import json
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.promote_release import build as promote
from scripts.release_manifest import build as candidate


def _candidate(architecture: str) -> dict[str, object]:
    result = candidate(
        "a" * 40,
        "bzohdy/open-model-orchestrator",
        "sha256:" + architecture[0] * 64,
        architecture,
        "0.1.0-rc.1",
        Path("."),
    )
    result["publication_state"] = "candidate; stable aliases unchanged"
    return result


def test_candidate_binds_requested_version_and_model_manifest() -> None:
    result = _candidate("amd64")

    assert result["application_version"] == "0.1.0-rc.1"
    assert len(result["model_manifest_sha256"]) == 64


def test_candidate_rejects_whitespace_in_image_reference() -> None:
    with pytest.raises(ValueError, match="whitespace"):
        candidate(
            "a" * 40,
            "bzohdy/open model",
            "sha256:" + "a" * 64,
            "amd64",
            "0.1.0-rc.1",
        )


def test_promotion_requires_complete_matching_candidates(tmp_path: Path) -> None:
    amd64 = _candidate("amd64")
    arm64 = _candidate("arm64")
    evidence = {
        "schema_version": "1",
        "security_audit": {"status": "passed", "report_sha256": "1" * 64},
        "platforms": {
            "linux/amd64": {
                "sbom": {
                    "verified": True,
                    "sha256": "2" * 64,
                    "format": "spdx-json",
                    "image_digest": "sha256:" + "a" * 64,
                },
                "provenance": {
                    "verified": True,
                    "sha256": "3" * 64,
                    "builder": "github-actions",
                    "source_commit": "a" * 40,
                    "image_digest": "sha256:" + "a" * 64,
                },
                "signature": {
                    "verified": True,
                    "identity": "release-workflow",
                    "issuer": "sigstore",
                    "subject": "sha256:" + "a" * 64,
                },
            },
            "linux/arm64": {
                "sbom": {
                    "verified": True,
                    "sha256": "2" * 64,
                    "format": "spdx-json",
                    "image_digest": "sha256:" + "a" * 64,
                },
                "provenance": {
                    "verified": True,
                    "sha256": "3" * 64,
                    "builder": "github-actions",
                    "source_commit": "a" * 40,
                    "image_digest": "sha256:" + "a" * 64,
                },
                "signature": {
                    "verified": True,
                    "identity": "release-workflow",
                    "issuer": "sigstore",
                    "subject": "sha256:" + "a" * 64,
                },
            },
        },
    }

    amd64_path = tmp_path / "amd64.json"
    arm64_path = tmp_path / "arm64.json"
    evidence_path = tmp_path / "evidence.json"
    amd64_path.write_text(json.dumps(amd64))
    arm64_path.write_text(json.dumps(arm64))
    evidence_path.write_text(json.dumps(evidence))
    result = promote([amd64_path, arm64_path], evidence_path)

    assert result["publication_state"] == "stable"
    assert result["stable_aliases"] == ["latest", "0.1.0-rc.1"]

    incomplete = deepcopy(arm64)
    incomplete.pop("model_manifest_sha256")
    arm64_path.write_text(json.dumps(incomplete))
    with pytest.raises(ValueError, match="model_manifest_sha256"):
        promote([amd64_path, arm64_path], evidence_path)
