"""Trip/stop_times-level Parquet extract for the app's ad hoc duckdb-wasm
explore panel. Kept separate from the small JSON summaries (metrics_export.py)
because this is the one output large/detailed enough to need columnar storage
and lazy client-side loading rather than eager JSON parsing.
"""

from __future__ import annotations

from pathlib import Path

from pipeline.ingest.gtfs_loader import GTFSFeed


def export_stop_times_parquet(feed: GTFSFeed, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    merged = feed.stop_times.merge(
        feed.trips[["trip_id", "route_id", "service_id", "direction_id"]], on="trip_id", how="left"
    ).merge(
        feed.stops[["stop_id", "stop_name", "stop_lat", "stop_lon"]], on="stop_id", how="left"
    )
    merged.to_parquet(out_path, index=False)
