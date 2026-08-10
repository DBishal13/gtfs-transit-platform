"""Tests for service/app/services/geo_service.py against a real PostGIS database seeded
with tests/fixtures/mini_gtfs (see service/tests/conftest.py). Skips automatically if no
database is reachable.

Fixture stop coordinates (tests/fixtures/mini_gtfs/stops.txt):
    S1  26.000, -80.200
    S2  26.010, -80.190
    S3  26.020, -80.180
    S4  26.005, -80.205

Querying from S1's exact coordinates, distance ordering is S1 (0m) < S4 (~750m) <
S2 (~1500m) < S3 (~3000m).
"""

from __future__ import annotations

from service.app.services import geo_service

ORIGIN_LON, ORIGIN_LAT = -80.200, 26.000


def test_nearest_stops_orders_by_distance(db_conn, seeded_feed):
    stops = geo_service.nearest_stops(
        db_conn, feed_id=seeded_feed, lon=ORIGIN_LON, lat=ORIGIN_LAT, limit=4
    )
    assert [s.stop_id for s in stops] == ["S1", "S4", "S2", "S3"]
    assert stops[0].distance_m < 1.0
    assert sorted(s.distance_m for s in stops) == [s.distance_m for s in stops]


def test_nearest_stops_respects_limit(db_conn, seeded_feed):
    stops = geo_service.nearest_stops(
        db_conn, feed_id=seeded_feed, lon=ORIGIN_LON, lat=ORIGIN_LAT, limit=1
    )
    assert [s.stop_id for s in stops] == ["S1"]


def test_stops_within_radius_excludes_farther_stops(db_conn, seeded_feed):
    stops = geo_service.stops_within_radius(
        db_conn, feed_id=seeded_feed, lon=ORIGIN_LON, lat=ORIGIN_LAT, radius_m=800
    )
    assert {s.stop_id for s in stops} == {"S1", "S4"}
    assert stops == sorted(stops, key=lambda s: s.distance_m)


def test_stops_within_radius_tight_bound_returns_only_origin_stop(db_conn, seeded_feed):
    stops = geo_service.stops_within_radius(
        db_conn, feed_id=seeded_feed, lon=ORIGIN_LON, lat=ORIGIN_LAT, radius_m=50
    )
    assert [s.stop_id for s in stops] == ["S1"]


def test_queries_are_scoped_by_feed_id(db_conn, seeded_feed):
    stops = geo_service.nearest_stops(
        db_conn, feed_id="some-other-feed-not-loaded", lon=ORIGIN_LON, lat=ORIGIN_LAT, limit=10
    )
    assert stops == []
