# Codex task: harden Claude workflows

Status: assigned for implementation; this initial commit is a task brief only.

## Reproduced defect

At main f666f6dbcb333e96a22530d7ddf3a357b0355738:
`uv run --no-sync python scripts/check_release_contract.py` fails on
`.github/workflows/claude.yml` using `actions/checkout@v4`.
Both Claude workflows use mutable action tags and lack job timeouts.

## Scope and acceptance

- Read AGENTS.md and its required project documentation first. Work only on OMO.
- Harden both Claude workflows. Verify full 40-character action commit SHAs against upstream sources, choose explicit supported runners, set bounded job timeouts, and disable persisted checkout credentials.
- Preserve the configured CLAUDE_CODE_OAUTH_TOKEN secret and the review plugin. Do not expose or replace secrets.
- Keep automatic independent review on opened, synchronize, ready_for_review and reopened PR events. Skip drafts, restrict secret-bearing execution to trusted same-repository PRs, and apply appropriate least privilege and concurrency.
- Check whether Codex-authored pushes are accepted by the Claude action. If a bot exception is required, allow only a verified exact identity with a trusted-repository guard; never allow all bots or weaken authorization. Report any owner-only configuration blocker.
- Keep Claude as reviewer, not an autonomous implementation agent. Preserve authorized manual review requests.
- Add meaningful regression coverage for these workflow guarantees. Do not weaken scripts/check_release_contract.py, release gates, or tests merely to get green CI.
- Update TODO.md / relevant documentation with implemented, tested and blocked status and reproduction evidence.
- Run uv sync --locked; ruff check; ruff format --check; mypy; pytest -m 'not model' -q; and python scripts/check_release_contract.py using uv run --no-sync. Report exact results and any unrelated existing failures.
- Commit and push implementation to this PR branch. Mark this PR ready for review after implementation so the existing ready_for_review event requests Claude's automatic review. If unable to do so, report the blocker.
- Report exact commit SHA and CI/review links. Leave PR open for owner approval. Do not merge, publish, change release secrets, enable paid training, scheduled jobs, or model promotion.

The developer is Codex; Claude is the independent reviewer. Do not claim an acknowledgement reaction means implementation or review completed.
