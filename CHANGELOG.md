# Changelog

## 0.1.0 development baseline — 2026-09-13

- Embedded SmolLM2-360M Q8_0 through pinned llama-cpp-python, checksum validation, warmup and supervised cancellation.
- Exact decimal helper and a bounded even-squares transformation through real Monty workers.
- Strict API/configuration/proposal schemas, protected endpoints, immutable registry snapshots and hard-constraint external selection.
- One pooled OpenAI-compatible/OpenRouter adapter with bounded responses, limited 429 retries and safe failures.
- Buffered SSE delivery; no provider output rewriting or native guest-code fallback.
- Real model, sandbox, policy, provider and API tests; original split-aware seed data and offline development evaluator.
- Bundled/slim Docker targets, hardened Compose and native architecture CI contracts.
- Manual gated candidate-release workflow; training, schedules and model promotion remain disabled.
- Corrected locked native build constraints, added secret/container vulnerability scans and a strict release audit gate; the DiskCache advisory remains a publication blocker.
- Expanded container acceptance for authentication, resource bounds and real sandbox isolation; release manifests bind code/model/data/policy identities.
- Fixed a cancellation-test observation race and now require complete worker reaping rather than accepting zombie state.

Publication and platform evidence are recorded separately in docs/VALIDATION.md. This is not a production release or an OMO fine-tuned model.
