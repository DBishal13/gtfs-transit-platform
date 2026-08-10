"""Tests for reachability_service.py against a real PostGIS database seeded with
tests/fixtures/mini_gtfs (see service/tests/conftest.py). Skips automatically if no
database is reachable.

Scenario (see tests/fixtures/mini_gtfs/{stops,stop_times,trips,routes}.txt):
    Route R1 (trips T1, T2): S1 08:00 -> S2 08:10 -> S3 08:20
    Route R2 (trip T3):      S4 08:05 -> S2 08:25

From S1's coordinates (-80.200, 26.000) with a 15-minute budget:
    walk radius = 15 * 80 m/min = 1200m -> walk-reachable: S1 (0m), S4 (~747m)
        (S2 ~1495m and S3 ~2990m fall outside the walk radius)
    one-hop from S1 (900s remaining after 0 min walk): T1 reaches S2 in 600s (included),
        S3 would take 1200s (excluded)
    one-hop from S4 (~340s remaining after ~9.3 min walk): T3 reaches S2 in 1200s (excluded)
    => walk_only_stops = {S1, S4}, one_hop_stops = {S2}
"""

from __future__ import annotations

from service.app.services import reachability_service

ORIGIN_LON, ORIGIN_LAT = -80.200, 26.000


def test_reachability_combines_walk_and_one_hop_transit(db_conn, seeded_feed):
    result = reachability_service.compute_reachability(
        db_conn, feed_id=seeded_feed, lon=ORIGIN_LON, lat=ORIGIN_LAT, minutes=15
    )
    assert result["minutes"] == 15
    assert result["walk_radius_m"] == 15 * reachability_service.WALK_SPEED_M_PER_MIN

    walk_ids = {s.stop_id for s in result["walk_only_stops"]}
    assert walk_ids == {"S1", "S4"}

    one_hop_ids = {s.stop_id for s in result["one_hop_stops"]}
    assert one_hop_ids == {"S2"}


def test_reachability_tight_budget_yields_no_one_hop_stops(db_conn, seeded_feed):
    result = reachability_service.compute_reachability(
        db_conn, feed_id=seeded_feed, lon=ORIGIN_LON, lat=ORIGIN_LAT, minutes=1
    )
    assert {s.stop_id for s in result["walk_only_stops"]} == {"S1"}
    assert result["one_hop_stops"] == []


def test_reachability_one_hop_stops_never_duplicate_walk_reachable_stops(db_conn, seeded_feed):
    # A generous budget where S2 becomes walk-reachable too should not double-count it.
    result = reachability_service.compute_reachability(
        db_conn, feed_id=seeded_feed, lon=ORIGIN_LON, lat=ORIGIN_LAT, minutes=30
    )
    walk_ids = {s.stop_id for s in result["walk_only_stops"]}
    one_hop_ids = {s.stop_id for s in result["one_hop_stops"]}
    assert "S2" in walk_ids
    assert walk_ids & one_hop_ids == set()


def test_reachability_is_scoped_by_feed_id(db_conn, seeded_feed):
    result = reachability_service.compute_reachability(
        db_conn, feed_id="some-other-feed-not-loaded", lon=ORIGIN_LON, lat=ORIGIN_LAT, minutes=15
    )
    assert result["walk_only_stops"] == []
    assert result["one_hop_stops"] == []
