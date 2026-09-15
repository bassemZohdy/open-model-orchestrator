"""Validate the disabled, lineage-bound training preparation contract."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from omo.classification import CLASSIFICATION_OBJECTIVE_ID
from training.sft import load_plan

CONFIG = Path("config/training.yaml")

plan = load_plan(CONFIG)
config = plan["config"]
assert config["enabled"] is False
assert config["execution"] == "dry-run-only"
assert config["objective"]["id"] == CLASSIFICATION_OBJECTIVE_ID
assert config["objective"]["local_answer_training"] == "excluded"
assert config["limits"]["max_cost_usd"] == 0
assert config["dataset"]["required_source"] == "omo-original-synthetic"
assert config["dataset"]["required_license"] == "Apache-2.0"
assert config["dataset"]["training_splits"] == ["train"]
assert config["dataset"]["protected_splits"] == ["test"]
assert plan["training_artifact"]["protected_test_included"] is False
assert config["export"]["require_lineage"] is True
assert config["export"]["require_rollback_manifest"] is True
assert config["export"]["output_root"].startswith("artifacts/")
print("Training preparation contract passed; execution remains disabled")
