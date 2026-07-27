from pipeline.analytics.duplication import compute_route_duplication
from pipeline.analytics.spacing import compute_stop_spacing


def test_stop_spacing_pairs(mini_feed):
    df = compute_stop_spacing(mini_feed)
    pairs = set(zip(df.route_id, df.from_stop_id, df.to_stop_id))
    assert ("R1", "S1", "S2") in pairs
    assert ("R1", "S2", "S3") in pairs
    assert ("R2", "S4", "S2") in pairs
    assert (df["gap_m"] > 0).all()
    # Stops in the fixture are all ~1-1.5km apart, well under the outlier threshold
    assert not df["is_outlier"].any()


def test_route_duplication_jaccard(mini_feed):
    df = compute_route_duplication(mini_feed)
    row = df[(df.route_a == "R1") & (df.route_b == "R2")]
    assert len(row) == 1
    assert row.iloc[0]["shared_stops"] == 1  # only S2 is shared
    assert row.iloc[0]["jaccard"] == 0.25
    assert not row.iloc[0]["high_overlap"]
