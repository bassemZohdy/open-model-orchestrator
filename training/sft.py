"""Budget-free local preparation. Actual tuning remains explicitly unavailable."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evaluation"))
from dataset import validate


def main():
    p = argparse.ArgumentParser(
        description="Prepare an offline SFT experiment; never creates a remote job"
    )
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--dataset", default="evaluation/seed.jsonl")
    args = p.parse_args()
    rows, digest = validate(args.dataset)
    train = [r for r in rows if r.split == "train"]
    if not args.dry_run:
        raise SystemExit(
            "Training is disabled: select and validate the isolated training stack, "
            "export path and owner-approved budget first. See TODO OMO-008."
        )
    print(
        json.dumps(
            {
                "status": "dry-run-only",
                "training_enabled": False,
                "remote_jobs_enabled": False,
                "automatic_promotion": False,
                "dataset_sha256": digest,
                "train_examples": len(train),
                "proposed_base_model": "HuggingFaceTB/SmolLM2-360M-Instruct",
                "proposal": {
                    "method": "full supervised fine-tuning baseline before comparing adapters",
                    "max_steps": 20,
                    "max_sequence_tokens": 512,
                    "max_runtime_minutes": 15,
                    "max_cost_usd": 0,
                },
                "not_implemented": [
                    "training execution",
                    "export",
                    "quantization regression",
                    "promotion",
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
