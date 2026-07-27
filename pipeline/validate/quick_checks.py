"""Custom referential-integrity and sanity checks the official GTFS validator
doesn't cover (or that we want available even when Java/the validator jar
isn't installed, e.g. for fast local iteration).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pipeline.ingest.gtfs_loader import GTFSFeed


@dataclass
class Finding:
    check: str
    severity: str  # "error" | "warning"
    message: str
    count: int = 0
    sample: list[Any] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "check": self.check,
            "severity": self.severity,
            "message": self.message,
            "count": self.count,
            "sample": self.sample[:10],
        }


def _missing_refs(child_col, child_ids, parent_ids) -> list:
    parent_set = set(parent_ids.dropna())
    child_ids = child_ids.dropna()
    bad = child_ids[~child_ids.isin(parent_set)]
    return sorted(set(bad.tolist()))


def run_quick_checks(feed: GTFSFeed) -> list[Finding]:
    findings: list[Finding] = []

    # Referential integrity
    bad = _missing_refs("route_id", feed.trips["route_id"], feed.routes["route_id"])
    if bad:
        findings.append(Finding(
            "trips_reference_valid_routes", "error",
            f"{len(bad)} trip(s) reference a route_id not present in routes.txt", len(bad), bad,
        ))

    known_services = set(feed.calendar["service_id"].dropna()) | set(
        feed.calendar_dates["service_id"].dropna()
    )
    bad = sorted(set(feed.trips["service_id"].dropna()) - known_services)
    if bad:
        findings.append(Finding(
            "trips_reference_valid_services", "error",
            f"{len(bad)} service_id(s) used by trips are missing from calendar.txt/calendar_dates.txt",
            len(bad), bad,
        ))

    bad = _missing_refs("trip_id", feed.stop_times["trip_id"], feed.trips["trip_id"])
    if bad:
        findings.append(Finding(
            "stop_times_reference_valid_trips", "error",
            f"{len(bad)} trip_id(s) in stop_times.txt are missing from trips.txt", len(bad), bad,
        ))

    bad = _missing_refs("stop_id", feed.stop_times["stop_id"], feed.stops["stop_id"])
    if bad:
        findings.append(Finding(
            "stop_times_reference_valid_stops", "error",
            f"{len(bad)} stop_id(s) in stop_times.txt are missing from stops.txt", len(bad), bad,
        ))

    if "shape_id" in feed.trips.columns and not feed.shapes.empty:
        trip_shapes = feed.trips["shape_id"].dropna()
        bad = sorted(set(trip_shapes) - set(feed.shape_geoms["shape_id"]))
        if bad:
            findings.append(Finding(
                "trips_reference_valid_shapes", "error",
                f"{len(bad)} shape_id(s) used by trips are missing from shapes.txt", len(bad), bad,
            ))
        orphans = sorted(set(feed.shape_geoms["shape_id"]) - set(trip_shapes))
        if orphans:
            findings.append(Finding(
                "orphan_shapes", "warning",
                f"{len(orphans)} shape(s) are not referenced by any trip", len(orphans), orphans,
            ))

    # Duplicate primary keys
    dup_stops = feed.stops["stop_id"][feed.stops["stop_id"].duplicated()].unique().tolist()
    if dup_stops:
        findings.append(Finding(
            "duplicate_stop_ids", "error",
            f"{len(dup_stops)} duplicate stop_id(s) in stops.txt", len(dup_stops), dup_stops,
        ))

    # Coordinate sanity
    bad_coords = feed.stops[
        (feed.stops["stop_lat"].abs() > 90)
        | (feed.stops["stop_lon"].abs() > 180)
        | ((feed.stops["stop_lat"] == 0) & (feed.stops["stop_lon"] == 0))
    ]
    if not bad_coords.empty:
        findings.append(Finding(
            "stop_coordinates_sane", "error",
            f"{len(bad_coords)} stop(s) have out-of-range or null-island coordinates",
            len(bad_coords), bad_coords["stop_id"].tolist(),
        ))

    return findings
