# Evaluation dataset and outcomes

OMO uses only original synthetic JSONL in
[`evaluation/seed.jsonl`](../evaluation/seed.jsonl). Every record is bound to
`omo-original-synthetic` and Apache-2.0 by the strict schema. The expanded
local corpus contains 52 records: 4 development, 12 validation, 10
calibration, 14 train and 12 protected test records. The content revision is
pinned by [`evaluation/dataset_manifest.json`](../evaluation/dataset_manifest.json)
and described in the [dataset card](../evaluation/DATASET_CARD.md).

Validation enforces unique IDs, family-level split isolation, duplicate prompt
content rejection and near-duplicate detection across splits. Protected test
records are validated but are not evaluated by the development evaluator.
Model-routed records also require a typed `expected_proposal` whose action and
capability match the source label. Policy-owned `local_answer` and `reject`
records cannot carry a model proposal.

[`training/dataset.py`](../training/dataset.py) deterministically converts only
train, validation or calibration records into conversational prompt/completion
examples using the exact runtime classification instruction and serializer. It
cannot emit the protected test split. The present corpus yields four usable
training records, so OMO-013 data expansion remains required before training.

Machine-readable provider or human-review results use
[`evaluation/outcomes.example.jsonl`](../evaluation/outcomes.example.jsonl) as
the schema smoke example. Each outcome is bounded by prompt/model/policy
identity, latency, optional observed cost, confidence and timestamp. The
`selective_curve` helper reports risk and coverage at explicit confidence
thresholds; confidence is an evaluation observation and never authorizes a
runtime action.

```bash
uv run --no-sync python evaluation/dataset.py --validate evaluation/seed.jsonl
uv run --no-sync python evaluation/dataset.py --validate-outcomes evaluation/outcomes.example.jsonl
uv run --no-sync python training/dataset.py --split train
```

Live-provider baselines, third-party benchmark imports, calibration claims and
human-reviewed quality results remain blocked until their licenses, budget and
review process are approved.
