"""Rolls up per-feed analytics outputs into the top-line KPIs the Compare page
renders side-by-side across agencies. This module only aggregates numbers
already computed by the other analytics modules — it does no GTFS parsing.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from pipeline.ingest.gtfs_loader import GTFSFeed


def summarize_feed(
    feed: GTFSFeed,
    route_headway: pd.DataFrame,
    coverage: dict,
    quality_report: dict,
) -> dict[str, Any]:
    weekday_headway = route_headway[route_headway["day_type"] == "weekday"]
    avg_weekday_headway = (
        round(float(weekday_headway["avg_headway_min"].mean()), 1)
        if not weekday_headway.empty
        else None
    )

    population = coverage.get("population")
    pct_covered_400m = (
        population["by_buffer_m"]["400"]["pct_of_total_population"]
        if population
        else None
    )

    return {
        "feed_id": feed.feed_id,
        "route_count": int(feed.routes["route_id"].nunique()),
        "stop_count": int(feed.stops["stop_id"].nunique()),
        "trip_count": int(feed.trips["trip_id"].nunique()),
        "avg_weekday_headway_min": avg_weekday_headway,
        "pct_population_covered_400m": pct_covered_400m,
        "quality_status": quality_report["summary"]["status"],
        "quality_errors": (
            quality_report["summary"]["custom_errors"] + quality_report["summary"]["official_errors"]
        ),
    }


def build_comparison(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    return {"feeds": summaries}
