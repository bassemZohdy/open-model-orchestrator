# Validation evidence

Date: 2026-09-13. This file distinguishes local observations from remote/container publication.

## Implemented and exercised locally

- Real CPU model responses, exact decimal values/units, real Monty transformation, structured embedded analysis, policy-controlled fake-provider execution and buffered SSE API.
- Monty denied file/proc/environment/network/DNS/subprocess/FFI/package and native-eval attempts. Actual memory/time/output/recursion limits, worker kill, cancellation, fresh state and no secret/FD inheritance were exercised.
- Model cancellation kills its worker; restart reloads it. Unknown model bytes fail before loading. Context overflows fail explicitly.
- API bearer/loopback access, body/content bounds, role/modality rejection, rate controls and safe validation errors are tested.

Local environment: Linux x86_64, no emulation; Python 3.12.14, eight CPU quota equivalents, approximately 20 GiB memory limit. Inference uses four threads and 2048 context tokens. Model artifact: 386,404,992 bytes. `docs/evidence/evaluation.json` records 46 checks: 40 runs over four local prompts plus six scope challenges; no external calls. Observed startup including hash/load/warmup: about 0.53 s. Local answer p50 about 260 ms and empirical p95 about 479 ms. Peak sampled application/model process-tree RSS about 609 MB. These are workspace observations, not portable capacity guarantees or container measurements.

The earlier 135M vs 360M comparison is preserved in `docs/evidence/model-comparison.json`. Its keyword-only pass flags did not catch the 135M quality defects; ADR 001 records the manual review and selection. No held-out calibration or language-generation reliability is claimed.

## Test results and remote verification

Local full suite: **103 passed in 15.34 seconds** (91 contract/security tests and 12 real-model tests). Ruff lint/format, strict mypy over 14 source files, lock validation, dataset validation and disabled-release/schedule contracts passed. The expanded runtime smoke also passed locally with authentication, oversized-body rejection, sandbox denial/limits and graceful shutdown.

GitHub source is on `feat/bootstrap-v0.1`, [draft PR #1](https://github.com/bassemZohdy/open-model-orchestrator/pull/1). At commit `a2baf9781a296330531dadf4927efa7905a5cb45`, [real-model run 34754277560](https://github.com/bassemZohdy/open-model-orchestrator/actions/runs/34754277560) passed: 12 real-model tests and 46 evaluation checks; CI local-answer p50/p95 250.588/435.234 ms, startup 0.646 s, peak sampled tree RSS 616,124,416 bytes. Its evidence artifact is `10317140322`, archive SHA-256 `3c9930d84e8467e2580fb42dbf9c447da990b42a3dfa78d34f23889207ca3413`. PR checks and native ARM64 container acceptance passed; AMD64 was still running at this checkpoint. Final head/platform results are recorded after completion.

Earlier failures are retained in Actions history: the initial build used an unsupported uv flag (corrected); a duplicate push run then exposed a test observation race when an already-reaped worker vanished between status reads. The cancellation test now requires complete reaping, and all 27 sandbox tests pass with that stricter assertion. These earlier failures are not reported as successful runs.

Docker Hub preflight authenticated `bzohdy` successfully in [run 34754068464](https://github.com/bassemZohdy/open-model-orchestrator/actions/runs/34754068464). Target image is `bzohdy/open-model-orchestrator`; login does not prove push permission. Preflight artifact `10315684770` has archive SHA-256 `6bfc2ccfbb3413cf9313b9d4dc92a7fa42a7ce948bb08a75af5fbc1edb737b16`. No Docker daemon is available in this local workspace; running the runtime smoke script locally is not container evidence. Docker-save gzip size is not compressed registry transfer bytes.

## Not published / not executed

No stable Docker Hub release, no HF model/dataset publication, no paid training/inference, no scheduled jobs, no automatic promotion. Training execution and stable multi-registry promotion/signing are not implemented. See TODO.md.
