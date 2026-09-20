# Validation and delivery evidence

This document retains historical CI evidence from 2026-09-13/14 and the
repository verification scope. The OMO-008–OMO-011 offline foundations,
OMO-012/013 contract pipeline and OMO-014 preflight are merged; current
remaining work is tracked in [TODO](../TODO.md),
[training](TRAINING.md), [dataset](DATASET.md) and [operations](OPERATIONS.md).
The evidence below is not a claim that paid training, live-provider evaluation
or publication has been performed.

## Current main verification — PR #26, 2026-09-20

PR [#26](https://github.com/bassemZohdy/open-model-orchestrator/pull/26) merged
runtime/release hardening and the Claude review workflow fix into `main` at
`b009102d5c30b938be1cdfd844ecbc5d636467a8`. Its head commit
`d04f62ad9d4dee8bb31b5a78218f2413d3ba682c` passed the
[OMO validation run](https://github.com/bassemZohdy/open-model-orchestrator/actions/runs/35530100803)
and the [Claude review run](https://github.com/bassemZohdy/open-model-orchestrator/actions/runs/35530100841).
The validation passed static checks, secret scanning, real-model validation and
native AMD64/ARM64 container acceptance. Local verification on the merged tree
passed 214 non-model tests, with 12 model tests deselected, plus three review-
workflow tests, Ruff, formatting, mypy, dataset/evaluation/training/access/
publication/model-promotion/release contracts and the OMO-015 artifact-contract
tests. The post-merge `main` validation run
[35530212896](https://github.com/bassemZohdy/open-model-orchestrator/actions/runs/35530212896)
also passed its native AMD64/ARM64, real-model, static and secret checks.

This verifies the repository implementation only. Public Docker publication
still requires the protected release workflow, security/signing approval and
immutable digest evidence. Training, human review and Hugging Face publication
remain separate external gates listed in [TODO](../TODO.md). OMO does not
operate a production host.

## Historical main verification — PR #11, 2026-09-14

PR [#11](https://github.com/bassemZohdy/open-model-orchestrator/pull/11) was
reviewed by Claude with no findings and merged into `main` at
`cc9dbbfde2d4c926842f30e385e9f07444b552ce`. The required
[OMO validation run](https://github.com/bassemZohdy/open-model-orchestrator/actions/runs/34803105374)
passed static checks, secret scanning, real-model validation and native AMD64
and ARM64 container acceptance. The current local non-model suite passed **163
tests**, with **12 model tests deselected**. That historical run validated 30
original synthetic records and the outcome example passed with SHA-256
`ba53c337cee6a7611e17e82c1661e90b99c0181efdfe9dd785c6a863e8a66714`.

The training, access-policy, evaluation, publication and release contracts also
passed at that revision. The current 52-record dataset and merged OMO-012/013
pipeline require fresh CI evidence; training, live-provider baselines, paid
operations, publication and stable promotion remain disabled.

## Implemented and tested

- Real SmolLM2-360M Q8_0 CPU inference through llama-cpp-python 0.3.35, with checksum verification, warmup, context/queue bounds, cancellation and worker restart.
- Exact decimal values/units and real Monty 0.0.23 computation; no native guest eval/exec fallback. File/proc/environment/network/DNS/subprocess/FFI/package access, state reuse, inherited descriptors and resource bounds are covered by actual sandbox tests.
- Strict configuration/API/proposal schemas, authentication, input limits, immutable registries, policy constraints before provider ranking, bounded external calls and validated upstream SSE with buffered downstream delivery. External-provider contracts use fakes; no live-provider quality or paid-inference result is claimed.
- Bundled/slim Docker targets, hardened Compose, native AMD64/ARM64 validation, secret scanning, container reports and strict release vulnerability gates. Training is a dry-run preparation tool only.
- Typed model-proposed helper arguments, predeclared cross-model evaluation gates, disabled HF publication identity checks and evidence-bound multi-platform promotion validation are covered by local contract tests.

The historical local verification passed **163 non-model tests**, with **12
model tests deselected**, plus Ruff lint/format, strict mypy, 30-record dataset
and outcome validation, training/access/evaluation contracts, and release-event
and schedule contracts. Fresh verification for the current cleanup branch is
reported by CI/command output rather than inferred from this historical record.

The trusted real-model run for the implementation commit is [34755031771](https://github.com/bassemZohdy/open-model-orchestrator/actions/runs/34755031771): **12 passed**, plus **46/46 development evaluation checks**, with zero external calls. Its artifact ID is `10315969857`; archive SHA-256 `27d597194fa85524958b16317a104e93dc7b769319d260f61d9a1b6549c3b87f`.

## Measurements and their limits

Local workspace: native Linux x86_64, Python 3.12.14, eight CPU quota equivalents and approximately 20 GiB RAM limit; inference uses four threads, 2048 context tokens and batch 128. Model bytes are **386,404,992**. Inference is greedy, seed 42, explicit ChatML.

| Observation | Local workspace | GitHub AMD64 model job |
|---|---:|---:|
| Startup, including hash/load/warmup | 0.527 s | 0.631 s |
| Warm local-answer p50 | 259.709 ms | 236.088 ms |
| Warm local-answer empirical p95 | 479.125 ms | 380.684 ms |
| Peak sampled application/model process-tree RSS | 608,571,392 bytes | 615,960,576 bytes |
| Development checks | 46/46 | 46/46 |

There are only **four independent local questions**, repeated ten times for latency, plus six scope challenges. These are development prompts, not a protected test set or proof of production reliability. Arabic/mixed-language rejection is not Arabic generation support. No calibrated confidence, p99 claim, GPU result or emulated/native equivalence is reported. The earlier 135M candidate's keyword checks missed quality defects; manual review rejected it. See [ADR 001](adr/001-baseline.md), [evaluation guide](EVALUATION.md), and the raw summaries in `docs/evidence/`.

## Native containers

The [native validation run 34755033927](https://github.com/bassemZohdy/open-model-orchestrator/actions/runs/34755033927) passed all four jobs: checks, secret scan, AMD64 container and ARM64 container. Full image IDs, artifact archive digests and scan summaries are in [machine-readable evidence](evidence/ci-verification.json).

| Native platform | Unpacked image bytes | Docker-save gzip bytes | Evidence artifact ID |
|---|---:|---:|---:|
| Linux AMD64 | 673,944,805 | 473,427,708 | 10317000839 |
| Linux ARM64 | 687,408,938 | 469,184,947 | 10316799643 |

Image IDs are local Docker image/config identifiers, **not published registry manifest digests**. Docker-save gzip size is an archive measurement, **not compressed registry transfer bytes**. Actual model answers and helper values were produced with `--network none`, read-only root, no capabilities, non-root UID, 1536 MiB memory and bounded CPU/PIDs. No local Docker daemon was available; this container evidence comes from GitHub-hosted native runners, without emulation. Other CPU feature combinations and host operating systems were not validated.

## Security and publication

Development tests may pass while security reports contain release-blocking findings. Rescanning both patched images confirmed no PCRE2 findings. Each platform still reports 60 package/advisory entries: 55 HIGH and five CRITICAL, spanning 21 distinct advisory IDs. These are scanner findings, not 60 demonstrated exploits. They and DiskCache 5.6.3 / CVE-2025-69872 block strict release gates. No finding was added to an ignore list. Reachability/review is still required; neither a clean audit nor VM-grade isolation is claimed.

| Destination | Verified state |
|---|---|
| GitHub `bassemZohdy/open-model-orchestrator` | Current `main` is `b009102` after PR #26; repository validation is green, with no model publication or stable application release |
| Docker Hub `bzohdy/open-model-orchestrator` | Actions credentials configured and login verified in run `34754068464`; a successful project-image push and immutable digest still need to be recorded; no candidate/stable image published by this work |
| HF `BassemZohdy/open-model-orchestrator` | Repository created by the owner; no approved OMO fine-tuned artifact is published |
| HF `BassemZohdy/open-model-orchestrator-dataset` | Intended dataset target; immutable publication and publishing authority remain unverified |
| Paid training/inference, schedules, automatic promotion | Not executed; disabled |

The bundled artifact remains upstream `HuggingFaceTB/SmolLM2-360M-Instruct-GGUF`, revision `593b5a2e04c8f3e4ee880263f93e0bd2901ad47f`, SHA-256 `48ab3034d0dd401fbc721eb1df3217902fee7dab9078992d66431f09b7750201`. It is not an OMO fine-tune. Current dataset SHA-256: `896d92c892c6cc951e73bbb184b1a59f0fa50f4831cc3c831360b5107d39e5f7`. Current outcome-example SHA-256: `ba53c337cee6a7611e17e82c1661e90b99c0181efdfe9dd785c6a863e8a66714`.

Earlier failed runs remain visible: the first build used an unsupported uv flag
(fixed), one duplicate push run hit the cancellation-test observation race
(fixed), and PR #11 initially exposed two synchronization defects that were
corrected before its final green run. No earlier failure is presented as a
success. Reproducible commands are in [README](../README.md), owner setup in
[RELEASE](RELEASE.md), and only remaining work in [TODO](../TODO.md).
