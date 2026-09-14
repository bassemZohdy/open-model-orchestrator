import json

import pytest

from scripts.promote_release import build


def candidate(platform):
    return {
        "publication_state": "candidate; stable aliases unchanged",
        "requested_release_version": "0.1.0-rc.1",
        "code_commit": "a" * 40,
        "embedded_model": {"revision": "model-revision", "sha256": "b" * 64},
        "dataset_sha256": "c" * 64,
        "evaluation_program_sha256": "d" * 64,
        "policy_sha256": "e" * 64,
        "platform": platform,
        "image": "example/omo",
        "image_digest": "sha256:" + "f" * 64,
    }


def write_json(path, value):
    path.write_text(json.dumps(value))
    return path


def evidence():
    return {
        "security_audit": "passed",
        "sbom_verified": True,
        "provenance_verified": True,
        "signatures_verified": True,
    }


def test_promotion_requires_complete_evidence(tmp_path):
    amd = write_json(tmp_path / "amd.json", candidate("linux/amd64"))
    arm = write_json(tmp_path / "arm.json", candidate("linux/arm64"))
    ev = write_json(tmp_path / "evidence.json", {**evidence(), "signatures_verified": False})
    with pytest.raises(ValueError, match="incomplete"):
        build([amd, arm], ev)


def test_promotion_binds_both_platforms_and_identity(tmp_path):
    amd = write_json(tmp_path / "amd.json", candidate("linux/amd64"))
    arm = write_json(tmp_path / "arm.json", candidate("linux/arm64"))
    ev = write_json(tmp_path / "evidence.json", evidence())
    result = build([amd, arm], ev)
    assert result["publication_state"] == "stable"
    assert {item["platform"] for item in result["platforms"]} == {
        "linux/amd64",
        "linux/arm64",
    }
