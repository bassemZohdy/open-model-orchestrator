"""Regression contracts for the independent, bounded PR reviewer."""

import re
import subprocess
import sys
from pathlib import Path

import yaml


def test_review_event_surface() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/claude-code-review.yml").read_text())
    events = workflow.get("on", workflow.get(True))
    assert events == {
        "pull_request": {"types": ["opened", "synchronize", "ready_for_review", "reopened"]}
    }
    assert not Path(".github/workflows/claude.yml").exists()
    assert workflow["concurrency"]["cancel-in-progress"] is True
    assert "pull_request.number" in workflow["concurrency"]["group"]


def test_reviewer_trust_and_execution_bounds() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/claude-code-review.yml").read_text())
    job = workflow["jobs"]["claude-review"]
    for clause in (
        "github.repository == 'bassemZohdy/open-model-orchestrator'",
        "github.event.pull_request.head.repo.full_name == github.repository",
        "github.event.pull_request.state == 'open'",
        "!github.event.pull_request.draft",
        "github.actor == 'bassemZohdy'",
        "github.actor == 'chatgpt-codex-connector[bot]'",
    ):
        assert clause in job["if"]
    assert job["runs-on"] == "ubuntu-24.04"
    assert 1 <= job["timeout-minutes"] <= 15
    assert job["permissions"] == {
        "contents": "read",
        "pull-requests": "read",
        "issues": "read",
        "id-token": "write",
    }
    checkout, review = job["steps"]
    assert checkout["with"]["persist-credentials"] is False
    for step in job["steps"]:
        assert re.fullmatch(r"[^@]+@[0-9a-f]{40}", step["uses"])
    inputs = review["with"]
    assert review["env"] == {"REVIEW_HEAD_SHA": "${{ github.event.pull_request.head.sha }}"}
    assert inputs["allowed_bots"] == "chatgpt-codex-connector[bot]"
    assert "allowed_non_write_users" not in inputs
    assert "secrets.CLAUDE_CODE_OAUTH_TOKEN" in inputs["claude_code_oauth_token"]
    assert "--comment" in inputs["prompt"]
    assert "Never edit files" in inputs["prompt"]
    assert "${{ env.REVIEW_HEAD_SHA }}" in inputs["prompt"]
    assert "identify that commit" in inputs["prompt"]
    assert "--max-turns 40" in inputs["claude_args"]
    assert '--disallowedTools "Edit,Write,NotebookEdit"' in inputs["claude_args"]


def test_existing_release_contract_still_passes() -> None:
    subprocess.run([sys.executable, "scripts/check_release_contract.py"], check=True)
