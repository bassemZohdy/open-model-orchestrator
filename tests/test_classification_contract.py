import pytest
from pydantic import ValidationError

from omo.contracts import Proposal


def test_proposal_contract_check_passes() -> None:
    from scripts.check_classification_contract import validate

    data = validate()
    assert data["objective"] == "omo-routing-classification-v1"


@pytest.mark.parametrize(
    "proposal",
    [
        {"schema_version": "1", "action": "helper", "capability": "text"},
        {
            "schema_version": "1",
            "action": "external_model",
            "capability": "text",
            "helper": {"id": "even_squares", "values": [2]},
        },
        {"schema_version": "1", "action": "external_model", "capability": "text", "extra": "nope"},
    ],
)
def test_invalid_model_proposals_fail_closed(proposal: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Proposal.model_validate(proposal)
