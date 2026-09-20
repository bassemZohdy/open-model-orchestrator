"""Validate the disabled-by-default fine-tuned model promotion contract."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/model-promotion.yaml"
ROLLBACK = ROOT / "models/manifest.json"
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
FILENAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return value


def validate(path: Path = CONFIG) -> dict[str, Any]:
    data = _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), "model promotion")
    if data.get("schema_version") != "1":
        raise ValueError("unsupported model promotion contract")
    candidate = _mapping(data.get("candidate"), "candidate")
    if candidate.get("repository") != "BassemZohdy/open-model-orchestrator":
        raise ValueError("candidate repository is not pinned")
    runtime = _mapping(data.get("runtime"), "runtime")
    if runtime.get("request_time_download") is not False:
        raise ValueError("request-time model downloads must remain disabled")
    if runtime.get("build_time_materialization") != "trusted-only":
        raise ValueError("model materialization must be trusted-only")
    rollback = _mapping(data.get("rollback"), "rollback")
    if rollback.get("manifest") != "models/manifest.json" or rollback.get("required") is not True:
        raise ValueError("upstream rollback manifest is required")

    if data.get("enabled") is False:
        if any(
            candidate.get(field) is not None
            for field in ("revision", "filename", "quantization", "size_bytes", "sha256")
        ):
            raise ValueError("disabled promotion cannot contain a candidate artifact")
        if candidate.get("format") != "safetensors":
            raise ValueError("disabled promotion format must remain safetensors")
    elif data.get("enabled") is True:
        if not SHA_PATTERN.fullmatch(str(candidate.get("revision", ""))):
            raise ValueError("candidate revision must be an immutable commit")
        if not FILENAME_PATTERN.fullmatch(str(candidate.get("filename", ""))):
            raise ValueError("candidate filename is unsafe")
        if candidate.get("format") != "safetensors":
            raise ValueError("candidate format must be safetensors")
        if not isinstance(candidate.get("quantization"), str) or not candidate["quantization"]:
            raise ValueError("candidate quantization is required")
        if candidate.get("template") != "chatml-explicit-v1":
            raise ValueError("candidate template is not supported")
        if not isinstance(candidate.get("size_bytes"), int) or candidate["size_bytes"] <= 0:
            raise ValueError("candidate size must be positive")
        if not HASH_PATTERN.fullmatch(str(candidate.get("sha256", ""))):
            raise ValueError("candidate SHA-256 is required")
    else:
        raise ValueError("enabled must be boolean")

    manifest = json.loads(ROLLBACK.read_text(encoding="utf-8"))
    if manifest.get("fine_tuned_by_omo") is not False:
        raise ValueError("rollback must remain an upstream model")
    return data


if __name__ == "__main__":
    result = validate()
    print(
        json.dumps(
            {
                "status": "validated",
                "enabled": result["enabled"],
                "request_time_download": result["runtime"]["request_time_download"],
            }
        )
    )
