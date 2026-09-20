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
        "model_manifest_sha256": "a" * 64,
        "platform": platform,
        "image": "example/omo",
        "image_digest": "sha256:" + "f" * 64,
    }


def write_json(path, value):
    path.write_text(json.dumps(value))
    return path


def evidence():
    return {
        "schema_version": "1",
        "security_audit": {"status": "passed", "report_sha256": "1" * 64},
        "platforms": {
            platform: {
                "sbom": {
                    "verified": True,
                    "sha256": "2" * 64,
                    "format": "spdx-json",
                    "image_digest": "sha256:" + "f" * 64,
                },
                "provenance": {
                    "verified": True,
                    "sha256": "3" * 64,
                    "builder": "https://github.com/actions/runner",
                    "source_commit": "a" * 40,
                    "image_digest": "sha256:" + "f" * 64,
                },
                "signature": {
                    "verified": True,
                    "identity": "https://github.com/bassemZohdy/open-model-orchestrator/.github/workflows/release.yml@refs/heads/main",
                    "issuer": "https://token.actions.githubusercontent.com",
                    "subject": "sha256:" + "f" * 64,
                },
            }
            for platform in ("linux/amd64", "linux/arm64")
        },
    }


def test_promotion_requires_complete_evidence(tmp_path):
    amd = write_json(tmp_path / "amd.json", candidate("linux/amd64"))
    arm = write_json(tmp_path / "arm.json", candidate("linux/arm64"))
    invalid = evidence()
    invalid["platforms"]["linux/amd64"]["signature"]["verified"] = False
    ev = write_json(tmp_path / "evidence.json", invalid)
    with pytest.raises(ValueError, match="must be true"):
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


@pytest.mark.parametrize("field", ["sbom", "provenance", "signature"])
def test_promotion_rejects_evidence_detached_from_image(tmp_path, field):
    amd = write_json(tmp_path / "amd.json", candidate("linux/amd64"))
    arm = write_json(tmp_path / "arm.json", candidate("linux/arm64"))
    invalid = evidence()
    invalid["platforms"]["linux/arm64"][field][
        "image_digest" if field != "signature" else "subject"
    ] = "sha256:" + "0" * 64
    ev = write_json(tmp_path / "evidence.json", invalid)
    with pytest.raises(ValueError, match="does not match image"):
        build([amd, arm], ev)
