import json
from pathlib import Path

import pytest

from scripts.check_security_report import validate


def report(*vulnerabilities):
    return {"Results": [{"Vulnerabilities": list(vulnerabilities)}]}


def vulnerability(**values):
    return {
        "VulnerabilityID": "CVE-TEST",
        "PkgName": "test-package",
        "InstalledVersion": "1.0",
        "Severity": "HIGH",
        **values,
    }


def test_security_report_preserves_findings_without_fixed_versions(tmp_path):
    path = tmp_path / "trivy.json"
    path.write_text(json.dumps(report(vulnerability(FixedVersion=None))))
    findings = validate(path)
    assert findings[0]["fixed"] is None


def test_strict_security_report_rejects_any_finding(tmp_path):
    path = tmp_path / "trivy.json"
    path.write_text(json.dumps(report(vulnerability(FixedVersion="2.0"))))
    with pytest.raises(ValueError, match="strict security"):
        validate(path, strict=True)


def test_malformed_security_report_is_rejected(tmp_path):
    path = tmp_path / "trivy.json"
    path.write_text(json.dumps(report(vulnerability(PkgName=None))))
    with pytest.raises(ValueError, match="malformed"):
        validate(path)


def test_diskcache_vex_remains_pending_and_blocked():
    vex = json.loads(Path("docs/evidence/diskcache-vex.json").read_text())

    assert vex["status"] == "pending-owner-approval"
    assert vex["advisory"]["fixed_versions"] == []
    assert vex["release_disposition"] == "blocked"
