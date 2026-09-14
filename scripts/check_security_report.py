"""Summarize Trivy findings without creating an allow-list bypass.

Normal CI records HIGH/CRITICAL findings for review. Release mode fails when
any such finding is present, including findings without a fixed version.
"""

import argparse
import json
from pathlib import Path
from typing import Any


def findings(report: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for scan in report.get("Results", []):
        for vulnerability in scan.get("Vulnerabilities", []) or []:
            item = {
                "id": vulnerability.get("VulnerabilityID"),
                "package": vulnerability.get("PkgName"),
                "installed": vulnerability.get("InstalledVersion"),
                "severity": vulnerability.get("Severity"),
                "fixed": vulnerability.get("FixedVersion"),
            }
            if not all(item[key] for key in ("id", "package", "installed", "severity")):
                raise ValueError("malformed vulnerability finding")
            result.append(item)
    return result


def validate(path: Path, strict: bool = False) -> list[dict[str, Any]]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError("Trivy report must be an object")
    result = findings(data)
    missing_fix = sum(not finding["fixed"] for finding in result)
    print(
        json.dumps(
            {
                "vulnerability_findings": result,
                "finding_count": len(result),
                "findings_without_fixed_version": missing_fix,
                "manual_review_required": bool(result),
            }
        )
    )
    if strict and result:
        raise ValueError("strict security gate rejected HIGH/CRITICAL findings")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    validate(args.report, args.strict)
