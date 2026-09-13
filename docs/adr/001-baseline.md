# ADR 001 — conservative embedded development baseline

Date: 2026-09-13. Status: implemented baseline; quality envelope and unmeasured alternatives remain provisional.

## Model and inference

| Candidate | Verified source fact | OMO decision/evidence |
|---|---|---|
| SmolLM2-135M-Instruct | Apache-2.0, Llama architecture, primarily English | Tested Q8_0 via llama-cpp-python 0.3.35. Four-prompt keyword checks passed, but review found an incorrect extra noun claim and a truncated gravity answer. Reject as selected baseline. |
| SmolLM2-360M-Instruct | Same family and license; official Q8_0 artifact available | Selected provisionally. All four development questions produced concise answers. 40 repeated local executions plus six scope challenges passed; only four independent local questions. |
| Granite 4.0 350M | Apache-2.0; compact instruction candidate, model card/config use Granite-specific architecture | Unmeasured. Revisit against this baseline before expanding coverage; do not infer equivalence from parameter count. |
| LFM2.5 230M / 350M | Cards exist; custom LFM Open License, not Apache/MIT | Not selected. The retrieved 350M license includes a commercial revenue threshold; redistribution/deployment needs separate review. No OMO benchmark run. |
| Qwen3-0.6B | Apache-2.0; documented non-thinking mode | Higher-capacity fallback candidate; unmeasured. Not required to prove the first request path. |

Selected artifact: `HuggingFaceTB/SmolLM2-360M-Instruct-GGUF`, revision `593b5a2e04c8f3e4ee880263f93e0bd2901ad47f`, file `smollm2-360m-instruct-q8_0.gguf`, 386,404,992 bytes, SHA-256 `48ab3034d0dd401fbc721eb1df3217902fee7dab9078992d66431f09b7750201`. ChatML is explicitly selected; no arbitrary metadata template is executed. Seed 42, greedy generation, context 2048, batch 128, four threads, CPU only.

Production backend: `llama-cpp-python==0.3.35`; vendored llama.cpp commit `4df29be4f4c3673f428170fda944a5b19f743bb8`. A persistent supervised model process keeps CPU work off the API loop and permits hard cancellation/crash recovery. Only one model copy serves the API. Bounds cover queue admission, tokens and wall time. Cancelling active inference kills that worker; a subsequent request reloads it. Readiness is false during that recovery.

Transformers/PyTorch is the practical reference and likely offline tuning path, but was not deployed or benchmarked. ONNX adds a conversion/runtime path without measured benefit here. The current selection is not a completed cross-runtime benchmark. No attempt is made to optimize away the generative model with an encoder classifier.

Security review: Python binding advisory GHSA-56xg-wfcc-g829 concerns <=0.2.71; selected version is newer. The reviewed llama.cpp GGUF fix b8146 is an ancestor of the pinned vendor commit (GitHub compare reported ahead). RPC is unused. Native parsers remain in the trusted computing base. Public Monty advisories endpoint returned an empty list at review time; that is not evidence of absence of vulnerabilities. Dependency audit results and remaining container scans are tracked separately.

Sources: [SmolLM2 135M card](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct), [360M card](https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct), [official GGUF](https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct-GGUF), [Granite card](https://huggingface.co/ibm-granite/granite-4.0-350m), [Liquid license](https://huggingface.co/LiquidAI/LFM2.5-350M/blob/main/LICENSE), [Qwen card](https://huggingface.co/Qwen/Qwen3-0.6B), [Python binding](https://github.com/abetlen/llama-cpp-python), [llama.cpp security](https://github.com/ggml-org/llama.cpp/security/advisories).

## Sandbox

Select `pydantic-monty==0.0.23` including client/runtime 0.0.23. Linux AMD64 and ARM64 wheels were verified in PyPI metadata. This release supplies a native worker pool; there is no nested generic process pool. Each checkout uses one fresh worker, capped at two live workers, then recycles it. OMO's trusted launcher closes inherited descriptors, suppresses worker diagnostic stderr, and adds CPU/address-space/core/file-size bounds. Monty runs with a minimal environment and no host capabilities.

This is a language-level boundary plus process containment, not VM isolation. Monty is pre-1.0 and remains behind an explicit feature flag. Real tests exercise forbidden I/O, allocation/time/output/recursion limits, process death, cancellation and fresh state. A full Wasmtime/Python guest was not built: it would add a second interpreter/distribution without evidence that Monty is unsuitable. RestrictedPython or a bare Python subprocess is not an alternative security boundary.

Sources: [Monty security](https://github.com/pydantic/monty/blob/v0.0.23/docs/security.md), [limits](https://github.com/pydantic/monty/blob/v0.0.23/docs/resource-limits.md), [worker implementation](https://github.com/pydantic/monty/blob/v0.0.23/crates/monty-pool/src/worker.rs), [PyPI](https://pypi.org/project/pydantic-monty/), [RestrictedPython](https://restrictedpython.readthedocs.io/en/latest/), [Wasmtime security](https://docs.wasmtime.dev/security.html).

## Routing and orchestration

Use direct typed composition with bounded branches. LangGraph offers graph execution/persistence but adds little to this fixed request path; omit it until a concrete durable or graph-specific requirement appears. Routing tests construct no graph. Model proposals are finite structured labels, not authorization. Helper arguments from this uncalibrated model are not executed automatically. Local eligibility requires the selected model revision and exact evaluated single-turn prompts.

A local immutable registry filters enabled/available state, modalities/capabilities, context/output bounds, privacy and known estimated cost before configured-priority ranking. Cost is conservative UTF-8 byte token upper bound plus output reservation, with two attempts reserved. No quality scores or confidence probabilities are invented. Current-information capability is explicitly unsupported without retrieval. Unknown pricing excludes a target.

RouteLLM and RouterBench are existing routing research, models and datasets; neither is installed. RouteLLM's strong/weak outcomes do not identify the best model for an arbitrary current registry. RouterBench contains historical multi-model outcomes derived from several benchmarks; the retrieved HF card lacks a license declaration, so no dataset bytes were imported or relicensed. OMO starts with original synthetic JSONL and grouped split checks. Calibration and broader outcome comparisons remain future work.

Sources: [RouteLLM](https://github.com/lm-sys/RouteLLM), [RouterBench dataset](https://huggingface.co/datasets/withmartian/routerbench), [RouterBench paper](https://arxiv.org/abs/2403.12031), [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview), [calibration paper](https://arxiv.org/abs/1706.04599).
