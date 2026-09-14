# Changelog

## Unreleased

- Added offline OMO-008 training preparation with locked model/dataset lineage,
  export/quantization targets and rollback requirements; training execution,
  export and promotion remain disabled.
- Expanded the original synthetic evaluation corpus to 30 records, added
  family/content deduplication, bounded outcome validation and selective
  risk/coverage observations without importing third-party benchmark data.
- Added opt-in hash-based caller policies with tenant/role identity, exact
  egress host allowlists, retention filtering and bounded in-memory daily budget
  reservations; raw bearer keys and prompt content are never stored.
- Added offline registry freshness/status administration, authenticated
  last-known-good reload and a declared tokenizer strategy for external count
  estimates. Request-time discovery and downloads remain disabled.
- Verified the issue-first Codex/Claude workflow on reviewed PR #10; Claude
  reported no findings and the PR passed all required CI jobs before merge.
- Hardened change-aware model/container selection: PRs compare the base SHA with the actual head SHA, all branch names are supported, renames/deletions are inspected, and unknown or unavailable change sets run both expensive suites.
- Manual dispatch and reusable release validation force the complete model/container suites; lightweight checks, secret scanning and release-contract checks remain unconditional.
- Added bounded upstream OpenAI-compatible SSE parsing with terminal-event validation, usage preservation, pre-data rate-limit retry only, and no replay after partial output.
- Added typed model-proposed helper arguments with the same strict schemas as explicit helper requests; untyped or incomplete proposals fail closed.
- Added predeclared cross-model evaluation gates, a disabled HF publication identity contract, security-report validation, and evidence-bound multi-platform promotion validation. External account, signing and security findings remain release blockers.

## Unreleased — reviewer workflow hardening

- Consolidated Claude into one review-only PR workflow; removed the comment-driven assistant (manual retry remains available through Actions).
- Added draft/fork/actor guards, a specific Codex bot allowance without bypassing write-access checks, immutable action refs, credential-free checkout, timeout/turn bounds and per-PR cancellation.
- Added three workflow regression tests. Local verification: 94 non-model tests passed (12 model tests deselected), ruff check/format, mypy and the unchanged release contract passed. Remote review and CI are recorded on PR #3, not inferred from local checks.

## 0.1.0 development baseline — 2026-09-13

- Embedded SmolLM2-360M Q8_0 through pinned llama-cpp-python, checksum validation, warmup and supervised cancellation.
- Exact decimal helper and a bounded even-squares transformation through real Monty workers.
- Strict API/configuration/proposal schemas, protected endpoints, immutable registry snapshots and hard-constraint external selection.
- One pooled OpenAI-compatible/OpenRouter adapter with bounded responses, limited 429 retries and safe failures.
- Validated upstream SSE collection with buffered downstream delivery; no provider output rewriting or native guest-code fallback.
- Real model, sandbox, policy, provider and API tests; original split-aware seed data and offline development evaluator.
- Bundled/slim Docker targets, hardened Compose and native architecture CI contracts.
- Manual gated candidate-release workflow; training, schedules and model promotion remain disabled.
- Corrected locked native build constraints, added secret/container vulnerability scans and a strict release audit gate; the DiskCache advisory remains a publication blocker.
- Expanded container acceptance for authentication, resource bounds and real sandbox isolation; release manifests bind code/model/data/policy identities.
- Fixed a cancellation-test observation race and now require complete worker reaping rather than accepting zombie state.

- Native AMD64 and ARM64 bundled images passed offline model/helper/sandbox/authentication/limits/shutdown acceptance at implementation commit 23a0b2881ec69f42d864d15440f8f06ef3969239. The pinned PCRE2 update removed two findings; remaining strict-audit blockers are retained in TODO.md.

Publication and platform evidence are recorded separately in docs/VALIDATION.md. This is not a production release or an OMO fine-tuned model.
