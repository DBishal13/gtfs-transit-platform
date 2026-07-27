"""GTFS time parsing and time-of-day bucketing.

GTFS `arrival_time`/`departure_time` values are HH:MM:SS strings where HH may
exceed 23 for trips that run past midnight (e.g. "25:10:00" for 1:10 AM the
next service day). We keep times as seconds-since-midnight (which can exceed
86400) so ordering within a service day stays correct, and reduce modulo
86400 only when bucketing into a time-of-day period for display/analytics.
"""

from __future__ import annotations

# (label, start_seconds_inclusive, end_seconds_exclusive) in wall-clock seconds [0, 86400).
# "night" wraps past midnight and is handled specially in bucket_for_seconds.
TIME_OF_DAY_BUCKETS = [
    ("early_am", 4 * 3600, 6 * 3600),
    ("am_peak", 6 * 3600, 9 * 3600),
    ("midday", 9 * 3600, 15 * 3600),
    ("pm_peak", 15 * 3600, 19 * 3600),
    ("evening", 19 * 3600, 22 * 3600),
    ("night", 22 * 3600, 24 * 3600),  # plus [0, 4*3600) — see bucket_for_seconds
]


def gtfs_time_to_seconds(value: str) -> int | None:
    """Parse an "HH:MM:SS" GTFS time string to seconds-since-midnight (may exceed 86400)."""
    if value is None or value == "":
        return None
    parts = value.strip().split(":")
    if len(parts) != 3:
        return None
    hours, minutes, seconds = (int(p) for p in parts)
    return hours * 3600 + minutes * 60 + seconds


def bucket_for_seconds(seconds: int) -> str:
    """Map seconds-since-midnight (possibly >= 86400) to a time-of-day bucket label."""
    wall_clock = seconds % 86400
    if wall_clock < 4 * 3600:
        return "night"
    for label, start, end in TIME_OF_DAY_BUCKETS:
        if start <= wall_clock < end:
            return label
    return "night"


SERVICE_DAY_ORDER = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
