"""Assembles manifest.json — the single file the frontend fetches first to
discover which feeds exist and where each feed's assets live. See
docs/data-contract.md for the authoritative shape.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pipeline.config import FeedConfig
from pipeline.ingest.gtfs_loader import GTFSFeed

SCHEMA_VERSION = 1


def compute_bbox(feed: GTFSFeed) -> list[float]:
    minx, miny, maxx, maxy = feed.stops.total_bounds
    return [round(v, 5) for v in (minx, miny, maxx, maxy)]


def build_feed_entry(
    feed_config: FeedConfig,
    feed: GTFSFeed,
    data_url_prefix: str,
    has_pmtiles: bool,
    has_parquet: bool,
) -> dict[str, Any]:
    prefix = f"{data_url_prefix}/{feed_config.id}"
    assets: dict[str, Any] = {
        "routes_summary": f"{prefix}/routes_summary.json",
        "headway": f"{prefix}/headway.json",
        "coverage": f"{prefix}/coverage.json",
        "quality": f"{prefix}/quality.json",
        "spacing": f"{prefix}/spacing.json",
        "duplication": f"{prefix}/duplication.json",
        "schedule_span": f"{prefix}/schedule_span.json",
        "routes_geojson": f"{prefix}/routes.geojson",
        "stops_geojson": f"{prefix}/stops.geojson",
    }
    assets["tiles"] = f"{prefix}/transit.pmtiles" if has_pmtiles else None
    assets["stop_times_parquet"] = f"{prefix}/stop_times.parquet" if has_parquet else None

    return {
        "id": feed_config.id,
        "name": feed_config.name,
        "region": feed_config.region,
        "source_url": feed_config.source_url,
        "license": feed_config.license,
        "bbox": compute_bbox(feed),
        "counts": {
            "routes": int(feed.routes["route_id"].nunique()),
            "stops": int(feed.stops["stop_id"].nunique()),
            "trips": int(feed.trips["trip_id"].nunique()),
        },
        "assets": assets,
        "updated_at": datetime.now(UTC).isoformat(),
    }


def build_manifest(feed_entries: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "feeds": feed_entries,
    }


def write_manifest(manifest: dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
