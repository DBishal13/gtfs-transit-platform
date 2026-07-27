"""Route overlap/duplication heuristic: routes sharing a large fraction of the
same stops are candidates for consolidation review. Uses Jaccard similarity of
each route's stop set rather than geometry, so it works even for feeds with
sparse/missing shapes.txt.
"""

from __future__ import annotations

from itertools import combinations

import pandas as pd

from pipeline.ingest.gtfs_loader import GTFSFeed

HIGH_OVERLAP_THRESHOLD = 0.6


def compute_route_duplication(feed: GTFSFeed) -> pd.DataFrame:
    st = feed.stop_times.merge(feed.trips[["trip_id", "route_id"]], on="trip_id", how="inner")
    stops_by_route = st.groupby("route_id")["stop_id"].apply(set)

    rows = []
    route_ids = sorted(stops_by_route.index)
    for route_a, route_b in combinations(route_ids, 2):
        stops_a, stops_b = stops_by_route[route_a], stops_by_route[route_b]
        shared = stops_a & stops_b
        union = stops_a | stops_b
        if not shared or not union:
            continue
        jaccard = len(shared) / len(union)
        rows.append({
            "route_a": route_a,
            "route_b": route_b,
            "shared_stops": len(shared),
            "route_a_stops": len(stops_a),
            "route_b_stops": len(stops_b),
            "jaccard": round(jaccard, 3),
            "high_overlap": jaccard >= HIGH_OVERLAP_THRESHOLD,
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values("jaccard", ascending=False).reset_index(drop=True)
