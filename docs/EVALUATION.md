# Evaluation and offline learning

`evaluation/seed.jsonl` contains 52 original synthetic records with family,
split, language, message roles, task capability, expected action, reference
terms and label provenance. Import accepts bounded UTF-8 JSONL only, checks
uniqueness, family split isolation and near-duplicate text across splits, and
never executes data-provided code.

Splits are 4 development, 12 validation, 10 calibration, 14 train and 12
protected-test examples. Development local prompts were used during selection
and are never described as held-out evidence. The protected test split is
checked for schema and split integrity but is not executed by the bootstrap
evaluator. Arabic and mixed-language refusal is not evidence of Arabic answer
capability.

`python evaluation/run.py` performs ten repeats of each of the four local
questions and one execution of each scope challenge. The required gate is no
incorrect policy path, all local reference checks pass, no truncated local
answer and no external calls. Keyword checks are weak and require human review;
40 repeated runs provide latency samples but only four independent quality
examples. No calibrated probability, production error rate or broad language
claim follows from this sample.

Always-local baseline: two SmolLM2 Q8 candidates were actually run on the same
four prompts; manual review overruled the 135M keyword-pass result. Fixed
external and broad rules-versus-learned utility comparisons were not run without
an approved external inference budget. No self-rating or LLM judge is used.

RouteLLM and RouterBench provide prior art and possible data sources, not
today's provider ranking. Their artifacts require independent license/schema
review before any import; no third-party benchmark bytes or labels are included
in this repository.

`training/sft.py --dry-run` validates the data and describes a bounded
experiment. It does not implement SFT execution, export or quantization. These
remain OMO-008. Full fine-tuning is the first proposed small-model baseline;
adapters must earn their complexity in measurements. There are no remote-job
calls, schedules, automatic fine-tunes or model promotions in runtime.

## Held-out routing contract

`evaluation/heldout.jsonl` contains four small, repository-owned scenarios for
helper selection, exact helper argument fidelity, result interpretation and
policy-owned routing contention. The evaluator compares an observed decision
record with the expected action and category-specific gate. It reports
per-category accuracy, fails on missing or unknown observations, and records
that no protected test split, provider call or confidence-based authorization
was used.

```bash
uv run --no-sync python evaluation/heldout.py --validate-cases
```

These four scenarios are harness coverage, not evidence for corpus quality,
calibration or production routing. A future model-backed run must supply
observations from an approved immutable revision and separately reviewed
corpus.

## Offline plans and review evidence

The OMO-003 [benchmark preflight](BENCHMARKS.md) requires exact immutable
application, dataset and candidate revisions. It separates llama.cpp Q4/Q8
comparisons from a Transformers fp16 CPU reference and emits a dry-run plan
only; no weights are downloaded, no provider is called and no model is
promoted.

The offline evaluation audit and [human-review protocol](EVALUATION_REVIEW.md)
bind source/license provenance, fixed-provider lineage, selective risk/coverage
calibration and reviewer decisions into one validated bundle. This remains
evidence preparation: no live-provider call, protected-test run or promotion
is performed.
