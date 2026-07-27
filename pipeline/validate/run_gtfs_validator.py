"""Wrapper around MobilityData's official gtfs-validator (Java CLI).

This is optional at the code level: if Java or the validator jar isn't
available (e.g. local dev on a machine without Java installed), we log a
warning and return None so the pipeline degrades to the custom quick_checks
only. CI installs Java + downloads a pinned jar version explicitly so the
full validator always runs there. See docs/adding-a-feed.md.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from pipeline.utils.logging import get_logger

log = get_logger(__name__)

DEFAULT_JAR_ENV = "GTFS_VALIDATOR_JAR"


def _find_jar(validator_jar: Path | None) -> Path | None:
    import os

    if validator_jar and validator_jar.exists():
        return validator_jar
    env_path = os.environ.get(DEFAULT_JAR_ENV)
    if env_path and Path(env_path).exists():
        return Path(env_path)
    return None


def run_official_validator(gtfs_zip: Path, output_dir: Path, validator_jar: Path | None = None) -> dict | None:
    """Run the official validator jar against a GTFS zip; return its parsed report.json.

    Returns None (with a warning logged) if Java or the jar isn't available —
    callers must treat this as "validator did not run", not "feed passed validation".
    """
    jar = _find_jar(validator_jar)
    if shutil.which("java") is None or jar is None:
        log.warning(
            "Java and/or the gtfs-validator jar are not available; skipping the official "
            "validator and relying on quick_checks only. Set %s to run it locally.",
            DEFAULT_JAR_ENV,
        )
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "java", "-jar", str(jar),
        "--input", str(gtfs_zip),
        "--output_base", str(output_dir),
    ]
    log.info("Running official GTFS validator: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode not in (0, 1):  # validator exits 1 when the feed has errors, that's expected
        log.error("gtfs-validator failed to run: %s", result.stderr[-2000:])
        return None

    report_path = output_dir / "report.json"
    if not report_path.exists():
        log.error("gtfs-validator did not produce report.json; stdout: %s", result.stdout[-2000:])
        return None

    return json.loads(report_path.read_text(encoding="utf-8"))
