from pathlib import Path

import pytest

from omo.ci_changes import changed_paths, classify


@pytest.mark.parametrize("path", ["README.md", "docs/API.md", "TODO.md"])
def test_documentation_only_changes_skip_expensive_suites(path: str) -> None:
    assert classify([path]) == {"model": False, "container": False}


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("evaluation/seed.jsonl", {"model": True, "container": False}),
        ("scripts/container_smoke.py", {"model": False, "container": True}),
        ("src/omo/service.py", {"model": True, "container": True}),
        ("uv.lock", {"model": True, "container": True}),
        (".github/workflows/model-validation.yml", {"model": True, "container": False}),
        (".github/workflows/ci.yml", {"model": False, "container": True}),
    ],
)
def test_relevant_changes_select_expected_suites(path: str, expected: dict[str, bool]) -> None:
    assert classify([path]) == expected


def test_changed_paths_fails_closed_for_unusable_base() -> None:
    with pytest.raises(ValueError, match="usable base"):
        changed_paths("0" * 40, "HEAD")


def test_workflows_keep_lightweight_checks_and_force_release_validation() -> None:
    ci = Path(".github/workflows/ci.yml").read_text()
    model = Path(".github/workflows/model-validation.yml").read_text()
    release = Path(".github/workflows/release.yml").read_text()

    assert "jobs:\n  changes:" in ci
    assert "needs: [changes, checks, secrets]" in ci
    assert "needs.changes.outputs.container == 'true' || inputs.strict_security" in ci
    assert "needs.changes.outputs.model == 'true' || inputs.force" in model
    assert "force: true" in release
    assert "strict_security: true" in release
