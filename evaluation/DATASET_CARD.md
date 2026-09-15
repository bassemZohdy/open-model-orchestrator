# OMO routing synthetic dataset card

## Summary

This repository-local dataset contains 52 original synthetic routing records for the
`omo-routing-proposal-v1` objective. It covers policy-owned decisions
(`local_answer` and `reject`) plus model-proposal decisions
(`external_model`, `helper` and `clarify`). The source is
[`evaluation/seed.jsonl`](seed.jsonl), and its immutable content revision is
recorded in [`dataset_manifest.json`](dataset_manifest.json).

| Split | Records | Use |
|---|---:|---|
| development | 4 | Local development examples |
| validation | 12 | Contract and policy validation |
| calibration | 10 | Offline calibration preparation |
| train | 14 | Candidate SFT preparation |
| test | 12 | Protected evaluation only |

## Provenance and license

All records are authored as original synthetic OMO examples. The dataset is
licensed under Apache-2.0 and uses no third-party prompts or provider output.
The current labels are bootstrap labels pending human review; they must not be
represented as human-reviewed evidence.

## Safety and isolation

Family-level split isolation, duplicate content checks and cross-split
near-duplicate checks run through `evaluation/dataset.py`. The training builder
can emit only train, validation or calibration records and never emits the
protected `test` split. Policy-owned records do not carry a model proposal.

## Limitations and release status

This corpus is for offline contract and training-preparation work. It is not a
trained-model result, a live-provider baseline or a promotion approval. HF Hub
publication, paid evaluation, human review and any production use remain
explicitly blocked until owner-controlled gates are satisfied.

Validate the dataset and revision manifest with:

```bash
uv run --no-sync python evaluation/dataset.py --validate evaluation/seed.jsonl
uv run --no-sync python scripts/check_evaluation_contract.py
```
