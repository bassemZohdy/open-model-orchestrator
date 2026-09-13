"""Real local development evaluation. No external requests; no protected-test use."""

import argparse
import asyncio
import json
import os
import platform
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path

import psutil
from dataset import validate

from omo.config import Settings
from omo.contracts import ChatRequest
from omo.inference import LlamaModel
from omo.provider import OpenAIProvider
from omo.registry import Registry, RegistryStore
from omo.sandbox import MontySandbox
from omo.service import Orchestrator


def percentile(values, p):
    return sorted(values)[max(0, round((len(values) - 1) * p))]


async def run(output):
    records, digest = validate("evaluation/seed.jsonl")
    settings = Settings(sandbox_enabled=True)
    model = LlamaModel(settings)
    t = time.perf_counter()
    await model.start()
    startup = time.perf_counter() - t
    provider = OpenAIProvider()
    results = []
    memory = []
    try:
        async with MontySandbox(True) as sandbox:
            service = Orchestrator(
                settings, model, RegistryStore(Registry(version="evaluation-1")), sandbox, provider
            )
            for record in records:
                if record.split not in {"development", "validation"}:
                    continue
                repeats = 10 if record.split == "development" else 1
                for repeat in range(repeats):
                    request = ChatRequest.model_validate(
                        {
                            "messages": [m.model_dump() for m in record.messages],
                            "omo": {
                                "local_only": True,
                                "required_capability": record.required_capability,
                            },
                        }
                    )
                    result = await service.chat(request)
                    text = result["choices"][0]["message"]["content"]
                    ok = result["omo"]["action"] == record.expected_action and all(
                        w in text.lower() for w in record.reference_terms
                    )
                    results.append(
                        {
                            "prompt_id": record.id,
                            "split": record.split,
                            "repeat": repeat,
                            "passed": ok,
                            "response": text,
                            "metadata": result["omo"],
                            "usage": result["usage"],
                        }
                    )
                    parent = psutil.Process(int(os.readlink("/proc/self")))
                    memory.append(
                        sum(p.memory_info().rss for p in [parent, *parent.children(recursive=True)])
                    )
    finally:
        await provider.close()
        await model.close()
    latency = [x["metadata"]["total_ms"] for x in results if x["split"] == "development"]
    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "hardware": {
            "architecture": platform.machine(),
            "cpu": platform.processor(),
            "cores_visible": os.cpu_count(),
            "threads": 4,
            "context_tokens": 2048,
            "python": platform.python_version(),
        },
        "dataset_sha256": digest,
        "model": json.loads(Path("models/manifest.json").read_text()),
        "runtime": "llama-cpp-python==0.3.35",
        "sandbox": "pydantic-monty==0.0.23",
        "startup_seconds": startup,
        "peak_sampled_tree_rss_bytes": max(memory),
        "local_latency_ms": {
            "samples": len(latency),
            "p50": statistics.median(latency),
            "p95_empirical": percentile(latency, 0.95),
        },
        "results": results,
        "passed": sum(r["passed"] for r in results),
        "samples": len(results),
        "limits": (
            "4 development prompts repeated 10 times, not 40 independent quality examples; "
            "no reliability/calibration/language claim; keyword checks need human review"
        ),
        "external_calls": 0,
        "protected_test_evaluated": False,
        "baselines": {
            "rules_router": "exact local envelope + helper grammar + eligible configured priority",
            "always_local": (
                "135M/360M four-prompt comparison in docs/evidence; no broad quality claim"
            ),
            "fixed_external": "not measured; no paid inference budget",
        },
    }
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: v
                for k, v in report.items()
                if k
                in [
                    "samples",
                    "passed",
                    "local_latency_ms",
                    "peak_sampled_tree_rss_bytes",
                    "startup_seconds",
                    "external_calls",
                ]
            }
        )
    )
    if report["passed"] != report["samples"]:
        raise SystemExit("development gate failed")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="evaluation/results-local/evaluation.json")
    args = p.parse_args()
    asyncio.run(run(args.output))
