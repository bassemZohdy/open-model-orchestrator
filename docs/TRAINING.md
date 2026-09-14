# Offline training preparation

OMO-008 is implemented as a disabled, reproducible preparation contract. It
does not install or invoke Transformers/PyTorch, create a remote job, download
weights, export adapters or publish an artifact.

## Contract

[`config/training.yaml`](../config/training.yaml) pins the base-model identity,
the original Apache-2.0 dataset, bounded proposal limits, supported export
formats and quantization targets. It requires a lineage record and a rollback
manifest for any future artifact. `enabled: false`, `execution: dry-run-only`
and `max_cost_usd: 0` are mandatory until the owner approves execution.

Run the safe planner with:

```bash
uv run --no-sync python training/sft.py --dry-run
uv run --no-sync python scripts/check_training_contract.py
```

The output includes hashes for the configuration and dataset, the exact base
model revision, proposed limits and required export evidence. It is a plan,
not a trained-model result. Enabling execution requires a separately reviewed
isolated environment, locked Transformers/PyTorch dependencies, a full-versus-
adapter comparison, protected held-out evaluation, artifact signing and an
owner-approved budget.
