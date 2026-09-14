"""Select optional expensive CI suites from a complete Git change set.

The classifier is deliberately conservative: only paths known to be
documentation-only can skip both expensive suites. Unknown paths, malformed
Git output and unavailable revisions select both suites.
"""

import argparse
import subprocess
from collections.abc import Iterable
from pathlib import Path
from typing import Final

FULL_VALIDATION: Final = {"model": True, "container": True}

# These are the only paths that are safe to classify as documentation-only.
# More specific runtime/configuration paths are checked first by _classify_path.
DOCUMENTATION_FILES: Final = frozenset(
    {
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "LICENSE",
        "NOTICE",
        "PROJECT_DEFINITION.md",
        "README.md",
        "SECURITY.md",
        "TODO.md",
    }
)

MODEL_PATHS: Final = (
    "config/",
    "evaluation/",
    "models/",
    "scripts/download_model.py",
    "src/",
    "tests/test_real_model.py",
    "training/",
    "uv.lock",
)
CONTAINER_PATHS: Final = (
    ".dockerignore",
    "Dockerfile",
    "compose.yaml",
    "config/",
    "models/",
    "scripts/container_smoke.py",
    "src/",
    "uv.lock",
)
DEPENDENCY_PATHS: Final = ("build-constraints.txt", "pyproject.toml")
MODEL_ONLY_FILES: Final = frozenset(
    {
        "config/training.yaml",
        "scripts/check_evaluation_contract.py",
    }
)
CONTAINER_ONLY_FILES: Final = frozenset(
    {
        "scripts/check_security_report.py",
    }
)
CI_ONLY_FILES: Final = frozenset(
    {
        "config/publication.yaml",
        "scripts/check_publication_contract.py",
        "scripts/check_release_contract.py",
        "scripts/promote_release.py",
        "scripts/release_manifest.py",
        ".github/workflows/account-preflight.yml",
        ".github/workflows/claude-code-review.yml",
    }
)
RELEVANT_WORKFLOWS: Final = (
    ".github/workflows/ci.yml",
    ".github/workflows/release.yml",
)


def _normalise_path(path: str) -> str:
    """Return a repository-relative POSIX path, or raise for unsafe input."""
    if not path or "\x00" in path:
        raise ValueError("Git returned an invalid path")
    normalised = path.replace("\\", "/")
    while normalised.startswith("./"):
        normalised = normalised[2:]
    if not normalised or normalised.startswith("/"):
        raise ValueError("Git returned a non-relative path")
    return normalised


def _matches(path: str, patterns: tuple[str, ...]) -> bool:
    return any(
        path == pattern or (pattern.endswith("/") and path.startswith(pattern))
        for pattern in patterns
    )


def _classify_path(path: str) -> dict[str, bool] | None:
    """Classify one path; ``None`` means it is unknown and must fail closed."""
    normalised = _normalise_path(path)

    if normalised in MODEL_ONLY_FILES:
        return {"model": True, "container": False}
    if normalised in CONTAINER_ONLY_FILES:
        return {"model": False, "container": True}
    if normalised in CI_ONLY_FILES:
        return {"model": False, "container": False}

    # A dependency/build input can affect both the model and image jobs.
    if _matches(normalised, DEPENDENCY_PATHS):
        return {"model": True, "container": True}
    if _matches(normalised, MODEL_PATHS) and _matches(normalised, CONTAINER_PATHS):
        return {"model": True, "container": True}
    if _matches(normalised, MODEL_PATHS):
        return {"model": True, "container": False}
    if _matches(normalised, CONTAINER_PATHS):
        return {"model": False, "container": True}
    if normalised in RELEVANT_WORKFLOWS:
        # Changes to orchestration/release gates must exercise every expensive path.
        return {"model": True, "container": True}

    if normalised.startswith(".github/workflows/"):
        # New or renamed workflows are ambiguous until their behavior is reviewed.
        return None
    if normalised.startswith("docs/") or normalised in DOCUMENTATION_FILES:
        return {"model": False, "container": False}
    if normalised.endswith(".md"):
        return {"model": False, "container": False}
    return None


def classify(paths: Iterable[str]) -> dict[str, bool]:
    """Return the expensive suites affected by *paths*.

    Empty or unknown change sets intentionally select full validation. This
    keeps a new repository file, an unexpected workflow, or a parser change
    from silently weakening required validation.
    """
    changed = tuple(paths)
    if not changed:
        return dict(FULL_VALIDATION)

    selected = {"model": False, "container": False}
    for path in changed:
        classification = _classify_path(path)
        if classification is None:
            return dict(FULL_VALIDATION)
        selected["model"] |= classification["model"]
        selected["container"] |= classification["container"]
    return selected


def _is_missing_revision(revision: str | None) -> bool:
    return not revision or set(revision) == {"0"}


def _parse_name_status(output: bytes) -> list[str]:
    """Extract every old and new path from NUL-delimited Git name-status output."""
    try:
        fields = output.decode("utf-8").split("\x00")
    except UnicodeDecodeError as exc:
        raise ValueError("Git returned a non-UTF-8 path") from exc

    paths: list[str] = []
    index = 0
    while index < len(fields) - 1:
        status = fields[index]
        index += 1
        if not status:
            continue
        kind = status[0]
        if kind in {"R", "C"}:
            if index + 1 >= len(fields) or not fields[index] or not fields[index + 1]:
                raise ValueError("Git returned an incomplete rename/copy record")
            paths.extend((fields[index], fields[index + 1]))
            index += 2
        else:
            if index >= len(fields) or not fields[index]:
                raise ValueError("Git returned an incomplete change record")
            paths.append(fields[index])
            index += 1
    return paths


def changed_paths(base: str, head: str) -> list[str]:
    """Read all changed paths, including both sides of renames and copies."""
    if _is_missing_revision(base) or _is_missing_revision(head):
        raise ValueError("a usable base and head revision are required")
    result = subprocess.run(
        [
            "git",
            "diff",
            "--no-ext-diff",
            "--name-status",
            "-z",
            "--find-renames=50%",
            "--find-copies=50%",
            "--diff-filter=ACDMRTUXB",
            base,
            head,
        ],
        check=True,
        capture_output=True,
    )
    return _parse_name_status(result.stdout)


def select(base: str | None, head: str | None, force_full: bool = False) -> dict[str, bool]:
    """Select suites and fail safe when the event cannot provide a valid diff."""
    if force_full or _is_missing_revision(base) or _is_missing_revision(head):
        return dict(FULL_VALIDATION)
    assert base is not None and head is not None
    try:
        return classify(changed_paths(base, head))
    except (OSError, ValueError, subprocess.CalledProcessError):
        return dict(FULL_VALIDATION)


def _parse_bool(value: str) -> bool:
    lowered = value.strip().lower()
    # GitHub Actions may render a false boolean expression as an empty env value.
    if not lowered:
        return False
    if lowered not in {"true", "false"}:
        raise argparse.ArgumentTypeError("expected true or false")
    return lowered == "true"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--force-full", type=_parse_bool, default=False)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()

    selected = select(args.base, args.head, args.force_full)
    output = "".join(f"{name}={str(value).lower()}\n" for name, value in selected.items())
    if args.github_output:
        with args.github_output.open("a") as file:
            file.write(output)
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
