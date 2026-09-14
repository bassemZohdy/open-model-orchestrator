from __future__ import annotations

import hashlib
import hmac
import json
import re
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
    """Bounded in-memory reservations; no prompt or provider response is retained."""

    def __init__(self) -> None:
        self._reservations: dict[tuple[str, date], float] = {}
        self._lock = threading.Lock()

    def reserve(self, caller: Caller, amount: float, now: datetime | None = None) -> bool:
        if caller.daily_budget_usd is None:
            return True
        current_time = datetime.now(UTC) if now is None else now
        day = current_time.date()
        key = (caller.id, day)
        with self._lock:
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
            return {
                caller: amount
                for (caller, reservation_day), amount in self._reservations.items()
                if reservation_day == day
            }
