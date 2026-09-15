import pytest
from pydantic import ValidationError

from omo.classification import parse_proposal, serialize_messages
from omo.contracts import Message, Proposal


def test_proposal_contract_check_passes() -> None:
    from scripts.check_classification_contract import validate

    data = validate()
    assert data["objective"] == "omo-routing-classification-v1"


def test_serialization_preserves_roles_and_order() -> None:
    messages = [
        Message(role="system", content="You are a router."),
        Message(role="user", content="Calculate this."),
        Message(role="assistant", content="What values?"),
        Message(role="user", content="2 and 4."),
    ]

    assert serialize_messages(messages) == (
        '[{"role":"system","content":"You are a router."},'
        '{"role":"user","content":"Calculate this."},'
        '{"role":"assistant","content":"What values?"},'
        '{"role":"user","content":"2 and 4."}]'
    )


def test_serialization_rejects_non_final_user_and_late_system() -> None:
    with pytest.raises(ValueError, match="final"):
        serialize_messages([Message(role="assistant", content="answer")])
    with pytest.raises(ValueError, match="system"):
        serialize_messages(
            [
                Message(role="user", content="first"),
                Message(role="system", content="late"),
            ]
        )


def test_proposal_parser_rejects_duplicate_keys_and_extra_fields() -> None:
    with pytest.raises(ValueError, match="invalid"):
        parse_proposal(
            '{"schema_version":"1","action":"clarify",'
            '"action":"external_model","capability":"text"}'
        )
    with pytest.raises(ValidationError):
        Proposal.model_validate(
            {"schema_version": "1", "action": "clarify", "capability": "text", "extra": True}
        )


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
