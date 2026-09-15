from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal, Self

import yaml
from pydantic import Field, SecretStr, model_validator

from omo.contracts import StrictModel


class Settings(StrictModel):
    schema_version: Literal["1"] = "1"
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1024, le=65535)
    api_key: SecretStr | None = None
    model_path: str = "models/embedded.gguf"
    model_manifest: str = "models/manifest.json"
    registry_path: str = "config/registry.yaml"
    access_policy_path: str | None = None
    budget_db_path: str | None = None
    registry_reload_enabled: bool = False
    registry_max_age_seconds: int = Field(default=86400, ge=60, le=604800)
    threads: int = Field(default=4, ge=1, le=8)
    context_tokens: int = Field(default=2048, ge=1024, le=4096)
    analysis_tokens: int = Field(default=768, ge=128, le=1024)
    inference_queue: int = Field(default=4, ge=1, le=16)
    max_inflight: int = Field(default=8, ge=1, le=32)
    requests_per_minute: int = Field(default=120, ge=1, le=600)
    deadline_seconds: float = Field(default=20.0, ge=1.0, le=60.0)
    sandbox_enabled: bool = False
    external_enabled: bool = False
    external_max_cost_usd: float = Field(default=0.01, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def safe_bind(self) -> Self:
        if (
            self.host not in {"127.0.0.1", "::1", "localhost"}
            and not self.api_key
            and not self.access_policy_path
        ):
            raise ValueError("non-loopback binding requires OMO_API_KEY or access policy")
        if self.api_key and len(self.api_key.get_secret_value()) < 24:
            raise ValueError("API key must contain at least 24 characters")
        return self


def load_settings(path: str | None = None, overrides: dict[str, Any] | None = None) -> Settings:
    """Defaults < YAML < OMO_ environment < documented CLI overrides."""
    values: dict[str, Any] = {}
    if path:
        p = Path(path)
        if p.stat().st_size > 65536:
            raise ValueError("configuration too large")
        parsed = yaml.safe_load(p.read_text())
        if not isinstance(parsed, dict):
            raise ValueError("configuration must be an object")
        values.update(parsed)
    known = Settings.model_fields
    for key, value in os.environ.items():
        if not key.startswith("OMO_") or key.startswith("OMO_PROVIDER_KEY_"):
            continue
        name = key[4:].lower()
        if name not in known:
            raise ValueError(f"unknown configuration name: {key}")
        if name in {
            "api_key",
            "host",
            "model_path",
            "model_manifest",
            "registry_path",
            "access_policy_path",
            "budget_db_path",
            "schema_version",
        }:
            values[name] = value
        else:
            values[name] = json.loads(value)
    values.update(overrides or {})
    return Settings.model_validate(values)
