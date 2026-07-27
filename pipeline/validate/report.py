"""Merge the official validator report (if it ran) and our custom quick_checks
into one `quality_report` JSON shape consumed by the DataQuality dashboard.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pipeline.validate.quick_checks import Finding


def _summarize_official_report(report: dict[str, Any]) -> dict[str, Any]:
    notices = report.get("notices", [])
    by_severity: dict[str, int] = {}
    for notice in notices:
        severity = str(notice.get("severity", "UNKNOWN")).upper()
        by_severity[severity] = by_severity.get(severity, 0) + int(notice.get("totalNotices", 1))
    return {
        "ran": True,
        "notice_count_by_severity": by_severity,
        "notice_types": [
            {
                "code": n.get("code"),
                "severity": n.get("severity"),
                "total_notices": n.get("totalNotices"),
            }
            for n in notices
        ],
    }


def build_quality_report(
    feed_id: str,
    custom_findings: list[Finding],
    official_report: dict[str, Any] | None,
) -> dict[str, Any]:
    custom = [f.to_dict() for f in custom_findings]
    custom_errors = sum(1 for f in custom if f["severity"] == "error")
    custom_warnings = sum(1 for f in custom if f["severity"] == "warning")

    if official_report is not None:
        official = _summarize_official_report(official_report)
        official_errors = official["notice_count_by_severity"].get("ERROR", 0)
    else:
        official = {"ran": False, "notice_count_by_severity": {}, "notice_types": []}
        official_errors = 0

    total_errors = custom_errors + official_errors
    status = "fail" if total_errors > 0 else ("warn" if custom_warnings > 0 else "pass")

    return {
        "feed_id": feed_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "official_validator": official,
        "custom_checks": custom,
        "summary": {
            "status": status,
            "custom_errors": custom_errors,
            "custom_warnings": custom_warnings,
            "official_errors": official_errors,
        },
    }
