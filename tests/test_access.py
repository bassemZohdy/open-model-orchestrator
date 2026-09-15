import hashlib
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from omo.access import AccessPolicy, AccessStore, BudgetLedger, Caller


def caller(token="client-secret"):
    return Caller(
        id="client",
        tenant="tenant-a",
        key_sha256=hashlib.sha256(token.encode()).hexdigest(),
        max_cost_usd=0.01,
        daily_budget_usd=0.02,
        allowed_hosts=("provider.example",),
    )


def test_access_store_hashes_and_resolves_bearer_keys():
    client = caller()
    store = AccessStore(AccessPolicy(callers=(client,)))
    assert store.authenticate("client-secret") == client
    assert store.authenticate("wrong") is None
    assert store.authenticate("x" * 257) is None


def test_external_caller_requires_explicit_egress_allowlist():
    with pytest.raises(ValidationError, match="egress host allowlist"):
        Caller(
            id="client",
            tenant="tenant-a",
            key_sha256="a" * 64,
            max_cost_usd=0.01,
        )


def test_egress_allowlist_rejects_wildcards_and_urls():
    for host in ("*", "https://provider.example/v1", "provider.example/path"):
        with pytest.raises(ValidationError, match="exact hostnames"):
            Caller(
                id="client",
                tenant="tenant-a",
                key_sha256="a" * 64,
                max_cost_usd=0.01,
                allowed_hosts=(host,),
            )


def test_budget_ledger_reserves_bounded_daily_budget():
    client = caller()
    ledger = BudgetLedger()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    assert ledger.reserve(client, 0.01, now)
    assert ledger.reserve(client, 0.01, now)
    assert not ledger.reserve(client, 0.01, now)
    assert ledger.reserve(client, 0.01, now + timedelta(days=1))


def test_budget_ledger_can_persist_reservations(tmp_path):
    client = caller()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    path = tmp_path / "budget.sqlite3"
    first = BudgetLedger(str(path))
    assert first.reserve(client, 0.01, now)
    first.close()

    second = BudgetLedger(str(path))
    assert second.snapshot(now) == {"client": 0.01}
    assert second.reserve(client, 0.01, now)
    assert not second.reserve(client, 0.01, now)
    second.close()


def test_budget_ledger_rejects_non_finite_amounts():
    client = caller()
    ledger = BudgetLedger()
    assert not ledger.reserve(client, float("nan"))
    assert not ledger.reserve(client, float("inf"))
