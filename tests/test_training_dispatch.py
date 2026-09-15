import pytest

from scripts.check_training_dispatch import validate


REVISION = "a" * 40


def _valid(**overrides: str) -> dict[str, str]:
    values = {
        "code_sha": REVISION,
        "dataset_revision": "b" * 40,
        "base_model_revision": "c" * 40,
        "method": "full-sft",
        "hardware": "cpu-small",
        "execution_backend": "huggingface-job",
        "timeout_minutes": "15",
        "max_cost_usd": "0",
        "resume_run_id": "none",
        "dry_run": "true",
    }
    values.update(overrides)
    return values


def test_manual_plan_requires_exact_revisions_and_stays_dry_run() -> None:
    plan = validate(**_valid())
    assert plan["code_sha"] == REVISION
    assert plan["dry_run"] is True
    assert plan["automatic_promotion"] is False


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("code_sha", "main"),
        ("dataset_revision", "latest"),
        ("base_model_revision", "deadbeef"),
        ("resume_run_id", "not valid"),
    ],
)
def test_unpinned_or_unsafe_identifiers_fail_closed(field: str, value: str) -> None:
    with pytest.raises(ValueError):
        validate(**_valid(**{field: value}))


def test_non_dry_run_is_blocked_until_owner_gates_pass() -> None:
    with pytest.raises(ValueError, match="disabled"):
        validate(**_valid(dry_run="false"))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("timeout_minutes", "0"),
        ("timeout_minutes", "1441"),
        ("max_cost_usd", "-1"),
        ("max_cost_usd", "1001"),
        ("max_cost_usd", "NaN"),
    ],
)
def test_runtime_and_cost_bounds_are_enforced(field: str, value: str) -> None:
    with pytest.raises(ValueError):
        validate(**_valid(**{field: value}))
