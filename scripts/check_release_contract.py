"""Static guard for the intentionally restricted release surface."""

import re
from pathlib import Path

import yaml


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


for path in Path(".github/workflows").glob("*.yml"):
    text = path.read_text()
    require("pull_request_target" not in text, f"unsafe pull_request_target in {path}")
    require("workflow_run:" not in text, f"unsafe workflow_run trigger in {path}")
    require("schedule:" not in text, f"unexpected schedule trigger in {path}")
    for action in re.findall(r"uses:\s+([^\s]+)", text):
        if action.startswith("./"):
            continue
        require(
            re.fullmatch(r"[^@]+@[0-9a-f]{40}", action) is not None,
            f"unpinned action {action} in {path}",
        )
    require("timeout-minutes:" in text or "uses: ./" in text, f"missing timeout in {path}")
release = yaml.safe_load(Path(".github/workflows/release.yml").read_text())
# PyYAML 1.1 resolves an unquoted `on` key to True; accept that representation.
events = release.get("on", release.get(True))
require(set(events) == {"workflow_dispatch"}, "release workflow has an unsafe trigger")
require(
    release["jobs"]["publish-platform"]["needs"] == ["validation", "security-audit"],
    "release publication bypasses required gates",
)
require(
    release["jobs"]["publish-platform"]["environment"] == "release",
    "release publication is not protected",
)
require(
    "github.ref == 'refs/heads/main'" in release["jobs"]["authorize"]["if"],
    "release authorization is not main-only",
)
require("approved_commit" in events["workflow_dispatch"]["inputs"], "release lacks commit approval")
require("training" not in release["jobs"], "release workflow can activate training")
print("Release event, dependency, action-pin and disabled-schedule contracts passed")

require(
    release["jobs"]["validation"]["with"]["strict_security"] is True,
    "release validation is not strict-security mode",
)
