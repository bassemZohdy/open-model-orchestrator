# Routing classification contract

OMO trains the selected tiny generative base as a causal-language-model
classifier for one bounded purpose: produce a structured routing proposal. The
model remains advisory. Deterministic code owns authorization, local-answer
eligibility, rejection, provider eligibility, cost, retention and target
selection.

## Objective v1

`omo-routing-proposal-v1` uses the exact runtime instruction, input
serialization and JSON schema exported by `src/omo/classification.py`.

| Model output | Allowed values |
|---|---|
| `action` | `external_model`, `helper`, `clarify` |
| `capability` | `text`, `coding`, `current_information` |
| `helper` | One validated `decimal` or `even_squares` call |

The model cannot output a provider URL, provider identity, credential, process
path, execution limit or confidence-based authorization. `local_answer` and
`reject` are policy-owned actions and are excluded from classification
training. Local-answer generation remains a separate evaluated behavior; every
fine-tuned revision must re-pass it before promotion.

## Dataset boundary

Each model-routed source record carries an `expected_proposal` that must match
its expected action and required capability. Policy-owned records must not
carry a proposal. The deterministic builder emits TRL-compatible conversational
prompt/completion JSONL and uses the same prompt serializer as production.

```bash
uv run --no-sync python training/dataset.py \
  --split train --output artifacts/training/train.jsonl
uv run --no-sync python training/sft.py --dry-run
```

The builder accepts only `train`, `validation` and `calibration`; it cannot
emit the protected `test` split. The current seed produces four training
records. This proves the contract and pipeline only—it is not adequate corpus
size or diversity for a training claim.

## Promotion boundary

Training, Hugging Face publication and model promotion remain disabled. A
future candidate must bind the objective ID, exact code commit, base revision,
dataset revision and hashes, training configuration, evaluation evidence and
export/quantization lineage. A candidate revision inherits no local-answer or
routing eligibility from the upstream checkpoint.
