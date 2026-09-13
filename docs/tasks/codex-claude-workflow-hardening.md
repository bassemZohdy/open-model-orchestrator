# Codex task: harden Claude workflows

Status: implemented directly in PR #3 after Codex cloud reported a missing repository environment. Remote CI and independent review must be checked on the final head.

## Final scope adjustment

The owner approved fixing this PR directly and trying issue-first delegation later. Consolidated Claude into one automatic PR-review workflow instead of retaining the comment-driven assistant. Manual retries use GitHub Actions **Re-run jobs**; arbitrary comment commands no longer invoke Claude after merge. This supersedes the original two-workflow/manual-mention requirements below.

Review skips drafts and forks, allows only the owner or verified Codex connector actor, pins actions, has a 15-minute timeout, a 20-turn bound, and per-PR cancellation. The OAuth secret is unchanged. Claude is instructed to review only with edit/write tools denied. The installed GitHub App still has broader permissions: these controls are not a standalone security sandbox. The upstream plugin is dynamically fetched, so action pinning does not make the entire toolchain reproducible.

Action source: https://github.com/anthropics/claude-code-action/commit/9cdae7f0d995e3ba7c33f226087fdf82a59cd520 (v1 resolved 2026-09-13).

Reproduce: `uv sync --locked`, `uv run --no-sync ruff check .`, `uv run --no-sync ruff format --check .`, `uv run --no-sync mypy`, `uv run --no-sync pytest -m 'not model' -q`, `uv run --no-sync python scripts/check_release_contract.py`.

No inference, Docker, release gates, publication, scheduling, training, or promotion changes. Expensive CI selection is OMO-013; cloud delegation is OMO-012.

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
