"""GeoJSON -> PMTiles export for the map layer.

PMTiles (via tippecanoe) is the canonical served format because it scales to
any agency's feed size and streams efficiently over plain HTTP (range
requests), unlike raw GeoJSON. tippecanoe is a native binary that CI installs
explicitly (see .github/workflows/deploy.yml); if it isn't found on a
developer's machine we still write the GeoJSON and skip tiling rather than
failing the whole pipeline — the app falls back to loading GeoJSON directly
when a feed's manifest entry has no `tiles` asset.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import geopandas as gpd

from pipeline.ingest.gtfs_loader import GTFSFeed
from pipeline.utils.logging import get_logger

log = get_logger(__name__)


def export_routes_stops_geojson(feed: GTFSFeed, out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)

    trip_route = feed.trips.dropna(subset=["shape_id"]).drop_duplicates("shape_id")[
        ["shape_id", "route_id"]
    ]
    routes_gdf = feed.shape_geoms.merge(trip_route, on="shape_id", how="left")
    routes_gdf = routes_gdf.merge(
        feed.routes[["route_id", "route_short_name", "route_long_name", "route_color"]],
        on="route_id",
        how="left",
    )

    stops_gdf = feed.stops[["stop_id", "stop_name", "stop_code", "geometry"]].copy()

    routes_path = out_dir / "routes.geojson"
    stops_path = out_dir / "stops.geojson"
    routes_gdf.to_file(routes_path, driver="GeoJSON")
    stops_gdf.to_file(stops_path, driver="GeoJSON")
    return {"routes": routes_path, "stops": stops_path}


def build_pmtiles(
    geojson_paths: dict[str, Path], out_pmtiles: Path, tippecanoe_bin: str = "tippecanoe"
) -> bool:
    """Tile routes+stops GeoJSON into one .pmtiles archive. Returns False (and logs a
    warning) if tippecanoe isn't installed, rather than raising."""
    if shutil.which(tippecanoe_bin) is None:
        log.warning(
            "tippecanoe not found on PATH; skipping PMTiles generation. "
            "The app will fall back to raw GeoJSON for this feed."
        )
        return False

    out_pmtiles.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        tippecanoe_bin,
        "-o", str(out_pmtiles),
        "--force",
        "-zg",
        "--drop-densest-as-needed",
        "-L", f"routes:{geojson_paths['routes']}",
        "-L", f"stops:{geojson_paths['stops']}",
    ]
    log.info("Building PMTiles: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log.error("tippecanoe failed: %s", result.stderr[-2000:])
        return False
    return True
