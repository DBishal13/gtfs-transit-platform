def test_load_gtfs_counts(mini_feed):
    assert len(mini_feed.routes) == 2
    assert len(mini_feed.trips) == 3
    assert len(mini_feed.stops) == 4
    assert len(mini_feed.stop_times) == 8
    assert len(mini_feed.shape_geoms) == 2


def test_stop_ids_stay_strings(mini_feed):
    # Regression guard: numeric-looking ids (e.g. "0003") must not be coerced to int/float.
    assert mini_feed.stops["stop_id"].dtype == "string"


def test_shape_geometries_are_linestrings(mini_feed):
    from shapely.geometry import LineString

    for geom in mini_feed.shape_geoms.geometry:
        assert isinstance(geom, LineString)
