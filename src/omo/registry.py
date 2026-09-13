from __future__ import annotations

import hashlib
import ipaddress
import json
import re
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
    def __init__(self, snapshot: Registry) -> None:
        self.snapshot = snapshot

    @staticmethod
    def read(path: str) -> Registry:
        p = Path(path)
        if p.stat().st_size > 65536:
            raise ValueError("registry too large")
        # JSON mode permits tuple arrays while retaining strict scalar validation.
        return Registry.model_validate_json(json.dumps(yaml.safe_load(p.read_text())))

    def reload(self, path: str) -> None:
        replacement = self.read(path)
        self.snapshot = replacement  # Complete validated immutable snapshot, one atomic reference.
