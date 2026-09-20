"""Materialize one approved Hub model during a trusted build step only."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def materialize(config_path: Path, output: Path) -> dict[str, Any]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or config.get("enabled") is not True:
        raise ValueError("model promotion is disabled")
    candidate = config.get("candidate")
    if not isinstance(candidate, dict):
        raise ValueError("candidate configuration is required")
    repository = candidate.get("repository")
    revision = candidate.get("revision")
    filename = candidate.get("filename")
    expected_size = candidate.get("size_bytes")
    expected_hash = candidate.get("sha256")
    if not isinstance(repository, str) or not REPOSITORY_PATTERN.fullmatch(repository):
        raise ValueError("candidate repository is unsafe")
    if not isinstance(revision, str) or not SHA_PATTERN.fullmatch(revision):
        raise ValueError("candidate revision must be immutable")
    if not isinstance(filename, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", filename
    ):
        raise ValueError("candidate filename is unsafe")
    if not isinstance(expected_size, int) or expected_size <= 0:
        raise ValueError("candidate size must be positive")
    if not isinstance(expected_hash, str) or not HASH_PATTERN.fullmatch(expected_hash):
        raise ValueError("candidate SHA-256 is required")

    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://huggingface.co/{repository}/resolve/{revision}/{filename}?download=true"
    digest = hashlib.sha256()
    size = 0
    temporary: str | None = None
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as stream:
                temporary = stream.name
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    if size > expected_size:
                        raise ValueError("download exceeds manifest size")
                    digest.update(chunk)
                    stream.write(chunk)
        actual_hash = digest.hexdigest()
        if size != expected_size or actual_hash != expected_hash:
            raise ValueError("download does not match model manifest")
        os.replace(temporary, output)
        temporary = None
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)
    return {"path": str(output), "size_bytes": size, "sha256": expected_hash, "revision": revision}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "config/model-promotion.yaml")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(materialize(args.config, args.output))


if __name__ == "__main__":
    main()
