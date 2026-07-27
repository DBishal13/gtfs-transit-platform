# Transit Data Platform

A generalized data-engineering and geospatial-analytics platform for GTFS
transit feeds — ingest any agency's schedule data, run real spatial and
service-quality analysis on it, and explore the results in an interactive map
app deployed straight from this repo to GitHub Pages. **Broward County
Transit** (Fort Lauderdale, FL) is the flagship dataset, not a hardcoded
assumption — see [`docs/adding-a-feed.md`](docs/adding-a-feed.md) to add
another agency.

**Live app:** https://dbishal13.github.io/gtfs-transit-platform/ *(after the
first successful `deploy.yml` run on `main`)*

This project started as a single-feed PostgreSQL/PostGIS/QGIS tutorial for
Broward County. That tutorial track still exists and still matters — see
[`docs/postgis-deep-dive.md`](docs/postgis-deep-dive.md) — but it's no longer
the whole story: everything below it is a from-scratch build that turns the
same idea into something that actually runs, scales to other agencies, and
ships as a real deployed product.

## Why this exists

Broward County, anchored by Fort Lauderdale, is one of Florida's most
populous and economically active counties. Efficient public transit is core
infrastructure there — it shapes congestion, access to jobs, and quality of
life — and the same is true for every other transit agency this platform can
ingest. Understanding *how frequent, how accessible, and how reliable a
transit network's schedule actually is* is the kind of question urban
planners, transit authorities, and riders all care about, and it's answerable
directly from the GTFS data agencies already publish.

## What it does

- **Ingests any GTFS schedule feed** — validated, typed, and turned into
  spatial data (`pipeline/ingest/`).
- **Runs real analytics** on the schedule (`pipeline/analytics/`):
  - Service frequency / headway by route, stop, day type, and time of day
  - Stop accessibility — walk-buffer coverage, weighted by US Census
    block-group population
  - Stop-spacing outlier detection and route-overlap/duplication heuristics
  - Service span (first/last trip, trip counts) per route
  - Cross-feed comparison once more than one agency is loaded
- **Validates data quality** (`pipeline/validate/`) — referential-integrity
  checks plus MobilityData's official `gtfs-validator`, merged into one report.
- **Exports scalable static assets** (`pipeline/export/`) — PMTiles for the
  map, small JSON for dashboards, Parquet for ad hoc browser-side SQL via
  duckdb-wasm — so the whole thing runs on GitHub Pages with zero servers.
- **Ships a real app** (`app/`) — React + TypeScript + MapLibre GL, deployed
  automatically by GitHub Actions on every push to `main`.

See [`docs/architecture.md`](docs/architecture.md) for how the pieces fit
together, and [`docs/analytics-methodology.md`](docs/analytics-methodology.md)
for exactly what each metric means (and its limitations — this is schedule
data, not realtime).

## Quick start

**Static pipeline + app (what's actually deployed):**

```bash
pip install -e ".[dev]"
python -m pipeline.cli all --feed broward-bct     # writes data/build/
pytest -q                                          # run the test suite

cd app
npm install
cp -r public/data-sample/* public/data/            # or point at data/build/ from above
npm run dev
```

**PostGIS deep-dive track** (local SQL/spatial exploration, not part of the
deployed app): see [`docs/postgis-deep-dive.md`](docs/postgis-deep-dive.md).

**Adding another agency's feed:** see
[`docs/adding-a-feed.md`](docs/adding-a-feed.md).

## Repository layout

```
pipeline/     Python ETL, validation, analytics, and static export
app/          React + Vite + TypeScript + MapLibre frontend
data/         feeds.yml registry + committed raw GTFS zips (generated output is gitignored)
docs/         architecture, data contract, methodology, onboarding guides
tests/        pytest suite against a small deterministic GTFS fixture
.github/      CI (tests + app build) and deploy (GitHub Pages) workflows
```

## Data quality note

This is real, live agency data — the Broward County Transit feed used here
passes every referential-integrity check the pipeline runs. That's not a
given: GTFS feeds vary widely in quality, which is exactly why the Data
Quality dashboard exists.

## License

MIT — see [`LICENSE`](LICENSE). GTFS data itself remains under each publishing
agency's own terms (see each feed's `license` field in `data/feeds.yml`).
