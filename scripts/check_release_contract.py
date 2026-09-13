"""Static guard for the intentionally restricted release surface."""

import re
from pathlib import Path

import yaml

for path in Path(".github/workflows").glob("*.yml"):
    text = path.read_text()
    assert "pull_request_target" not in text
    assert "workflow_run:" not in text
    assert "schedule:" not in text
    for action in re.findall(r"uses:\s+([^\s]+)", text):
        if action.startswith("./"):
            continue
        assert re.fullmatch(r"[^@]+@[0-9a-f]{40}", action), (path, action)
    assert "timeout-minutes:" in text or "uses: ./" in text
release = yaml.safe_load(Path(".github/workflows/release.yml").read_text())
# PyYAML 1.1 resolves an unquoted `on` key to True; accept that representation.
events = release.get("on", release.get(True))
assert set(events) == {"workflow_dispatch"}
assert release["jobs"]["publish-platform"]["needs"] == ["validation", "model-validation"]
assert release["jobs"]["publish-platform"]["environment"] == "release"
assert "github.ref == 'refs/heads/main'" in release["jobs"]["authorize"]["if"]
assert "approved_commit" in events["workflow_dispatch"]["inputs"]
assert "training" not in release["jobs"]
print("Release event, dependency, action-pin and disabled-schedule contracts passed")
