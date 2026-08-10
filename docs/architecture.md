# Architecture

## Why three tracks

GitHub Pages only serves static files — there's no server, no live database, at
runtime for the deployed app itself. But hands-on SQL/PostGIS work is a legitimate
and valuable part of this project's data-engineering story, and a real
natural-language agent with location queries needs a live database, auth, and
per-tenant isolation that a static site fundamentally cannot provide. So there
are three tracks that share the same GTFS ingestion code but serve different
purposes:

1. **Static export pipeline** (`pipeline/export/`, `pipeline/analytics/`) — runs
   in GitHub Actions on every deploy. Ingests each registered feed, validates it,
   computes analytics, and writes small static assets (JSON, GeoJSON, PMTiles,
   Parquet) that the deployed React app fetches over plain HTTP. This is the only
   path involved in what ends up live on Pages, and is completely unaffected by
   the other two tracks.
2. **PostGIS deep-dive track** (`pipeline/postgis/`, `docker-compose.yml`) — a
   local Postgres/PostGIS database (parameterized by `feed_id` so multiple
   agencies can coexist) for exploratory SQL and spatial analysis. Not used by CI
   or the deployed app. See `docs/postgis-deep-dive.md`.
3. **Backend service** (`service/`) — a hosted FastAPI application, built on top
   of the same PostGIS schema as track 2 (extended with spatial indexes,
   multi-tenancy, and agent-conversation tables), powering location/geo query
   endpoints and a constrained-tool-calling natural-language agent. This is the
   only track with authentication, per-tenant data isolation, and a live server;
   it's what the app's "Dispatch" console (`app/src/components/agent/`) talks to
   when `VITE_API_BASE_URL` is configured. See `service/README.md` for the full
   design (why the LLM never generates SQL, the provider-agnostic LLM layer,
   deployment) — deliberately not duplicated here.

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

## Data flow (backend service track)

```
data/raw/<feed_id>/gtfs.zip
        │
        ▼
pipeline.ingest.gtfs_loader.load_gtfs()   → same loader as tracks 1 and 2
        │
        ▼
pipeline.postgis.load.load_feed_to_postgis()   → hosted Postgres/PostGIS
        │        (service/migrations/*.sql adds GIST indexes, orgs/users/api_keys,
        │         agent_conversations/messages, api_usage_events on top of
        │         pipeline/postgis/schema.sql — see service/migrations/runner.py)
        ▼
service/app/  (FastAPI) — routers: health, auth, orgs, feeds, geo, agent
        │
        ▼ (JWT or API key)
app/src/components/agent/DispatchConsole.tsx  — only rendered when
        VITE_API_BASE_URL is set at build time (never set by deploy.yml)
```

## Frontend

React + Vite + TypeScript + MapLibre GL JS (`app/`). Fetches `data/manifest.json`
first to discover which feeds exist, then loads each feed's assets on demand per
page (map, frequency, coverage, quality, compare). See `docs/data-contract.md`
for the exact shapes.

## CI/CD

- **`.github/workflows/ci.yml`** — runs on every push/PR: pytest against the
  deterministic mini-GTFS fixture (`pipeline-tests`), the backend service's test
  suite against a real Postgres/PostGIS container (`service-tests`), and an app
  lint/typecheck/build using the committed sample data (`app-build`). All three
  jobs are independent — a failure in one doesn't affect the others.
- **`.github/workflows/deploy.yml`** — runs on push to `main`: builds real data
  for every feed in `data/feeds.yml` (installing Java + tippecanoe as needed),
  then builds and deploys the app to GitHub Pages. Generated assets are never
  committed — they exist only as CI artifacts and the final Pages build. Never
  sets `VITE_API_BASE_URL`, so the deployed static app never renders any
  backend-service-dependent UI.
- **`.github/workflows/deploy-service.yml`** — runs on pushes touching
  `service/`, `pipeline/`, `pyproject.toml`, or `fly.toml`: re-runs the backend
  test suite, then deploys to Fly.io — but only once a `FLY_API_TOKEN` repo
  secret exists; until then the deploy job is skipped (not failed). See
  "Deploying" in `service/README.md`.

## Why PMTiles, not raw GeoJSON

PMTiles (built with [tippecanoe](https://github.com/felt/tippecanoe)) is a
single-file vector tile archive that supports HTTP range requests, so a static
host like GitHub Pages can serve zoomed, simplified tiles without a tile server.
This is what lets the platform scale from Broward's ~4,800 stops to a much
larger agency's feed without the map becoming slow or the payload becoming huge.
Raw GeoJSON is kept as a fallback (used automatically when tippecanoe isn't
available, e.g. quick local iteration) and as a "download the raw data" option.
