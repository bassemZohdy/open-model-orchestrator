# OMO engineering instructions

Work only in bassemZohdy/open-model-orchestrator. Do not modify or introduce relationships with the owner's other agent projects. Preserve existing branches and edits. Fetch current state before changing an existing checkout. Use a dedicated branch and a PR; do not force-push or merge failing/unverified changes. Merge requires owner authorization.

Read README.md, docs/adr/001-baseline.md, docs/SECURITY_MODEL.md and TODO.md. Required checks:

- `uv sync --locked --build-constraint build-constraints.txt`
- `uv run --no-sync ruff check .` and `uv run --no-sync ruff format --check .`
- `uv run --no-sync mypy`
- `uv run --no-sync pytest -m 'not model' -q`
- For inference changes, download the pinned artifact and run `pytest -m model` plus the development evaluator.
- For Docker/release changes, pass native container acceptance and inspect the actual head CI results.

No native eval/exec fallback for guest code. Preserve typed policy boundaries and full external conversation history. New model revisions do not inherit local eligibility. Never load pickle, remote model code, arbitrary endpoints or user-supplied executable paths. Keep runtime credentials distinct from publishing credentials.

No paid training/inference sweep, scheduled jobs, automatic tuning or promotion without explicit owner budget and operating approval. Current training command is a dry-run preparation tool, not an executable trainer. Do not call it implemented training.

Record measurements as observations, upstream documentation as claims, and unrun platform tests as unverified. Keep TODO.md limited to remaining work; move completed work to CHANGELOG.md. Do not fabricate model, Docker or HF artifact IDs or publication success.
