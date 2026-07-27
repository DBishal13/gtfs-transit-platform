# Data contract

The static export pipeline and the React app share no runtime, so this document
(plus `pipeline/export/schema/manifest.schema.json` and
`app/src/types/dataContract.ts`) is the source of truth both sides are kept in
sync against manually. `tests/test_manifest_contract.py` validates generated
manifests against the JSON Schema on every CI run.

## `manifest.json`

The first file the app fetches. Lists every feed and where its assets live.

| Field | Type | Notes |
|---|---|---|
| `schema_version` | int | Bump on breaking changes to this contract |
| `generated_at` | ISO datetime | |
| `feeds[].id` | string | Matches `data/feeds.yml` and the build output directory name |
| `feeds[].bbox` | `[minLon, minLat, maxLon, maxLat]` | Used to fit the map on load |
| `feeds[].counts` | `{routes, stops, trips}` | |
| `feeds[].assets` | see below | All paths are relative to the site root |

## Per-feed assets (under `data/<feed_id>/`)

| Asset | File | Produced by |
|---|---|---|
| Vector tiles | `transit.pmtiles` (nullable) | `pipeline/export/tiles.py` — null if tippecanoe wasn't available at build time |
| Raw routes/stops | `routes.geojson`, `stops.geojson` | Always present; the app's fallback when `tiles` is null |
| Route list | `routes_summary.json` | `pipeline/export/metrics_export.py` |
| Frequency | `headway.json` — `{by_route: [...], by_stop: [...]}` | `pipeline/analytics/headway.py` |
| Coverage | `coverage.json` — buffer polygons + optional population stats | `pipeline/analytics/coverage.py` |
| Data quality | `quality.json` | `pipeline/validate/report.py` |
| Stop spacing | `spacing.json` | `pipeline/analytics/spacing.py` |
| Route overlap | `duplication.json` | `pipeline/analytics/duplication.py` |
| Service span | `schedule_span.json` | `pipeline/analytics/schedule_span.py` |
| Ad hoc queries | `stop_times.parquet` | `pipeline/export/parquet_export.py`, queried client-side via duckdb-wasm |

## `comparison.json` (build root, not per-feed)

Cross-feed KPI rollup consumed by the Compare page. Produced by
`pipeline/analytics/comparison.py` from the per-feed outputs above — it does no
GTFS parsing of its own.

## Changing the contract

1. Update the Python side that writes the field (`pipeline/export/` or
   `pipeline/analytics/`).
2. Update `pipeline/export/schema/manifest.schema.json` if it's part of the
   manifest itself.
3. Update `app/src/types/dataContract.ts` to match.
4. Run `pytest` — `tests/test_manifest_contract.py` will catch a manifest that
   no longer matches its own schema.
