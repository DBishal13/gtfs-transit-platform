from pipeline.analytics.headway import compute_route_headway, compute_stop_headway


def test_route_headway_weekday_am_peak(mini_feed):
    df = compute_route_headway(mini_feed)
    row = df[(df.route_id == "R1") & (df.day_type == "weekday") & (df.time_bucket == "am_peak")]
    assert len(row) == 1
    assert row.iloc[0]["avg_headway_min"] == 30.0
    assert row.iloc[0]["trip_count"] == 2


def test_stop_headway_aggregates_across_routes(mini_feed):
    df = compute_stop_headway(mini_feed)
    row = df[(df.stop_id == "S2") & (df.day_type == "weekday") & (df.time_bucket == "am_peak")]
    assert len(row) == 1
    # S2 is served at 08:10 (T1/R1), 08:25 (T3/R2), 08:40 (T2/R1) -> 15 min average headway
    assert row.iloc[0]["avg_headway_min"] == 15.0
    assert row.iloc[0]["departure_count"] == 3
