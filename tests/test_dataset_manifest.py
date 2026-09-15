from scripts.check_evaluation_contract import validate


def test_evaluation_contract_pins_expanded_dataset_manifest():
    contract = validate()

    assert contract["dataset"] == "evaluation/seed.jsonl"
