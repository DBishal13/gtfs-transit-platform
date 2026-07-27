"""Expected columns/dtypes per GTFS file.

All ID columns are read as strings — GTFS ids are opaque tokens (some agencies
use zero-padded numerics like "0003"), so letting pandas infer numeric dtypes
silently corrupts them. Optional files/columns are tolerated; only the columns
listed in REQUIRED_FILES must be present for a feed to be usable.
"""

from __future__ import annotations

REQUIRED_FILES = ["agency.txt", "routes.txt", "trips.txt", "stops.txt", "stop_times.txt"]
OPTIONAL_FILES = ["calendar.txt", "calendar_dates.txt", "shapes.txt", "feed_info.txt"]

# dtype maps passed straight to pandas.read_csv(dtype=...). Columns not listed
# are left to pandas' default inference (fine for numeric metrics like sequence
# ints, lat/lon floats read separately below).
DTYPES: dict[str, dict[str, str]] = {
    "agency.txt": {"agency_id": "string", "agency_name": "string"},
    "routes.txt": {
        "route_id": "string",
        "agency_id": "string",
        "route_short_name": "string",
        "route_long_name": "string",
        "route_color": "string",
        "route_text_color": "string",
    },
    "trips.txt": {
        "route_id": "string",
        "service_id": "string",
        "trip_id": "string",
        "shape_id": "string",
        "block_id": "string",
    },
    "stops.txt": {
        "stop_id": "string",
        "stop_code": "string",
        "parent_station": "string",
        "zone_id": "string",
    },
    "stop_times.txt": {
        "trip_id": "string",
        "stop_id": "string",
        "arrival_time": "string",
        "departure_time": "string",
    },
    "calendar.txt": {"service_id": "string"},
    "calendar_dates.txt": {"service_id": "string"},
    "shapes.txt": {"shape_id": "string"},
}

FLOAT_COLUMNS: dict[str, list[str]] = {
    "stops.txt": ["stop_lat", "stop_lon"],
    "shapes.txt": ["shape_pt_lat", "shape_pt_lon", "shape_dist_traveled"],
}
