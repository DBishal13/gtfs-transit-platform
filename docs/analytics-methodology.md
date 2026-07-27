# Analytics methodology & limitations

All analytics run against **static GTFS schedules** (`pipeline/analytics/`).
There is no GTFS-realtime input, so every metric here is "what the timetable
says should happen," not observed vehicle behavior. That's an honest
limitation worth stating plainly rather than implying more than the data
supports.

## Service frequency / headway (`headway.py`)

Headway = average minutes between consecutive scheduled departures, bucketed
by route (or stop) × day type × time-of-day. Day type is derived from
`calendar.txt`'s weekly pattern (any weekday flag → "weekday", `saturday` /
`sunday` flags independently) — `calendar_dates.txt` single-date exceptions
are **not** resolved to specific calendar dates, since a "typical Tuesday"
frequency answer doesn't need date-level exception handling. Time-of-day
buckets: `early_am` (4–6), `am_peak` (6–9), `midday` (9–15), `pm_peak` (15–19),
`evening` (19–22), `night` (22–4, wraps past midnight). GTFS times past
`24:00:00` (post-midnight trips) are parsed as seconds-since-midnight without
capping, then reduced mod 86400 only for bucketing (`pipeline/utils/time.py`).

## Stop accessibility / coverage (`coverage.py`)

Dissolved walk-buffer polygons at 400m (~5 min) and 800m (~10 min) around all
stops, built in a local UTM projection for accurate meter-based buffering.
Population weighting apportions each US Census block group's population to a
buffer in proportion to the **share of the block group's area** the buffer
covers — a standard areal-weighting approximation, not parcel-level accuracy.
Requires a free Census API key (`CENSUS_API_KEY`); without one, buffer
geometry is still computed and returned, just without population numbers.

## Stop spacing (`spacing.py`)

Flags consecutive-stop gaps (by route) that are statistical outliers (median +
6×MAD, with a 3km floor) — usually a data error (wrong sequence, missing
intermediate stops) rather than a genuine express segment, though it can be
either; the dashboard surfaces it for a human to judge.

## Route duplication (`duplication.py`)

Jaccard similarity of each route pair's served-stop sets. High overlap
(≥0.6) flags candidates for consolidation review — it does not account for
directionality, express/local pairing intent, or ridership, so it's a
starting point for investigation, not a recommendation to merge routes.

## Schedule span (`schedule_span.py`)

First/last scheduled time and trip count per route × day type — the honest
proxy for "how much service" a static feed can support, given there's no
realtime adherence data to check against the schedule.

## Data quality (`validate/`)

Two layers, merged into one `quality.json`:
- **Custom checks** (`quick_checks.py`) — referential integrity (trips → routes
  /services/shapes, stop_times → trips/stops), duplicate stop ids, coordinate
  sanity. Always runs, no external dependency.
- **Official validator** (`run_gtfs_validator.py`) — MobilityData's
  [gtfs-validator](https://github.com/MobilityData/gtfs-validator) (Java CLI),
  the canonical spec-conformance tool. Skipped automatically (with a logged
  warning, not a failure) if Java/the jar aren't available; CI always installs
  both.

## Cross-feed comparison (`comparison.py`)

Pure aggregation of the outputs above into one KPI row per feed — does no GTFS
parsing itself, so its accuracy is only as good as the per-feed analytics it
rolls up.
