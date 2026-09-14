import argparse
import subprocess
from pathlib import Path

import pytest
import yaml

from omo.ci_changes import _parse_bool, changed_paths, classify, select


@pytest.mark.parametrize("path", ["README.md", "docs/API.md", "TODO.md", "notes/design.md"])
def test_documentation_only_changes_skip_expensive_suites(path: str) -> None:
    assert classify([path]) == {"model": False, "container": False}


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("evaluation/seed.jsonl", {"model": True, "container": False}),
        ("scripts/download_model.py", {"model": True, "container": False}),
        ("Dockerfile", {"model": False, "container": True}),
        ("scripts/container_smoke.py", {"model": False, "container": True}),
        ("config/default.yaml", {"model": True, "container": True}),
        ("src/omo/service.py", {"model": True, "container": True}),
        ("pyproject.toml", {"model": True, "container": True}),
        ("uv.lock", {"model": True, "container": True}),
        ("training/sft.py", {"model": True, "container": False}),
        ("config/training.yaml", {"model": True, "container": False}),
        ("scripts/check_evaluation_contract.py", {"model": True, "container": False}),
        ("scripts/check_security_report.py", {"model": False, "container": True}),
        ("scripts/check_publication_contract.py", {"model": False, "container": False}),
        ("scripts/check_release_contract.py", {"model": False, "container": False}),
        ("scripts/promote_release.py", {"model": False, "container": False}),
        ("config/publication.yaml", {"model": False, "container": False}),
        (".github/workflows/ci.yml", {"model": True, "container": True}),
    ],
)
def test_relevant_changes_select_expected_suites(path: str, expected: dict[str, bool]) -> None:
    assert classify([path]) == expected


@pytest.mark.parametrize("path", [".env.example", ".github/workflows/new.yml", "new-file.json"])
def test_unknown_changes_fail_closed(path: str) -> None:
    assert classify([path]) == {"model": True, "container": True}


def test_mixed_documentation_and_runtime_changes_run_both() -> None:
    assert classify(["README.md", "src/omo/service.py"]) == {
        "model": True,
        "container": True,
    }


def test_empty_change_set_fails_closed() -> None:
    assert classify([]) == {"model": True, "container": True}


def test_changed_paths_includes_multiple_commits_and_rename_sides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()

    def git(*args: str) -> str:
        result = subprocess.run(
            ["git", *args], cwd=repository, check=True, capture_output=True, text=True
        )
        return result.stdout.strip()

    git("init", "--quiet")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "OMO tests")
    (repository / "README.md").write_text("one\n")
    (repository / "src-old.py").write_text("print(1)\n")
    git("add", ".")
    git("commit", "--quiet", "-m", "initial")
    base = git("rev-parse", "HEAD")
    (repository / "Dockerfile").write_text("FROM scratch\n")
    git("add", ".")
    git("commit", "--quiet", "-m", "docker")
    git("mv", "src-old.py", "src-new.py")
    git("commit", "--quiet", "-m", "rename")

    head = git("rev-parse", "HEAD")
    monkeypatch.chdir(repository)
    assert changed_paths(base, head) == [
        "Dockerfile",
        "src-old.py",
        "src-new.py",
    ]


def test_changed_paths_includes_deleted_relevant_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()

    def git(*args: str) -> str:
        result = subprocess.run(
            ["git", *args], cwd=repository, check=True, capture_output=True, text=True
        )
        return result.stdout.strip()

    git("init", "--quiet")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "OMO tests")
    (repository / "Dockerfile").write_text("FROM scratch\n")
    git("add", ".")
    git("commit", "--quiet", "-m", "initial")
    base = git("rev-parse", "HEAD")
    (repository / "Dockerfile").unlink()
    git("commit", "--quiet", "-am", "delete")
    head = git("rev-parse", "HEAD")
    monkeypatch.chdir(repository)

    assert changed_paths(base, head) == ["Dockerfile"]


def test_invalid_revision_is_rejected_and_selection_fails_safe() -> None:
    with pytest.raises(ValueError, match="usable base"):
        changed_paths("0" * 40, "HEAD")
    assert select("0" * 40, "HEAD") == {"model": True, "container": True}
    assert select(None, None) == {"model": True, "container": True}
    assert select("base", "head", force_full=True) == {"model": True, "container": True}


@pytest.mark.parametrize("value", ["", "false", "FALSE"])
def test_empty_or_false_force_flag_does_not_force_validation(value: str) -> None:
    assert _parse_bool(value) is False


def test_invalid_force_flag_is_rejected() -> None:
    with pytest.raises(argparse.ArgumentTypeError, match="expected true or false"):
        _parse_bool("sometimes")


def test_workflows_keep_lightweight_checks_and_force_release_validation() -> None:
    ci = yaml.safe_load(Path(".github/workflows/ci.yml").read_text())
    release = yaml.safe_load(Path(".github/workflows/release.yml").read_text())
    ci_on = ci.get("on", ci.get(True))
    release_on = release.get("on", release.get(True))

    assert "pull_request" in ci_on and "workflow_call" in ci_on
    assert ci_on["workflow_dispatch"]["inputs"]["strict_security"]["type"] == "boolean"
    assert "jobs:\n  changes:" in Path(".github/workflows/ci.yml").read_text()
    assert (
        "model: ${{ steps.select.outputs.model }}" in Path(".github/workflows/ci.yml").read_text()
    )
    assert "\n  real-model:" in Path(".github/workflows/ci.yml").read_text()
    assert "needs: [changes, checks, secrets]" in Path(".github/workflows/ci.yml").read_text()
    assert (
        "github.event.pull_request.head.sha || github.sha"
        in Path(".github/workflows/ci.yml").read_text()
    )
    assert "strict_security: true" in Path(".github/workflows/release.yml").read_text()
    assert "model-validation.yml" not in Path(".github/workflows/release.yml").read_text()
    ci_text = Path(".github/workflows/ci.yml").read_text()
    assert "uv lock --check" not in ci_text
    assert "python training/sft.py --dry-run" in ci_text
    assert set(release_on) == {"workflow_dispatch"}
