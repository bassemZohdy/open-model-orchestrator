"""Validate the disabled, lineage-bound training preparation contract."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from omo.classification import CLASSIFICATION_OBJECTIVE_ID
from training.sft import load_plan

CONFIG = Path("config/training.yaml")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


plan = load_plan(CONFIG)
config = plan["config"]
require(config["enabled"] is False, "training must remain disabled")
require(config["execution"] == "dry-run-only", "training must remain dry-run-only")
require(config["objective"]["id"] == CLASSIFICATION_OBJECTIVE_ID, "training objective drifted")
require(
    config["objective"]["local_answer_training"] == "excluded",
    "local-answer training must remain excluded",
)
require(config["limits"]["max_cost_usd"] == 0, "training must have zero cost limit")
require(
    config["dataset"]["required_source"] == "omo-original-synthetic",
    "training source drifted",
)
require(config["dataset"]["required_license"] == "Apache-2.0", "training license drifted")
require(config["dataset"]["training_splits"] == ["train"], "training split is invalid")
require(config["dataset"]["protected_splits"] == ["test"], "protected split is invalid")
require(
    plan["training_artifact"]["protected_test_included"] is False,
    "protected test data entered the training artifact",
)
require(config["export"]["require_lineage"] is True, "training lineage is not required")
require(
    config["export"]["require_rollback_manifest"] is True,
    "training rollback manifest is not required",
)
require(
    config["export"]["output_root"].startswith("artifacts/"), "training output escaped artifacts"
)
print("Training preparation contract passed; execution remains disabled")
