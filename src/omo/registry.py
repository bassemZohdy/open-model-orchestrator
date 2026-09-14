from __future__ import annotations

import hashlib
import ipaddress
import json
import re
import time
from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit

import yaml
from pydantic import Field, model_validator

from omo.contracts import Capability, StrictModel


class ModelEntry(StrictModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")
    provider: Literal["openai_compatible", "openrouter"] = "openai_compatible"
    upstream_model: str = Field(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9_./:-]+$")
    base_url: str
    key_env: str = Field(pattern=r"^OMO_PROVIDER_KEY_[A-Z0-9_]+$")
    enabled: bool = False
    allow_private_endpoint: bool = False
    capabilities: tuple[Capability, ...] = ("text",)
    context_tokens: int = Field(ge=1024, le=2_000_000)
    max_output_tokens: int = Field(ge=8, le=65536)
    input_usd_per_million: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    output_usd_per_million: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    retention: Literal["none", "provider_default", "unknown"] = "unknown"
    priority: int = Field(default=100, ge=0, le=1000)
    available: bool = False
    supports_tools: bool = False
    supports_structured_output: bool = False
    tokenizer: Literal["utf8-byte-upper-bound"] = "utf8-byte-upper-bound"
    metadata_verified_at: str | None = None
    provenance: str = "administrator configured; quality unmeasured"
    evaluated_quality: float | None = Field(default=None, ge=0, le=1)
    observed_latency_ms: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def endpoint(self) -> Self:
        u = urlsplit(self.base_url)
        if not u.hostname or u.username or u.password or u.query or u.fragment:
            raise ValueError("endpoint must have a hostname and no credentials/query/fragment")
        if u.scheme != "https" and not (u.scheme == "http" and self.allow_private_endpoint):
            raise ValueError("TLS required except explicitly configured local endpoints")
        if not re.fullmatch(r"/[A-Za-z0-9_/-]*", u.path or "/"):
            raise ValueError("unsupported endpoint path")
        try:
            is_private = not ipaddress.ip_address(u.hostname).is_global
        except ValueError:
            is_private = u.hostname == "localhost" or u.hostname.endswith((".local", ".internal"))
        if is_private and not self.allow_private_endpoint:
            raise ValueError("private endpoint requires explicit administrator configuration")
        if self.provider == "openrouter" and self.base_url != "https://openrouter.ai/api/v1":
            raise ValueError("OpenRouter endpoint must match the official origin")
        return self


class Registry(StrictModel):
    schema_version: Literal["1"] = "1"
    version: str = Field(min_length=1, max_length=64)
    models: tuple[ModelEntry, ...] = ()

    @model_validator(mode="after")
    def unique(self) -> Self:
        if len({m.id for m in self.models}) != len(self.models):
            raise ValueError("duplicate model identifier")
        if len(self.models) > 32:
            raise ValueError("at most 32 configured models")
        return self

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()[:16]


class RegistryStore:
    def __init__(self, snapshot: Registry, source_path: str | None = None) -> None:
        self.snapshot = snapshot
        self.source_path = source_path
        self.loaded_at = time.time()
        self.last_reload_error: str | None = None
        self.last_reload_at = self.loaded_at

    @staticmethod
    def read(path: str) -> Registry:
        p = Path(path)
        if p.stat().st_size > 65536:
            raise ValueError("registry too large")
        # JSON mode permits tuple arrays while retaining strict scalar validation.
        return Registry.model_validate_json(json.dumps(yaml.safe_load(p.read_text())))

    def reload(self, path: str) -> None:
        try:
            replacement = self.read(path)
        except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
            self.last_reload_at = time.time()
            self.last_reload_error = type(exc).__name__
            raise
        self.snapshot = replacement  # Complete validated immutable snapshot, one atomic reference.
        self.source_path = path
        self.loaded_at = time.time()
        self.last_reload_at = self.loaded_at
        self.last_reload_error = None

    def try_reload(self, path: str) -> bool:
        try:
            self.reload(path)
        except (OSError, TypeError, ValueError, yaml.YAMLError):
            return False
        return True

    def refresh_if_stale(self, path: str, max_age_seconds: int, now: float | None = None) -> bool:
        if self.status(max_age_seconds, now)["fresh"]:
            return False
        return self.try_reload(path)

    def status(self, max_age_seconds: int, now: float | None = None) -> dict[str, object]:
        current = time.time() if now is None else now
        age = max(0.0, current - self.loaded_at)
        return {
            "version": self.snapshot.version,
            "digest": self.snapshot.digest,
            "age_seconds": round(age, 3),
            "fresh": age <= max_age_seconds,
            "last_reload_error": self.last_reload_error,
        }
