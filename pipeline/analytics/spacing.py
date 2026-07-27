"""Stop-to-stop spacing analysis: flags consecutive-stop gaps that are unusually
large for a route, which often indicate a data error (wrong stop sequence,
missing intermediate stops) rather than a genuine express segment.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from pipeline.ingest.gtfs_loader import GTFSFeed
from pipeline.utils.geo import haversine_m

OUTLIER_MIN_GAP_M = 3000  # below this, never flag regardless of statistics
OUTLIER_MAD_MULTIPLIER = 6


def compute_stop_spacing(feed: GTFSFeed) -> pd.DataFrame:
    """Per route_id + from_stop_id + to_stop_id: the consecutive-stop gap distance
    in meters (averaged across trips sharing that pair), with an `is_outlier` flag."""
    st = feed.stop_times.sort_values(["trip_id", "stop_sequence"]).copy()
    st["next_stop_id"] = st.groupby("trip_id")["stop_id"].shift(-1)
    pairs = st.dropna(subset=["next_stop_id"])[["trip_id", "stop_id", "next_stop_id"]]
    pairs = pairs.merge(feed.trips[["trip_id", "route_id"]], on="trip_id", how="inner")

    stop_coords = feed.stops.set_index("stop_id")[["stop_lat", "stop_lon"]]
    pairs = pairs.join(stop_coords.rename(columns={"stop_lat": "from_lat", "stop_lon": "from_lon"}), on="stop_id")
    pairs = pairs.join(
        stop_coords.rename(columns={"stop_lat": "to_lat", "stop_lon": "to_lon"}), on="next_stop_id"
    )
    pairs = pairs.dropna(subset=["from_lat", "from_lon", "to_lat", "to_lon"])

    pairs["gap_m"] = pairs.apply(
        lambda r: haversine_m(r["from_lon"], r["from_lat"], r["to_lon"], r["to_lat"]), axis=1
    )

    grouped = (
        pairs.groupby(["route_id", "stop_id", "next_stop_id"])["gap_m"]
        .mean()
        .reset_index()
        .rename(columns={"stop_id": "from_stop_id", "next_stop_id": "to_stop_id"})
    )
    if grouped.empty:
        grouped["is_outlier"] = pd.Series(dtype=bool)
        return grouped

    median = grouped["gap_m"].median()
    mad = (grouped["gap_m"] - median).abs().median() or 1.0
    threshold = max(OUTLIER_MIN_GAP_M, median + OUTLIER_MAD_MULTIPLIER * mad)
    grouped["is_outlier"] = grouped["gap_m"] > threshold
    grouped["gap_m"] = grouped["gap_m"].round(1)
    return grouped.sort_values("gap_m", ascending=False).reset_index(drop=True)
