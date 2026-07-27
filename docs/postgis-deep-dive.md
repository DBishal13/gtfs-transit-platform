# PostGIS deep-dive track

This is the hands-on SQL/spatial-analysis path this project started as — kept
and expanded, but decoupled from the deployed app (GitHub Pages can't run a
database). Useful for learning PostGIS, writing ad hoc spatial queries, or
connecting QGIS directly to real transit data.

## Setup

```bash
docker compose up -d          # starts Postgres 16 + PostGIS 3.4, applies pipeline/postgis/schema.sql
pip install -e ".[postgis]"   # adds psycopg for the loader
python -m pipeline.postgis.load --feed broward-bct
```

The schema is **feed-parameterized**: every table carries a `feed_id` column,
so you can load Broward County Transit and any other registered feed side by
side without id collisions, and compare them with plain SQL joins.

## What gets created

- Raw GTFS tables: `agency`, `routes`, `trips`, `stops`, `stop_times`,
  `calendar`, `calendar_dates`, `shapes` — one row set per `feed_id`.
- `shape_geoms` — one `LINESTRING(4326)` per `(feed_id, shape_id)`, built with
  `ST_MakeLine`/`ST_SetSRID` over the ordered points in `shapes`.
- `stops.stop_geom` — a `POINT(4326)` per stop.
- Views `stops_view` and `shape_geoms_view` — convenient QGIS connection
  targets (Layer → Add Layer → Add PostGIS Layer, connect to `localhost:5432`,
  db `transit`, user/password `transit`).

## Example queries

Routes with the most stops:

```sql
SELECT feed_id, route_id, route_short_name, count(*) AS stop_count
FROM stop_times st
JOIN trips t USING (feed_id, trip_id)
JOIN routes r USING (feed_id, route_id)
GROUP BY feed_id, r.route_id, route_short_name
ORDER BY stop_count DESC
LIMIT 10;
```

Stops within 400m of a point (e.g. a proposed development site):

```sql
SELECT stop_id, stop_name
FROM stops
WHERE feed_id = 'broward-bct'
  AND ST_DWithin(stop_geom::geography, ST_MakePoint(-80.14, 26.12)::geography, 400);
```

Total route-shape length per feed:

```sql
SELECT feed_id, sum(ST_Length(shape_geom::geography)) / 1609.34 AS total_miles
FROM shape_geoms
GROUP BY feed_id;
```

This track intentionally duplicates some of what `pipeline/analytics/` computes
in Python — that's fine. Doing the same analysis in SQL and in pandas/geopandas
is a good way to sanity-check both and to learn the tradeoffs of each approach.
