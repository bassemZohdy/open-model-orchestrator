"""Classify changed paths for optional, expensive CI jobs."""

import argparse
import subprocess
from collections.abc import Iterable
from pathlib import Path, PurePosixPath

MODEL_PATHS = (
    ".github/workflows/model-validation.yml",
    "build-constraints.txt",
    "config/",
    "evaluation/",
    "models/",
    "pyproject.toml",
    "scripts/download_model.py",
    "src/",
    "tests/test_real_model.py",
    "uv.lock",
)
CONTAINER_PATHS = (
    ".dockerignore",
    ".github/workflows/ci.yml",
    "Dockerfile",
    "build-constraints.txt",
    "compose.yaml",
    "config/",
    "models/",
    "pyproject.toml",
    "scripts/container_smoke.py",
    "src/",
    "uv.lock",
)


def _matches(path: str, patterns: tuple[str, ...]) -> bool:
    normalized = PurePosixPath(path).as_posix().removeprefix("./")
    return any(
        normalized == pattern or (pattern.endswith("/") and normalized.startswith(pattern))
        for pattern in patterns
    )


def classify(paths: Iterable[str]) -> dict[str, bool]:
    """Return which expensive suites can be affected by *paths*."""
    changed = tuple(paths)
    return {
        "model": any(_matches(path, MODEL_PATHS) for path in changed),
        "container": any(_matches(path, CONTAINER_PATHS) for path in changed),
    }


def changed_paths(base: str, head: str) -> list[str]:
    """Read changed paths from git, failing rather than silently skipping CI."""
    if not base or set(base) == {"0"}:
        raise ValueError("a usable base revision is required")
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACDMRTUXB", base, head],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()

    # Manual runs and new branches without a parent deliberately run everything.
    selected = {"model": True, "container": True}
    if args.base and set(args.base) != {"0"}:
        selected = classify(changed_paths(args.base, args.head))

    output = "".join(f"{name}={str(value).lower()}\n" for name, value in selected.items())
    if args.github_output:
        with args.github_output.open("a") as file:
            file.write(output)
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
