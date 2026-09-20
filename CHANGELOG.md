# Changelog

## Unreleased

- Hardened provider response limits and replaced runtime security assertions
  with explicit fail-closed errors.
- Converted release, training, access-policy and container smoke gates from
  optimization-sensitive assertions to explicit failures.
- Strengthened stable-release promotion evidence to require digest-bound,
  per-platform SBOM, provenance and signature identity records.

- Added offline evaluation governance for fixed-provider batch lineage,
  source/license audits, selective risk/coverage calibration and the
  `omo-human-review-v1` protocol. Live-provider calls, protected-test
  evaluation and promotion remain disabled.
- Expanded the local synthetic routing corpus to 52 records, added a SHA-256
  dataset manifest and dataset card, and kept bootstrap labels, Hub publication
  and training activation blocked pending review.
- Hardened the native inference request parser against unknown fields, duplicate
  JSON keys and malformed Unicode, and added a scoped pending DiskCache VEX
  record without relaxing strict release gates.
- Added OMO-003 benchmark preflight and OMO-004 held-out evaluation contracts;
  both produce offline evidence plans only and do not call providers or promote
  models.
- Added the manual-only OMO-014 training preflight workflow with exact code,
  dataset and base-model revisions, bounded inputs, cancellation, locked
  dependencies, resume identifiers and a dry-run-only fail-closed boundary.
- Unified the OMO-012/013 routing-classification objective as
  `omo-routing-proposal-v1` across runtime, training, evaluation and contract
  checks. The model may propose only `external_model`, `helper` or `clarify`;
  deterministic policy retains `local_answer`, `reject`, authorization and
  target eligibility.
- Added bounded ordered multi-turn serialization, duplicate-key-safe Proposal
  parsing and a deterministic train-only dataset builder with input/output
  checksums. The current 14-record output is contract evidence, not a
  training-ready corpus or trained model.
- Added the disabled OMO-016 model-promotion manifest and trusted build-time
  materializer. It verifies an immutable Hub revision, filename, size and
  SHA-256 before replacement; request-time model downloads remain impossible.
- Added the OMO-015 candidate-artifact validator. It verifies safetensors,
  tokenizer, configuration and model-card files, exact checksums, training
  lineage, held-out evidence, license provenance and the upstream rollback
  target before publication.
- Clarified the self-hosted distribution boundary: OMO publishes optional
  Docker artifacts for users to operate in their own environments and does not
  provide a project-managed production host. Multi-instance ledgers,
  request-time registry discovery and operator telemetry are not release gates.
- Added restart-durable local budget reservations and fail-closed native parser
  hardening; distributed accounting and provider reconciliation remain optional
  operator integrations, while independent security review remains a release
  gate.

## 0.1.0 development follow-up — 2026-09-14

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
- Verified the issue-first Codex/Claude workflow on reviewed PR #10 and merged
  the OMO-008–OMO-011 offline foundations in PR #11 after required CI passed.
- Hardened change-aware model/container selection, bounded upstream SSE parsing,
  typed model-proposed helper arguments and evidence-bound multi-platform
  promotion validation.

## 0.1.0 reviewer workflow hardening — 2026-09-13

- Consolidated Claude into one review-only PR workflow with draft/fork/actor
  guards, immutable action refs, credential-free checkout, timeout/turn bounds
  and per-PR cancellation.
- Added workflow regression tests and kept remote review/CI evidence separate
  from local verification claims.

## 0.1.0 development baseline — 2026-09-13

- Embedded SmolLM2-360M Q8_0 through pinned llama-cpp-python, checksum
  verification, warmup and supervised cancellation.
- Added exact decimal and bounded even-squares helpers through real Monty
  workers, strict API/configuration/proposal schemas, authentication, immutable
  registries, bounded external calls and validated upstream SSE collection.
- Added real model, sandbox, policy, provider and API tests; bundled/slim Docker
  targets; hardened Compose; native architecture CI contracts; secret scanning;
  container reports and strict release vulnerability gates.
- Kept training, schedules, automatic promotion and stable model publication
  disabled. The bundled checkpoint remains upstream SmolLM2, not an OMO
  fine-tune.
