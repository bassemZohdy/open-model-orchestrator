"""Validate publication identity without creating or uploading repositories."""

from pathlib import Path

import yaml

MANIFEST = Path("models/manifest.json")
CONFIG = Path("config/publication.yaml")


def validate(config_path: Path = CONFIG, manifest_path: Path = MANIFEST) -> dict:
    config = yaml.safe_load(config_path.read_text())
    manifest = __import__("json").loads(manifest_path.read_text())
    if config.get("schema_version") != "1" or config.get("enabled") is not False:
        raise ValueError("publication must remain disabled until authority is verified")
    authority = config.get("publisher_authority", {})
    if authority != {
        "required": True,
        "trusted_publisher": True,
        "runtime_credentials_separate": True,
    }:
        raise ValueError("publisher authority contract is incomplete")
    model = config["targets"]["model"]
    if model["repository"] != "BassemZohdy/open-model-orchestrator":
        raise ValueError("unexpected model repository")
    if (
        model["source_repository"] != manifest["repo_id"]
        or model["source_revision"] != manifest["revision"]
    ):
        raise ValueError("model identity is not bound to the pinned artifact")
    if model["fine_tuned_by_omo"] is not False:
        raise ValueError("upstream weights must not be relabeled as an OMO fine-tune")
    dataset = config["targets"]["dataset"]
    if dataset["repository"] != "BassemZohdy/open-model-orchestrator-dataset":
        raise ValueError("unexpected dataset repository")
    if dataset["immutable_revisions_required"] is not True:
        raise ValueError("dataset revisions must be immutable")
    return config


if __name__ == "__main__":
    validate()
    print("HF publication identity contract passed; publishing remains disabled")
