"""Bind candidate image identity to reproducible code/model/data configuration."""

import argparse
import hashlib
import json
import re
from pathlib import Path


def build(commit, image, digest, architecture, version, root=Path(".")):
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("immutable code commit required")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise ValueError("immutable OCI digest required")
    if architecture not in {"amd64", "arm64"}:
        raise ValueError("unsupported native architecture")
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-rc\.\d+)?", version):
        raise ValueError("invalid approved release version")

    def sha(path):
        return hashlib.sha256((root / path).read_bytes()).hexdigest()

    return {
        "schema_version": "1",
        "application_version": "0.1.0.dev0",
        "requested_release_version": version,
        "code_commit": commit,
        "image": image,
        "image_digest": digest,
        "platform": "linux/" + architecture,
        "embedded_model": json.loads((root / "models/manifest.json").read_text()),
        "tokenizer": "embedded GGUF tokenizer",
        "template": "chatml-explicit-v1",
        "inference_runtime": "llama-cpp-python==0.3.35",
        "sandbox_runtime": "pydantic-monty==0.0.23",
        "dependency_lock_sha256": sha("uv.lock"),
        "dataset_sha256": sha("evaluation/seed.jsonl"),
        "evaluation_program_sha256": sha("evaluation/run.py"),
        "policy_version": "omo-policy-1",
        "policy_sha256": sha("src/omo/policy.py"),
        "calibration": "uncalibrated",
        "compatibility": {"python": "3.12", "cpu_only": True, "context_tokens": 2048},
        "publication_state": "candidate; stable aliases unchanged",
        "hf_publication": None,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for name in ["commit", "image", "digest", "architecture", "version", "output"]:
        p.add_argument("--" + name, required=True)
    a = p.parse_args()
    Path(a.output).write_text(
        json.dumps(build(a.commit, a.image, a.digest, a.architecture, a.version), indent=2) + "\n"
    )
