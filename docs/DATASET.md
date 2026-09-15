# Evaluation dataset and outcomes

OMO uses only original synthetic JSONL in
[evaluation/seed.jsonl](../evaluation/seed.jsonl). Every record is bound to
omo-original-synthetic and Apache-2.0 by the strict schema. The current corpus
contains 30 records across development, validation, calibration, train and
protected test splits.

Validation enforces unique IDs, family-level split isolation, duplicate prompt
content rejection and near-duplicate detection across splits. Protected test
records are validated but are not evaluated by the development evaluator.

## Classification training build

The classification objective and model/policy boundary are frozen in
[docs/CLASSIFICATION.md](CLASSIFICATION.md). Build the reproducible training
view locally with:

```bash
uv run --no-sync python scripts/check_dataset_pipeline.py
```

The underlying builder in
[evaluation/build_dataset.py](../evaluation/build_dataset.py) validates the
source corpus, emits canonical JSONL sorted by record ID, and writes a
deterministic dataset card with input/output SHA-256 values. It copies only the
train split and only records labeled external_model, helper or clarify. The
development, validation, calibration and protected test labels remain outside
the training output. The check uses temporary output paths; it does not mutate
the repository.

Machine-readable provider or human-review results use
[evaluation/outcomes.example.jsonl](../evaluation/outcomes.example.jsonl) as the
schema smoke example. Each outcome is bounded by prompt/model/policy identity,
latency, optional observed cost, confidence and timestamp. The
selective_curve helper reports risk and coverage at explicit confidence
thresholds; confidence is an evaluation observation and never authorizes a
runtime action.

```bash
uv run --no-sync python evaluation/dataset.py --validate evaluation/seed.jsonl
uv run --no-sync python evaluation/dataset.py --validate-outcomes evaluation/outcomes.example.jsonl
```

Live-provider baselines, third-party benchmark imports, calibration claims,
human-reviewed quality results, dataset Hub creation and immutable Hub
revisions remain blocked until their licenses, budget, authority and review
process are approved.
