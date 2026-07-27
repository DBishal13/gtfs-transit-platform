"""Service span analysis: first/last scheduled departure and trip count per
route per day type. Static GTFS has no realtime adherence data, so this (plus
headway) is the honest proxy for "how much service does this route actually
run" that schedule-only data supports.
"""

from __future__ import annotations

import pandas as pd

from pipeline.analytics.headway import compute_day_type_services
from pipeline.ingest.gtfs_loader import GTFSFeed
from pipeline.utils.time import gtfs_time_to_seconds


def compute_schedule_span(feed: GTFSFeed) -> pd.DataFrame:
    day_services = compute_day_type_services(feed.calendar)

    first_stop = (
        feed.stop_times.sort_values("stop_sequence")
        .groupby("trip_id", as_index=False)
        .first()[["trip_id", "departure_time"]]
        .rename(columns={"departure_time": "start_time"})
    )
    last_stop = (
        feed.stop_times.sort_values("stop_sequence")
        .groupby("trip_id", as_index=False)
        .last()[["trip_id", "arrival_time"]]
        .rename(columns={"arrival_time": "end_time"})
    )
    trips = feed.trips.merge(first_stop, on="trip_id").merge(last_stop, on="trip_id")
    trips["start_seconds"] = trips["start_time"].map(gtfs_time_to_seconds)
    trips["end_seconds"] = trips["end_time"].map(gtfs_time_to_seconds)
    trips = trips.dropna(subset=["start_seconds", "end_seconds"])

    rows = []
    for day_type, service_ids in day_services.items():
        subset = trips[trips["service_id"].isin(service_ids)]
        if subset.empty:
            continue
        for route_id, group in subset.groupby("route_id"):
            span_start = group["start_seconds"].min()
            span_end = group["end_seconds"].max()
            rows.append({
                "route_id": route_id,
                "day_type": day_type,
                "trip_count": len(group),
                "first_departure_min": round(span_start / 60.0, 1),
                "last_arrival_min": round(span_end / 60.0, 1),
                "span_hours": round((span_end - span_start) / 3600.0, 2),
            })
    return pd.DataFrame(rows)
