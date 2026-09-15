# Evaluation and offline learning

`evaluation/seed.jsonl` contains 22 original synthetic records with family, split, language, message roles, task capability, expected action, reference terms and label provenance. Intent and outcome schemas are separately defined in evaluation/dataset.py. Import accepts bounded UTF-8 JSONL only, checks uniqueness, family split isolation and near-duplicate text across splits. It does not execute data-provided code. This small matcher is not a scalable near-deduplication pipeline.

Splits: four train, four development, six validation challenges, four calibration and four protected-test examples. Development local prompts were used during selection and are never described as held-out evidence. The final test split is checked for schema/split integrity but not executed during bootstrap. The six validation challenges run local-only and require rejection. Arabic and mixed-language refusal is not evidence of Arabic answer capability.

`python evaluation/run.py` performs ten repeats of each of the four local questions and one execution of each scope challenge. Required gate: no incorrect policy path, all local reference checks pass, no truncated local answer, no external calls. Reference keyword checks are weak and require human review; 40 repeated runs provide latency samples but only four independent quality examples. No calibrated probability, production error rate or broad language claim follows from this sample. p95 is empirical; p99 is not reported. Reference hardware, model/runtime revision, context, thread count, dataset hash, startup and sampled process-tree RSS are recorded.

Always-local baseline: two SmolLM2 Q8 candidates were actually run on the same four prompts; manual review overruled the 135M keyword-pass result. Fixed external and broad rules-versus-learned utility comparisons were not run without an approved external inference budget. No self-rating or LLM judge is used.

RouteLLM and RouterBench provide prior art and possible data sources, not today's provider ranking. RouterBench HF card lacks a clear license declaration in the inspected artifact. Do not import its historical outcomes as modern selection labels or assume the source benchmark licenses are interchangeable. Exact artifact/license/schema review is required before import.

`training/sft.py --dry-run` validates the data and describes a bounded experiment. **It does not implement SFT execution, export or quantization.** These remain OMO-008. Full fine-tuning is the first proposed small-model baseline; adapters must earn their complexity in measurements. There are no remote-job calls, schedules, automatic fine-tunes or model promotions anywhere in runtime. Any future paid job requires an approved budget/timeout, isolated training dependencies, export checks and held-out safety/quality gates before deployment.


## Held-out routing contract

`evaluation/heldout.jsonl` contains four small, repository-owned scenarios for helper selection, exact helper argument fidelity, result interpretation and policy-owned routing contention. The evaluator in `evaluation/heldout.py` compares an observed decision record with the expected action and category-specific gate. It reports per-category accuracy, fails on missing or unknown observations, and records that no protected test split, provider call or confidence-based authorization was used.

Validate only the case contract in CI:

```bash
uv run --no-sync python evaluation/heldout.py --validate-cases
```

A future model-backed run must supply observations from an approved immutable revision and separately reviewed corpus. These four scenarios are harness coverage, not evidence for corpus quality, calibration, or production routing.


The OMO-003 [benchmark preflight](BENCHMARKS.md) requires exact immutable application, dataset and candidate revisions. It separates llama.cpp Q4/Q8 comparisons from a Transformers fp16 CPU reference and emits a dry-run plan only; no weights are downloaded, no provider is called and no model is promoted.


The offline evaluation audit and [human-review protocol](EVALUATION_REVIEW.md) now bind source/license provenance, fixed-provider lineage, selective risk/coverage calibration and reviewer decisions into one validated bundle. This remains evidence preparation: no live-provider call, protected-test run or promotion is performed.
