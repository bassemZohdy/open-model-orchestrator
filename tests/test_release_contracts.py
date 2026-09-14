from pathlib import Path

import pytest

from scripts.check_evaluation_contract import validate as validate_evaluation
from scripts.check_publication_contract import validate as validate_publication


def test_evaluation_contract_is_predeclared():
    data = validate_evaluation()
    assert data["candidates"][0]["status"] == "measured-development-only"


def test_publication_contract_is_disabled_and_pinned():
    config = validate_publication()
    assert config["enabled"] is False


def test_publication_contract_rejects_relabeling(tmp_path):
    path = tmp_path / "publication.yaml"
    path.write_text(
        Path("config/publication.yaml")
        .read_text()
        .replace("fine_tuned_by_omo: false", "fine_tuned_by_omo: true")
    )
    with pytest.raises(ValueError, match="relabel"):
        validate_publication(path)
