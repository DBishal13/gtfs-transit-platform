"""Spatial query functions against the service backend's PostGIS-backed GTFS tables.

Every query below is scoped by feed_id and uses parameterized SQL exclusively (values are
always bound as %(name)s, never string-interpolated — see service/app/security/sql_safety.py).
These are the same functions both the direct REST endpoints (service/app/routers/geo.py) and,
from Phase 4, the agent's tool layer call — so whatever tenant-scoping is enforced upstream
(resolving which feed_id values a caller may query) applies identically to both entry points.
"""

from __future__ import annotations

import psycopg

from service.app.schemas.geo import StopResult

_NEAREST_STOPS_SQL = """
SELECT stop_id, stop_name, stop_lat, stop_lon,
       ST_Distance(
         stop_geom::geography,
         ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography
       ) AS distance_m
FROM stops
WHERE feed_id = %(feed_id)s AND stop_geom IS NOT NULL
ORDER BY stop_geom <-> ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)
LIMIT %(limit)s
"""

_STOPS_WITHIN_RADIUS_SQL = """
SELECT stop_id, stop_name, stop_lat, stop_lon,
       ST_Distance(
         stop_geom::geography,
         ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography
       ) AS distance_m
FROM stops
WHERE feed_id = %(feed_id)s
  AND stop_geom IS NOT NULL
  AND ST_DWithin(
        stop_geom::geography,
        ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography,
        %(radius_m)s
      )
ORDER BY distance_m
"""


def _rows_to_stops(cur: psycopg.Cursor) -> list[StopResult]:
    columns = [desc.name for desc in cur.description]
    return [StopResult(**dict(zip(columns, row))) for row in cur.fetchall()]


def nearest_stops(
    conn: psycopg.Connection, *, feed_id: str, lon: float, lat: float, limit: int = 10
) -> list[StopResult]:
    """The `limit` nearest stops to (lon, lat) in `feed_id`, ordered by distance ascending.
    Uses the <-> KNN operator so a GIST index on stop_geom (see migrations/0001) is used."""
    with conn.cursor() as cur:
        cur.execute(_NEAREST_STOPS_SQL, {"feed_id": feed_id, "lon": lon, "lat": lat, "limit": limit})
        return _rows_to_stops(cur)


def stops_within_radius(
    conn: psycopg.Connection, *, feed_id: str, lon: float, lat: float, radius_m: float
) -> list[StopResult]:
    """All stops in `feed_id` within `radius_m` meters of (lon, lat), ordered by distance
    ascending. Uses ST_DWithin on the geography cast for accurate meter-based distance."""
    with conn.cursor() as cur:
        cur.execute(
            _STOPS_WITHIN_RADIUS_SQL,
            {"feed_id": feed_id, "lon": lon, "lat": lat, "radius_m": radius_m},
        )
        return _rows_to_stops(cur)
