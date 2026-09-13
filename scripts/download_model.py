#!/usr/bin/env python3
"""Offline build/setup operation; runtime never downloads artifacts."""

import argparse
import hashlib
import json
import os
import urllib.request
from pathlib import Path


def download(manifest_path="models/manifest.json", destination="models/embedded.gguf"):
    manifest = json.loads(Path(manifest_path).read_text())
    path = Path(destination)

    def verified(p):
        if not p.exists() or p.stat().st_size != manifest["size_bytes"]:
            return False
        with p.open("rb") as f:
            return hashlib.file_digest(f, "sha256").hexdigest() == manifest["sha256"]

    if verified(path):
        print(f"Verified {path}: {manifest['sha256']}")
        return
    # Only the pinned project artifact. No remote Python, pickle or model discovery.
    if manifest["repo_id"] != "HuggingFaceTB/SmolLM2-360M-Instruct-GGUF":
        raise ValueError("unreviewed artifact source")
    if len(manifest["revision"]) != 40 or not all(
        x in "0123456789abcdef" for x in manifest["revision"]
    ):
        raise ValueError("immutable revision required")
    name = manifest["filename"]
    if "/" in name or not name.endswith(".gguf"):
        raise ValueError("unexpected artifact filename")
    url = f"https://huggingface.co/{manifest['repo_id']}/resolve/{manifest['revision']}/{name}"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".part")
    try:
        with urllib.request.urlopen(url, timeout=60) as response, temporary.open("wb") as out:
            size = 0
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > manifest["size_bytes"]:
                    raise ValueError("artifact exceeds expected size")
                out.write(chunk)
        if not verified(temporary):
            raise ValueError("artifact checksum mismatch")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Verified {path}: {manifest['sha256']}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", default="models/manifest.json")
    p.add_argument("--destination", default="models/embedded.gguf")
    args = p.parse_args()
    download(args.manifest, args.destination)
