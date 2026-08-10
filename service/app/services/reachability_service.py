"""Reachability: "what can I reach in N minutes from here" — a schedule-based walk +
one-transit-hop APPROXIMATION, not full multimodal routing.

Simplifications, stated plainly rather than hidden:
  - Straight-line (great-circle) walking distance, not a street network — the same
    simplification pipeline/analytics/coverage.py's walk buffers already use.
  - At most one transit boarding; no transfers.
  - No schedule wait time: a rider is assumed to board the fastest available trip through
    each walk-reachable stop immediately on arrival — optimistic for low-frequency routes.
  - One representative trip per (route, direction) serving a boarding stop, not every
    scheduled departure, to keep the query bounded.

True isochrones would need pgRouting/OpenTripPlanner and a real street network — named as
future work in service/README.md, deliberately out of scope here to keep this phase
reviewable.
"""

from __future__ import annotations

import psycopg

from pipeline.utils.time import gtfs_time_to_seconds
from service.app.schemas.geo import ReachablePoint
from service.app.services import geo_service

# Matches the ~80 m/min (400m ≈ 5min) walking-speed assumption already implicit in
# pipeline/analytics/coverage.py's BUFFER_DISTANCES_M.
WALK_SPEED_M_PER_MIN = 80.0

_REPRESENTATIVE_BOARDINGS_SQL = """
SELECT DISTINCT ON (t.route_id, t.direction_id)
       t.trip_id, st.departure_time, st.stop_sequence
FROM stop_times st
JOIN trips t ON t.feed_id = st.feed_id AND t.trip_id = st.trip_id
WHERE st.feed_id = %(feed_id)s AND st.stop_id = %(stop_id)s AND st.departure_time IS NOT NULL
ORDER BY t.route_id, t.direction_id, st.departure_time
"""

_TRIP_TAIL_SQL = """
SELECT st.stop_id, st.arrival_time, s.stop_name, s.stop_lat, s.stop_lon
FROM stop_times st
JOIN stops s ON s.feed_id = st.feed_id AND s.stop_id = st.stop_id
WHERE st.feed_id = %(feed_id)s AND st.trip_id = %(trip_id)s AND st.stop_sequence > %(from_sequence)s
ORDER BY st.stop_sequence
"""


def _one_hop_stops_from(
    conn: psycopg.Connection, *, feed_id: str, origin_stop_id: str, remaining_seconds: float
) -> dict[str, ReachablePoint]:
    """For each (route, direction) pair with a representative trip serving
    `origin_stop_id`, walk forward through that trip's remaining stops until the
    schedule-implied elapsed time since boarding would exceed `remaining_seconds`."""
    with conn.cursor() as cur:
        cur.execute(_REPRESENTATIVE_BOARDINGS_SQL, {"feed_id": feed_id, "stop_id": origin_stop_id})
        boardings = cur.fetchall()

    reached: dict[str, ReachablePoint] = {}
    for trip_id, departure_time, stop_sequence in boardings:
        boarding_seconds = gtfs_time_to_seconds(departure_time)
        if boarding_seconds is None:
            continue
        with conn.cursor() as cur:
            cur.execute(
                _TRIP_TAIL_SQL,
                {"feed_id": feed_id, "trip_id": trip_id, "from_sequence": stop_sequence},
            )
            for stop_id, arrival_time, stop_name, stop_lat, stop_lon in cur.fetchall():
                arrival_seconds = gtfs_time_to_seconds(arrival_time)
                if arrival_seconds is None or arrival_seconds < boarding_seconds:
                    continue
                if arrival_seconds - boarding_seconds > remaining_seconds:
                    break
                reached.setdefault(
                    stop_id,
                    ReachablePoint(
                        stop_id=stop_id, stop_name=stop_name, stop_lat=stop_lat, stop_lon=stop_lon
                    ),
                )
    return reached


def compute_reachability(
    conn: psycopg.Connection, *, feed_id: str, lon: float, lat: float, minutes: int
) -> dict:
    walk_radius_m = minutes * WALK_SPEED_M_PER_MIN
    walk_stops = geo_service.stops_within_radius(
        conn, feed_id=feed_id, lon=lon, lat=lat, radius_m=walk_radius_m
    )
    walk_stop_ids = {s.stop_id for s in walk_stops}

    one_hop: dict[str, ReachablePoint] = {}
    for stop in walk_stops:
        walk_minutes = stop.distance_m / WALK_SPEED_M_PER_MIN
        remaining_seconds = (minutes - walk_minutes) * 60
        if remaining_seconds <= 0:
            continue
        for stop_id, point in _one_hop_stops_from(
            conn, feed_id=feed_id, origin_stop_id=stop.stop_id, remaining_seconds=remaining_seconds
        ).items():
            if stop_id not in walk_stop_ids:
                one_hop[stop_id] = point

    return {
        "minutes": minutes,
        "walk_radius_m": walk_radius_m,
        "walk_only_stops": [
            ReachablePoint(
                stop_id=s.stop_id, stop_name=s.stop_name, stop_lat=s.stop_lat, stop_lon=s.stop_lon
            )
            for s in walk_stops
        ],
        "one_hop_stops": list(one_hop.values()),
    }
