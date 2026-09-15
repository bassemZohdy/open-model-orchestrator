"""Validate manual OMO-014 training inputs without starting a remote job."""

from __future__ import annotations

import argparse
import json
import re
from decimal import Decimal, InvalidOperation
from typing import Final

SHA_PATTERN: Final = re.compile(r"^[0-9a-fA-F]{40}$")
IDENTIFIER_PATTERN: Final = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
METHODS: Final = frozenset({"full-sft", "lora"})
HARDWARE: Final = frozenset({"cpu-small", "a10g-small"})
BACKENDS: Final = frozenset({"huggingface-job"})
MAX_TIMEOUT_MINUTES: Final = 1440
MAX_COST_USD: Final = Decimal("1000")


def _revision(value: str, field: str) -> str:
    if not SHA_PATTERN.fullmatch(value):
        raise ValueError(f"{field} must be a 40-character immutable commit revision")
    return value.lower()


def _bounded_decimal(value: str, field: str) -> str:
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{field} must be a decimal amount") from exc
    if not amount.is_finite() or amount < 0 or amount > MAX_COST_USD:
        raise ValueError(f"{field} must be between 0 and 1000")
    return format(amount, "f")


def _bounded_integer(value: str, field: str) -> int:
    try:
        amount = int(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be an integer") from exc
    if not 1 <= amount <= MAX_TIMEOUT_MINUTES:
        raise ValueError(f"{field} must be between 1 and {MAX_TIMEOUT_MINUTES}")
    return amount


def validate(
    *,
    code_sha: str,
    dataset_revision: str,
    base_model_revision: str,
    method: str,
    hardware: str,
    execution_backend: str,
    timeout_minutes: str,
    max_cost_usd: str,
    resume_run_id: str,
    dry_run: str,
) -> dict[str, object]:
    """Validate the complete owner-supplied plan and fail closed on execution."""
    if method not in METHODS:
        raise ValueError(f"method must be one of {sorted(METHODS)}")
    if hardware not in HARDWARE:
        raise ValueError(f"hardware must be one of {sorted(HARDWARE)}")
    if execution_backend not in BACKENDS:
        raise ValueError(f"execution_backend must be one of {sorted(BACKENDS)}")
    if resume_run_id != "none" and not IDENTIFIER_PATTERN.fullmatch(resume_run_id):
        raise ValueError("resume_run_id must be none or a bounded run identifier")
    if dry_run not in {"true", "false"}:
        raise ValueError("dry_run must be true or false")
    if dry_run != "true":
        raise ValueError(
            "remote training is disabled; use the dry-run preflight until owner gates pass"
        )

    plan = {
        "code_sha": _revision(code_sha, "code_sha"),
        "dataset_revision": _revision(dataset_revision, "dataset_revision"),
        "base_model_revision": _revision(base_model_revision, "base_model_revision"),
        "method": method,
        "hardware": hardware,
        "execution_backend": execution_backend,
        "timeout_minutes": _bounded_integer(timeout_minutes, "timeout_minutes"),
        "max_cost_usd": _bounded_decimal(max_cost_usd, "max_cost_usd"),
        "resume_run_id": resume_run_id,
        "dry_run": True,
        "automatic_promotion": False,
    }
    return plan


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a manual OMO training plan")
    parser.add_argument("--code-sha", required=True)
    parser.add_argument("--dataset-revision", required=True)
    parser.add_argument("--base-model-revision", required=True)
    parser.add_argument("--method", required=True)
    parser.add_argument("--hardware", required=True)
    parser.add_argument("--execution-backend", required=True)
    parser.add_argument("--timeout-minutes", required=True)
    parser.add_argument("--max-cost-usd", required=True)
    parser.add_argument("--resume-run-id", required=True)
    parser.add_argument("--dry-run", required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            validate(
                code_sha=args.code_sha,
                dataset_revision=args.dataset_revision,
                base_model_revision=args.base_model_revision,
                method=args.method,
                hardware=args.hardware,
                execution_backend=args.execution_backend,
                timeout_minutes=args.timeout_minutes,
                max_cost_usd=args.max_cost_usd,
                resume_run_id=args.resume_run_id,
                dry_run=args.dry_run,
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
