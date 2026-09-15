# Benchmark preparation

OMO-003 compares the pinned 360M baseline, Granite, LFM and Qwen through the
same llama.cpp envelope, with a Transformers CPU reference kept separate from
quantized comparisons. The repository owns the manifest contract and plan
serialization; it does not silently download weights or execute a sweep.

Create an owner-reviewed JSON manifest with exact 40-character revisions:

```json
{
  "code_sha": "<40-character application commit>",
  "dataset_revision": "<40-character dataset revision>",
  "candidates": [
    {
      "role": "smollm2-360m",
      "model_id": "HuggingFaceTB/SmolLM2-360M-Instruct-GGUF",
      "revision": "<40-character model revision>",
      "runtime": "llama-cpp",
      "quantizations": ["q8_0"],
      "license_decision": "approved"
    },
    {
      "role": "granite",
      "model_id": "<reviewed Granite model>",
      "revision": "<40-character model revision>",
      "runtime": "llama-cpp",
      "quantizations": ["q4_0", "q8_0"],
      "license_decision": "pending"
    },
    {
      "role": "lfm",
      "model_id": "<reviewed LFM model>",
      "revision": "<40-character model revision>",
      "runtime": "llama-cpp",
      "quantizations": ["q4_0", "q8_0"],
      "license_decision": "pending"
    },
    {
      "role": "qwen",
      "model_id": "<reviewed Qwen model>",
      "revision": "<40-character model revision>",
      "runtime": "llama-cpp",
      "quantizations": ["q4_0", "q8_0"],
      "license_decision": "pending"
    },
    {
      "role": "transformers-cpu-reference",
      "model_id": "<reviewed Transformers reference>",
      "revision": "<40-character model revision>",
      "runtime": "transformers",
      "quantizations": ["fp16"],
      "license_decision": "pending"
    }
  ],
  "execution": "dry-run-only"
}
```

Validate or print the deterministic plan:

```bash
uv run --no-sync python benchmarks/runner.py \
  --manifest path/to/benchmark.json --validate
uv run --no-sync python benchmarks/runner.py \
  --manifest path/to/benchmark.json --dry-run
```

The planner rejects floating revisions, missing comparison roles and a quantized
Transformers reference. It records the application and dataset revisions so
results cannot be detached from the evaluated source. Execution, paid provider
calls, remote jobs and model promotion remain disabled. Full Q4/Q8 sweeps,
license acceptance and hardware/budget approval are required before an actual
comparison can be claimed.
