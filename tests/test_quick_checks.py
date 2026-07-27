import copy

import pandas as pd

from pipeline.validate.quick_checks import run_quick_checks


def test_clean_feed_has_no_findings(mini_feed):
    findings = run_quick_checks(mini_feed)
    assert findings == []


def test_detects_missing_stop_reference(mini_feed):
    broken = copy.deepcopy(mini_feed)
    bad_row = broken.stop_times.iloc[[0]].copy()
    bad_row["stop_id"] = "DOES_NOT_EXIST"
    broken.stop_times = pd.concat([broken.stop_times, bad_row], ignore_index=True)

    findings = run_quick_checks(broken)
    checks = {f.check for f in findings}
    assert "stop_times_reference_valid_stops" in checks


def test_detects_duplicate_stop_ids(mini_feed):
    broken = copy.deepcopy(mini_feed)
    dup_row = broken.stops.iloc[[0]].copy()
    broken.stops = pd.concat([broken.stops, dup_row], ignore_index=True)

    findings = run_quick_checks(broken)
    checks = {f.check for f in findings}
    assert "duplicate_stop_ids" in checks


def test_detects_out_of_range_coordinates(mini_feed):
    broken = copy.deepcopy(mini_feed)
    broken.stops.loc[broken.stops.index[0], "stop_lat"] = 999.0

    findings = run_quick_checks(broken)
    checks = {f.check for f in findings}
    assert "stop_coordinates_sane" in checks
