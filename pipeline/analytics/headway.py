"""Service frequency / headway analysis from static GTFS schedules.

This is schedule-based, not realtime: headway here means "minutes between
scheduled departures," derived from stop_times + calendar. calendar_dates.txt
exceptions (single-date add/remove) are intentionally not resolved to specific
calendar dates — we classify service by its weekly pattern in calendar.txt,
which is the right level of granularity for a "how frequent is this route on
a typical weekday/Saturday/Sunday" analysis.
"""

from __future__ import annotations

import pandas as pd

from pipeline.ingest.gtfs_loader import GTFSFeed
from pipeline.utils.time import bucket_for_seconds, gtfs_time_to_seconds

DAY_TYPES = ["weekday", "saturday", "sunday"]


def compute_day_type_services(calendar: pd.DataFrame) -> dict[str, set[str]]:
    """Classify each service_id into weekday/saturday/sunday by its calendar.txt flags."""
    if calendar.empty:
        return {day_type: set() for day_type in DAY_TYPES}
    weekday_mask = (
        (calendar["monday"] == 1)
        | (calendar["tuesday"] == 1)
        | (calendar["wednesday"] == 1)
        | (calendar["thursday"] == 1)
        | (calendar["friday"] == 1)
    )
    return {
        "weekday": set(calendar.loc[weekday_mask, "service_id"]),
        "saturday": set(calendar.loc[calendar["saturday"] == 1, "service_id"]),
        "sunday": set(calendar.loc[calendar["sunday"] == 1, "service_id"]),
    }


def _headway_from_sorted_seconds(seconds: list[int]) -> float | None:
    if len(seconds) < 2:
        return None
    seconds = sorted(seconds)
    diffs = [(b - a) / 60.0 for a, b in zip(seconds, seconds[1:])]
    return round(sum(diffs) / len(diffs), 1)


def compute_route_headway(feed: GTFSFeed) -> pd.DataFrame:
    """Per route_id + direction_id + day_type + time_bucket: mean headway (minutes)
    between scheduled trip start times, and the trip count backing that mean."""
    day_services = compute_day_type_services(feed.calendar)

    first_stop = (
        feed.stop_times.sort_values("stop_sequence")
        .groupby("trip_id", as_index=False)
        .first()[["trip_id", "departure_time"]]
    )
    first_stop["start_seconds"] = first_stop["departure_time"].map(gtfs_time_to_seconds)
    first_stop = first_stop.dropna(subset=["start_seconds"])

    trips = feed.trips.merge(first_stop, on="trip_id", how="inner")
    trips["direction_id"] = trips.get("direction_id", 0).fillna(0).astype(int)
    trips["time_bucket"] = trips["start_seconds"].map(bucket_for_seconds)

    rows = []
    for day_type, service_ids in day_services.items():
        subset = trips[trips["service_id"].isin(service_ids)]
        if subset.empty:
            continue
        for (route_id, direction_id, time_bucket), group in subset.groupby(
            ["route_id", "direction_id", "time_bucket"]
        ):
            headway = _headway_from_sorted_seconds(group["start_seconds"].tolist())
            if headway is None:
                continue
            rows.append({
                "route_id": route_id,
                "direction_id": int(direction_id),
                "day_type": day_type,
                "time_bucket": time_bucket,
                "avg_headway_min": headway,
                "trip_count": len(group),
            })
    return pd.DataFrame(rows)


def compute_stop_headway(feed: GTFSFeed) -> pd.DataFrame:
    """Per stop_id + day_type + time_bucket: mean headway (minutes) between any
    scheduled vehicle departure at that stop, across all routes serving it."""
    day_services = compute_day_type_services(feed.calendar)

    st = feed.stop_times.merge(feed.trips[["trip_id", "service_id"]], on="trip_id", how="inner")
    st["dep_seconds"] = st["departure_time"].map(gtfs_time_to_seconds)
    st = st.dropna(subset=["dep_seconds"])
    st["time_bucket"] = st["dep_seconds"].map(bucket_for_seconds)

    rows = []
    for day_type, service_ids in day_services.items():
        subset = st[st["service_id"].isin(service_ids)]
        if subset.empty:
            continue
        for (stop_id, time_bucket), group in subset.groupby(["stop_id", "time_bucket"]):
            headway = _headway_from_sorted_seconds(group["dep_seconds"].tolist())
            if headway is None:
                continue
            rows.append({
                "stop_id": stop_id,
                "day_type": day_type,
                "time_bucket": time_bucket,
                "avg_headway_min": headway,
                "departure_count": len(group),
            })
    return pd.DataFrame(rows)
