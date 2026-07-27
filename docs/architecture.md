# Architecture

## Why two pipelines

GitHub Pages only serves static files — there's no server, no live database, at
runtime. But hands-on SQL/PostGIS work is a legitimate and valuable part of this
project's data-engineering story. So there are two tracks that share the same
GTFS ingestion code but serve different purposes:

1. **Static export pipeline** (`pipeline/export/`, `pipeline/analytics/`) — runs
   in GitHub Actions on every deploy. Ingests each registered feed, validates it,
   computes analytics, and writes small static assets (JSON, GeoJSON, PMTiles,
   Parquet) that the deployed React app fetches over plain HTTP. This is the only
   path involved in what ends up live on Pages.
2. **PostGIS deep-dive track** (`pipeline/postgis/`, `docker-compose.yml`) — a
   local Postgres/PostGIS database (parameterized by `feed_id` so multiple
   agencies can coexist) for exploratory SQL and spatial analysis. Not used by CI
   or the deployed app. See `docs/postgis-deep-dive.md`.

## Data flow (static export track)

```
data/raw/<feed_id>/gtfs.zip
        │
        ▼
pipeline.ingest.gtfs_loader.load_gtfs()   → typed pandas/geopandas frames
        │
        ├─→ pipeline.validate  → quick_checks.py (always) + gtfs-validator (Java, if available)
        │                        → quality.json
        │
        ├─→ pipeline.analytics → headway.py, coverage.py, spacing.py,
        │                        duplication.py, schedule_span.py, comparison.py
        │                        → headway.json, coverage.json, spacing.json, …
        │
        └─→ pipeline.export    → tiles.py (GeoJSON → tippecanoe → PMTiles)
                                 → metrics_export.py (JSON)
                                 → parquet_export.py (stop_times.parquet)
                                 → manifest.py (manifest.json — the app's entry point)
        │
        ▼
data/build/manifest.json + data/build/<feed_id>/*
        │
        ▼ (GitHub Actions artifact, not committed to git)
app/public/data/  →  npm run build  →  GitHub Pages
```

## Frontend

React + Vite + TypeScript + MapLibre GL JS (`app/`). Fetches `data/manifest.json`
first to discover which feeds exist, then loads each feed's assets on demand per
page (map, frequency, coverage, quality, compare). See `docs/data-contract.md`
for the exact shapes.

## CI/CD

- **`.github/workflows/ci.yml`** — runs on every push/PR: pytest against the
  deterministic mini-GTFS fixture, plus an app lint/typecheck/build using the
  committed sample data (`app/public/data-sample/`).
- **`.github/workflows/deploy.yml`** — runs on push to `main`: builds real data
  for every feed in `data/feeds.yml` (installing Java + tippecanoe as needed),
  then builds and deploys the app to GitHub Pages. Generated assets are never
  committed — they exist only as CI artifacts and the final Pages build.

## Why PMTiles, not raw GeoJSON

PMTiles (built with [tippecanoe](https://github.com/felt/tippecanoe)) is a
single-file vector tile archive that supports HTTP range requests, so a static
host like GitHub Pages can serve zoomed, simplified tiles without a tile server.
This is what lets the platform scale from Broward's ~4,800 stops to a much
larger agency's feed without the map becoming slow or the payload becoming huge.
Raw GeoJSON is kept as a fallback (used automatically when tippecanoe isn't
available, e.g. quick local iteration) and as a "download the raw data" option.
