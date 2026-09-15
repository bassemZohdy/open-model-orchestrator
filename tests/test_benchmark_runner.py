import json

import pytest

from benchmarks.runner import BenchmarkManifest, dry_run_plan, load_manifest


REVISION = "a" * 40
DATASET_REVISION = "b" * 40
ROLES = (
    ("smollm2-360m", "llama-cpp", ("q8_0",)),
    ("granite", "llama-cpp", ("q4_0", "q8_0")),
    ("lfm", "llama-cpp", ("q4_0", "q8_0")),
    ("qwen", "llama-cpp", ("q4_0", "q8_0")),
    ("transformers-cpu-reference", "transformers", ("fp16",)),
)


def manifest_data() -> dict[str, object]:
    return {
        "code_sha": REVISION,
        "dataset_revision": DATASET_REVISION,
        "candidates": [
            {
                "role": role,
                "model_id": f"org/{role}",
                "revision": REVISION,
                "runtime": runtime,
                "quantizations": quantizations,
            }
            for role, runtime, quantizations in ROLES
        ],
    }


def test_manifest_requires_all_pinned_comparison_roles(tmp_path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest_data()))
    manifest, digest = load_manifest(str(path))
    plan = dry_run_plan(manifest, digest)
    assert len(manifest.candidates) == 5
    assert plan["execution"] == "disabled"
    assert plan["reference_comparison_required"] is True
    assert plan["paid_provider_calls"] is False
    assert plan["remote_execution"] is False


@pytest.mark.parametrize(
    "patch",
    [
        {"code_sha": "main"},
        {"dataset_revision": "latest"},
        {"candidates": manifest_data()["candidates"][:-1]},
    ],
)
def test_manifest_rejects_unpinned_or_incomplete_plans(patch: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        BenchmarkManifest.model_validate({**manifest_data(), **patch})


def test_transformers_reference_cannot_run_quantized(tmp_path) -> None:
    data = manifest_data()
    data["candidates"] = [
        {
            **candidate,
            "quantizations": ("q8_0",),
        }
        if candidate["role"] == "transformers-cpu-reference"
        else candidate
        for candidate in data["candidates"]
    ]
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="Transformers CPU reference"):
        load_manifest(str(path))
