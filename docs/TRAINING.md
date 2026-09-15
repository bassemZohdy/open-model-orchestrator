# Offline training preparation

OMO-008 is implemented as a disabled, reproducible preparation contract. It
does not install or invoke Transformers/PyTorch, create a remote job, download
weights, export adapters or publish an artifact.

## Contract

[`config/training.yaml`](../config/training.yaml) pins the base-model identity,
the `omo-routing-proposal-v1` objective, the original Apache-2.0 dataset,
bounded proposal limits, supported export formats and quantization targets. It
requires a lineage record and a rollback manifest for any future artifact.
`enabled: false`, `execution: dry-run-only` and `max_cost_usd: 0` are mandatory
until the owner approves execution.

The runtime and training pipeline import their instruction, serializer, label
sets and JSON schema from one contract in `src/omo/classification.py`.
`training/dataset.py` creates deterministic TRL-compatible prompt/completion
records and refuses to emit the protected test split. See
[classification](CLASSIFICATION.md) for the policy boundary.

Run the safe planner with:

```bash
uv run --no-sync python training/sft.py --dry-run
uv run --no-sync python training/dataset.py --split train
uv run --no-sync python scripts/check_training_contract.py
```

The output includes hashes for the configuration and dataset, the exact base
model revision, proposed limits and required export evidence. It is a plan,
not a trained-model result.

## Manual OMO-014 preflight

The manual-only [training workflow](../.github/workflows/training.yml) is a protected preflight, not an execution switch. Dispatch it from main with exact 40-character code, dataset and base-model revisions plus the method, hardware, timeout, maximum cost, backend and optional resume-run identifier. It checks out the exact code, runs `uv sync --locked`, validates the offline lineage plan and then stops. Concurrency cancels an older preflight for the same code revision.

The workflow accepts only `dry_run: true`; it does not create an HF Job, upload checkpoints, publish a model or promote an alias. A future HF Job dispatch still requires the protected `training` environment, owner-approved spend/credits, scoped credentials and the larger reviewed OMO-013 corpus. The expanded local source currently produces 14 trainable
classification records. They remain bootstrap-labeled and pending human review.
Enabling execution still requires a materially larger reviewed corpus, a
separately reviewed isolated environment, locked Transformers/PyTorch/TRL
dependencies, Trackio monitoring, a full-versus-adapter comparison, protected
held-out evaluation, artifact signing and an owner-approved budget.
