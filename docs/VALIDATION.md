# Validation evidence

Date: 2026-09-13. This file distinguishes local observations from remote/container publication.

## Implemented and exercised locally

- Real CPU model responses, exact decimal values/units, real Monty transformation, structured embedded analysis, policy-controlled fake-provider execution and buffered SSE API.
- Monty denied file/proc/environment/network/DNS/subprocess/FFI/package and native-eval attempts. Actual memory/time/output/recursion limits, worker kill, cancellation, fresh state and no secret/FD inheritance were exercised.
- Model cancellation kills its worker; restart reloads it. Unknown model bytes fail before loading. Context overflows fail explicitly.
- API bearer/loopback access, body/content bounds, role/modality rejection, rate controls and safe validation errors are tested.

Local environment: Linux x86_64, no emulation; Python 3.12.14, eight CPU quota equivalents, approximately 20 GiB memory limit. Inference uses four threads and 2048 context tokens. Model artifact: 386,404,992 bytes. `docs/evidence/evaluation.json` records 46 checks: 40 runs over four local prompts plus six scope challenges; no external calls. Observed startup including hash/load/warmup: about 0.53 s. Local answer p50 about 260 ms and empirical p95 about 479 ms. Peak sampled application/model process-tree RSS about 609 MB. These are workspace observations, not portable capacity guarantees or container measurements.

The earlier 135M vs 360M comparison is preserved in `docs/evidence/model-comparison.json`. Its keyword-only pass flags did not catch the 135M quality defects; ADR 001 records the manual review and selection. No held-out calibration or language-generation reliability is claimed.

## Pending remote verification

Exact final test counts, head commit, PR URL, Actions results, native container evidence and Docker Hub account preflight results will be filled after the corresponding operations complete. No Docker daemon is available in this local workspace; running the runtime smoke script locally is not container evidence. Docker-save gzip size is not compressed registry transfer bytes.

## Not published / not executed

No stable Docker Hub release, no HF model/dataset publication, no paid training/inference, no scheduled jobs, no automatic promotion. Training execution and stable multi-registry promotion/signing are not implemented. See TODO.md.
