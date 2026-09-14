"""Budget-free local preparation. Actual tuning remains explicitly unavailable."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.dataset import validate  # noqa: E402, I001


DEFAULT_CONFIG = ROOT / "config/training.yaml"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_plan(config_path: Path = DEFAULT_CONFIG) -> dict:
    if config_path.stat().st_size > 65536:
        raise ValueError("training configuration too large")
    config = yaml.safe_load(config_path.read_text())
    if not isinstance(config, dict):
        raise ValueError("training configuration must be an object")
    if config.get("schema_version") != "1":
        raise ValueError("unsupported training configuration")
    if config.get("enabled") is not False or config.get("execution") != "dry-run-only":
        raise ValueError("training execution must remain disabled")
    dataset = ROOT / config["dataset"]["path"]
    rows, dataset_digest = validate(str(dataset))
    return {
        "config": config,
        "config_sha256": _digest(config_path),
        "dataset_sha256": dataset_digest,
        "dataset_records": len(rows),
        "train_examples": sum(r.split == "train" for r in rows),
        "base_model": config["base_model"],
    }


def main() -> None:
    p = argparse.ArgumentParser(
        description="Prepare an offline SFT experiment; never creates a remote job"
    )
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = p.parse_args()
    plan = load_plan(args.config)
    if not args.dry_run:
        raise SystemExit(
            "Training is disabled: select and validate the isolated training stack, "
            "export path and owner-approved budget first. See TODO OMO-008."
        )
    print(
        json.dumps(
            {
                "status": "dry-run-only",
                "training_enabled": False,
                "remote_jobs_enabled": False,
                "automatic_promotion": False,
                "config_sha256": plan["config_sha256"],
                "dataset_sha256": plan["dataset_sha256"],
                "dataset_records": plan["dataset_records"],
                "train_examples": plan["train_examples"],
                "base_model": plan["base_model"],
                "proposal": {
                    "method": "full supervised fine-tuning baseline before comparing adapters",
                    **plan["config"]["limits"],
                },
                "export": plan["config"]["export"],
                "lineage": {
                    "dataset_path": plan["config"]["dataset"]["path"],
                    "base_model_revision": plan["base_model"]["revision"],
                    "rollback_manifest_required": True,
                },
                "not_implemented": [
                    "training execution",
                    "export",
                    "quantization regression",
                    "promotion",
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
