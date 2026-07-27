"""Load a GTFS zip into typed pandas/geopandas frames."""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point

from pipeline.ingest.schema import DTYPES, FLOAT_COLUMNS, OPTIONAL_FILES, REQUIRED_FILES
from pipeline.utils.geo import WGS84
from pipeline.utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class GTFSFeed:
    feed_id: str
    agency: pd.DataFrame
    routes: pd.DataFrame
    trips: pd.DataFrame
    stops: gpd.GeoDataFrame
    stop_times: pd.DataFrame
    calendar: pd.DataFrame
    calendar_dates: pd.DataFrame
    shapes: pd.DataFrame
    shape_geoms: gpd.GeoDataFrame


def _read_table(zf: zipfile.ZipFile, filename: str) -> pd.DataFrame | None:
    if filename not in zf.namelist():
        return None
    dtype = DTYPES.get(filename, {})
    with zf.open(filename) as fh:
        df = pd.read_csv(fh, dtype=dtype)
    for col in FLOAT_COLUMNS.get(filename, []):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _empty(filename: str) -> pd.DataFrame:
    return pd.DataFrame(columns=list(DTYPES.get(filename, {}).keys()))


def _build_stop_geometries(stops: pd.DataFrame) -> gpd.GeoDataFrame:
    geometry = [Point(lon, lat) for lon, lat in zip(stops["stop_lon"], stops["stop_lat"])]
    return gpd.GeoDataFrame(stops, geometry=geometry, crs=WGS84)


def _build_shape_geometries(shapes: pd.DataFrame) -> gpd.GeoDataFrame:
    if shapes.empty:
        return gpd.GeoDataFrame(columns=["shape_id", "geometry"], geometry="geometry", crs=WGS84)
    records = []
    ordered = shapes.sort_values(["shape_id", "shape_pt_sequence"])
    for shape_id, group in ordered.groupby("shape_id", sort=False):
        coords = list(zip(group["shape_pt_lon"], group["shape_pt_lat"]))
        if len(coords) >= 2:
            records.append({"shape_id": shape_id, "geometry": LineString(coords)})
        else:
            log.warning("shape %s has fewer than 2 points, skipping", shape_id)
    return gpd.GeoDataFrame(records, geometry="geometry", crs=WGS84)


def load_gtfs(zip_path: Path, feed_id: str) -> GTFSFeed:
    """Read a GTFS zip archive into a GTFSFeed of typed frames + derived geometries."""
    zip_path = Path(zip_path)
    with zipfile.ZipFile(zip_path) as zf:
        available = set(zf.namelist())
        missing_required = [f for f in REQUIRED_FILES if f not in available]
        if missing_required:
            raise ValueError(f"Feed '{feed_id}' is missing required GTFS files: {missing_required}")

        agency = _read_table(zf, "agency.txt")
        routes = _read_table(zf, "routes.txt")
        trips = _read_table(zf, "trips.txt")
        stops_raw = _read_table(zf, "stops.txt")
        stop_times = _read_table(zf, "stop_times.txt")
        calendar = _read_table(zf, "calendar.txt")
        if calendar is None:
            calendar = _empty("calendar.txt")
        calendar_dates = _read_table(zf, "calendar_dates.txt")
        if calendar_dates is None:
            calendar_dates = _empty("calendar_dates.txt")
        shapes = _read_table(zf, "shapes.txt")
        if shapes is None:
            shapes = _empty("shapes.txt")

    stops = _build_stop_geometries(stops_raw)
    shape_geoms = _build_shape_geometries(shapes)

    log.info(
        "Loaded feed '%s': %d routes, %d trips, %d stops, %d stop_times, %d shapes",
        feed_id,
        len(routes),
        len(trips),
        len(stops),
        len(stop_times),
        len(shape_geoms),
    )

    return GTFSFeed(
        feed_id=feed_id,
        agency=agency,
        routes=routes,
        trips=trips,
        stops=stops,
        stop_times=stop_times,
        calendar=calendar,
        calendar_dates=calendar_dates,
        shapes=shapes,
        shape_geoms=shape_geoms,
    )
