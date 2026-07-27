from pipeline.utils.time import bucket_for_seconds, gtfs_time_to_seconds


def test_gtfs_time_to_seconds_basic():
    assert gtfs_time_to_seconds("08:00:00") == 8 * 3600
    assert gtfs_time_to_seconds("00:00:00") == 0


def test_gtfs_time_to_seconds_past_midnight():
    # GTFS allows hours >= 24 for trips that run past midnight
    assert gtfs_time_to_seconds("25:10:00") == 25 * 3600 + 10 * 60


def test_gtfs_time_to_seconds_empty():
    assert gtfs_time_to_seconds("") is None
    assert gtfs_time_to_seconds(None) is None


def test_bucket_for_seconds_wraps_past_midnight():
    # 25:10:00 -> wall clock 01:10:00 -> "night" bucket
    assert bucket_for_seconds(25 * 3600 + 10 * 60) == "night"


def test_bucket_for_seconds_am_peak():
    assert bucket_for_seconds(8 * 3600) == "am_peak"
