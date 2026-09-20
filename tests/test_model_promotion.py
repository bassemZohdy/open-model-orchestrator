from pathlib import Path

import pytest
import yaml

from scripts.check_model_promotion import validate
from scripts.materialize_model import materialize


def test_model_promotion_contract_is_disabled_and_pinned() -> None:
    config = validate()

    assert config["enabled"] is False
    assert config["runtime"]["request_time_download"] is False
    assert config["rollback"]["manifest"] == "models/manifest.json"


def test_enabled_promotion_requires_complete_immutable_candidate(tmp_path: Path) -> None:
    config = yaml.safe_load(Path("config/model-promotion.yaml").read_text())
    config["enabled"] = True
    config["candidate"]["revision"] = "a" * 40
    config["candidate"]["filename"] = "model.safetensors"
    config["candidate"]["quantization"] = "fp16"
    config["candidate"]["size_bytes"] = None
    config["candidate"]["sha256"] = None
    path = tmp_path / "model-promotion.yaml"
    path.write_text(yaml.safe_dump(config))

    with pytest.raises(ValueError, match="size"):
        validate(path)


def test_materialization_never_downloads_when_disabled(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="disabled"):
        materialize(Path("config/model-promotion.yaml"), tmp_path / "model.safetensors")
