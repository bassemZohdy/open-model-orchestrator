# Evaluation dataset and outcomes

OMO uses only original synthetic JSONL in
[`evaluation/seed.jsonl`](../evaluation/seed.jsonl). Every record is bound to
`omo-original-synthetic` and Apache-2.0 by the strict schema. The current
corpus contains 30 records across development, validation, calibration, train
and protected test splits.

Validation enforces unique IDs, family-level split isolation, duplicate prompt
content rejection and near-duplicate detection across splits. Protected test
records are validated but are not evaluated by the development evaluator.

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
```

Live-provider baselines, third-party benchmark imports, calibration claims and
human-reviewed quality results remain blocked until their licenses, budget and
review process are approved.
