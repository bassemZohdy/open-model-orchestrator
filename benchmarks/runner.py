"""Validate reproducible model-comparison plans without executing them.

Benchmark execution stays disabled until the owner supplies exact revisions,
license decisions, hardware and budget approval. This module only validates and
prints a deterministic plan.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from omo.contracts import StrictModel

SHA_PATTERN = re.compile(r"^[0-9a-fA-F]{40}$")
ModelRole = Literal[
    "smollm2-360m",
    "granite",
    "lfm",
    "qwen",
    "transformers-cpu-reference",
]
Runtime = Literal["llama-cpp", "transformers"]
Quantization = Literal["fp16", "q4_0", "q8_0"]


class BenchmarkCandidate(StrictModel):
    role: ModelRole
    model_id: str = Field(min_length=3, max_length=200)
    revision: str = Field(pattern=SHA_PATTERN.pattern)
    runtime: Runtime
    quantizations: tuple[Quantization, ...] = Field(min_length=1)
    license_decision: Literal["approved", "pending"] = "pending"

    @model_validator(mode="after")
    def reference_constraints(self) -> BenchmarkCandidate:
        if self.role == "transformers-cpu-reference" and (
            self.runtime != "transformers" or self.quantizations != ("fp16",)
        ):
            raise ValueError("Transformers CPU reference must use fp16")
        if self.role != "transformers-cpu-reference" and self.runtime != "llama-cpp":
            raise ValueError("comparison candidates must use llama-cpp")
        if self.license_decision == "approved" and not self.model_id:
            raise ValueError("approved candidate requires a model id")
        return self


class BenchmarkManifest(StrictModel):
    schema_version: Literal["1"] = "1"
    code_sha: str = Field(pattern=SHA_PATTERN.pattern)
    dataset_revision: str = Field(pattern=SHA_PATTERN.pattern)
    benchmark_objective: Literal["omo-routing-proposal-v1"] = "omo-routing-proposal-v1"
    candidates: tuple[BenchmarkCandidate, ...] = Field(min_length=5)
    execution: Literal["dry-run-only"] = "dry-run-only"

    @model_validator(mode="after")
    def required_roles(self) -> BenchmarkManifest:
        roles = {candidate.role for candidate in self.candidates}
        required = {
            "smollm2-360m",
            "granite",
            "lfm",
            "qwen",
            "transformers-cpu-reference",
        }
        if roles != required:
            raise ValueError("manifest must contain exactly the five comparison roles")
        return self


def load_manifest(path: str) -> tuple[BenchmarkManifest, str]:
    raw = Path(path).read_bytes()
    if len(raw) > 100_000:
        raise ValueError("benchmark manifest exceeds 100 KB budget")
    manifest = BenchmarkManifest.model_validate_json(raw)
    return manifest, hashlib.sha256(raw).hexdigest()


def dry_run_plan(manifest: BenchmarkManifest, manifest_sha256: str) -> dict[str, object]:
    return {
        "schema_version": "1",
        "manifest_sha256": manifest_sha256,
        "code_sha": manifest.code_sha.lower(),
        "dataset_revision": manifest.dataset_revision.lower(),
        "benchmark_objective": manifest.benchmark_objective,
        "candidates": [
            {
                "role": candidate.role,
                "model_id": candidate.model_id,
                "revision": candidate.revision.lower(),
                "runtime": candidate.runtime,
                "quantizations": list(candidate.quantizations),
                "license_decision": candidate.license_decision,
            }
            for candidate in manifest.candidates
        ],
        "reference_comparison_required": True,
        "execution": "disabled",
        "paid_provider_calls": False,
        "remote_execution": False,
        "model_promotion": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--validate", action="store_true")
    group.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    manifest, digest = load_manifest(args.manifest)
    plan = dry_run_plan(manifest, digest)
    if args.validate:
        print(json.dumps({"candidates": len(manifest.candidates), "manifest_sha256": digest}))
        return 0
    print(json.dumps(plan, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
