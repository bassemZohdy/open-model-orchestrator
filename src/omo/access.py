from __future__ import annotations

import hashlib
import hmac
import json
import math
import re
import sqlite3
import threading
from datetime import UTC, date, datetime
from typing import Literal, Self

import yaml
from pydantic import Field, model_validator

from omo.contracts import StrictModel

Retention = Literal["none", "provider_default", "unknown"]


class Caller(StrictModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")
    tenant: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")
    key_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    enabled: bool = True
    role: Literal["caller", "admin"] = "caller"
    max_cost_usd: float = Field(default=0.0, ge=0, le=1.0, allow_inf_nan=False)
    daily_budget_usd: float | None = Field(default=None, ge=0, le=1000, allow_inf_nan=False)
    allowed_retention: tuple[Retention, ...] = ("none",)
    allowed_hosts: tuple[str, ...] = ()

    @model_validator(mode="after")
    def require_egress_allowlist(self) -> Self:
        if self.enabled and self.max_cost_usd > 0 and not self.allowed_hosts:
            raise ValueError("callers with external budget require an egress host allowlist")
        for host in self.allowed_hosts:
            if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]{0,252}[a-z0-9])?", host):
                raise ValueError("egress hosts must be exact hostnames or IP addresses")
        return self


class AccessPolicy(StrictModel):
    schema_version: Literal["1"] = "1"
    callers: tuple[Caller, ...] = ()

    @model_validator(mode="after")
    def unique(self) -> Self:
        ids = [caller.id for caller in self.callers]
        hashes = [caller.key_sha256 for caller in self.callers]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate caller identifier")
        if len(set(hashes)) != len(hashes):
            raise ValueError("duplicate caller key hash")
        if len(self.callers) > 64:
            raise ValueError("at most 64 callers")
        return self


class AccessStore:
    def __init__(self, policy: AccessPolicy) -> None:
        self.policy = policy

    @staticmethod
    def read(path: str) -> AccessStore:
        from pathlib import Path

        file = Path(path)
        if file.stat().st_size > 65536:
            raise ValueError("access policy too large")
        parsed = yaml.safe_load(file.read_text())
        if not isinstance(parsed, dict):
            raise ValueError("access policy must be an object")
        return AccessStore(AccessPolicy.model_validate_json(json.dumps(parsed)))

    def authenticate(self, token: str) -> Caller | None:
        if not token or len(token) > 256:
            return None
        digest = hashlib.sha256(token.encode()).hexdigest()
        for caller in self.policy.callers:
            if caller.enabled and hmac.compare_digest(digest, caller.key_sha256):
                return caller
        return None


class BudgetLedger:
    """Bounded budget reservations with optional durable local persistence.

    The SQLite mode survives process restarts and uses an immediate transaction
    for multi-process correctness on one node. It is not a replacement for a
    managed distributed ledger or provider-billing reconciliation.
    """

    def __init__(self, db_path: str | None = None) -> None:
        self._reservations: dict[tuple[str, date], float] = {}
        self._lock = threading.Lock()
        self._db: sqlite3.Connection | None = None
        if db_path:
            self._db = sqlite3.connect(
                db_path, timeout=5, isolation_level=None, check_same_thread=False
            )
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS budget_reservations "
                "(caller_id TEXT NOT NULL, reservation_day TEXT NOT NULL, "
                "amount REAL NOT NULL, PRIMARY KEY (caller_id, reservation_day))"
            )

    def close(self) -> None:
        if self._db is not None:
            self._db.close()
            self._db = None

    def reserve(self, caller: Caller, amount: float, now: datetime | None = None) -> bool:
        if not math.isfinite(amount) or amount < 0:
            return False
        if caller.daily_budget_usd is None:
            return True
        current_time = datetime.now(UTC) if now is None else now
        day = current_time.date()
        key = (caller.id, day)
        with self._lock:
            if self._db is not None:
                try:
                    self._db.execute("BEGIN IMMEDIATE")
                    row = self._db.execute(
                        "SELECT amount FROM budget_reservations "
                        "WHERE caller_id = ? AND reservation_day = ?",
                        (caller.id, day.isoformat()),
                    ).fetchone()
                    reserved = float(row[0]) if row else 0.0
                    if reserved + amount > caller.daily_budget_usd:
                        self._db.rollback()
                        return False
                    self._db.execute(
                        "INSERT INTO budget_reservations(caller_id, reservation_day, amount) "
                        "VALUES (?, ?, ?) ON CONFLICT(caller_id, reservation_day) "
                        "DO UPDATE SET amount = excluded.amount",
                        (caller.id, day.isoformat(), reserved + amount),
                    )
                    self._db.commit()
                    return True
                except sqlite3.Error:
                    self._db.rollback()
                    return False
            self._reservations = {
                item: value for item, value in self._reservations.items() if item[1] == day
            }
            reserved = self._reservations.get(key, 0.0)
            if reserved + amount > caller.daily_budget_usd:
                return False
            self._reservations[key] = reserved + amount
            return True

    def snapshot(self, now: datetime | None = None) -> dict[str, float]:
        current_time = datetime.now(UTC) if now is None else now
        day = current_time.date()
        with self._lock:
            if self._db is not None:
                rows = self._db.execute(
                    "SELECT caller_id, amount FROM budget_reservations WHERE reservation_day = ?",
                    (day.isoformat(),),
                ).fetchall()
                return {str(caller): float(amount) for caller, amount in rows}
            return {
                caller: amount
                for (caller, reservation_day), amount in self._reservations.items()
                if reservation_day == day
            }
