"""Loads a GTFS feed's raw tables into the local Postgres/PostGIS "deep-dive"
track (docker-compose). This is a separate, optional path from the main
static-export pipeline — it requires `pip install -e ".[postgis]"` and a
running `docker compose up` database. Not used by CI/the deployed app.

Usage:
    python -m pipeline.postgis.load --feed broward-bct
"""

from __future__ import annotations

import os

import typer

from pipeline.config import FeedConfig, get_feed
from pipeline.ingest.gtfs_loader import GTFSFeed, load_gtfs
from pipeline.utils.logging import get_logger

log = get_logger(__name__)
app = typer.Typer(add_completion=False)

DEFAULT_DSN = "postgresql://transit:transit@localhost:5432/transit"

TABLE_COLUMNS = {
    "agency": ["agency_id", "agency_name", "agency_url", "agency_timezone", "agency_lang", "agency_phone"],
    "routes": [
        "route_id", "route_short_name", "route_long_name", "route_desc",
        "route_type", "route_url", "route_color", "route_text_color",
    ],
    "calendar": [
        "service_id", "monday", "tuesday", "wednesday", "thursday",
        "friday", "saturday", "sunday", "start_date", "end_date",
    ],
    "calendar_dates": ["service_id", "date", "exception_type"],
    "shapes": ["shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence"],
    "stops": [
        "stop_id", "stop_code", "stop_name", "stop_desc", "stop_lat", "stop_lon",
        "zone_id", "stop_url", "location_type", "parent_station", "wheelchair_boarding",
    ],
    "trips": ["route_id", "service_id", "trip_id", "trip_headsign", "direction_id", "block_id", "shape_id"],
    "stop_times": [
        "trip_id", "arrival_time", "departure_time", "stop_id",
        "stop_sequence", "pickup_type", "drop_off_type", "shape_dist_traveled",
    ],
}


def _copy_table(cursor, table: str, feed_id: str, df) -> None:
    columns = [c for c in TABLE_COLUMNS[table] if c in df.columns]
    if not columns:
        return
    subset = df[columns].where(df[columns].notna(), None)
    col_list = ", ".join(["feed_id"] + columns)
    with cursor.copy(f"COPY {table} ({col_list}) FROM STDIN") as copy:
        for row in subset.itertuples(index=False, name=None):
            copy.write_row((feed_id, *row))
    log.info("Loaded %d rows into %s for feed '%s'", len(subset), table, feed_id)


def _build_geometries(cursor, feed_id: str) -> None:
    """Python equivalent of geometries.sql, parameterized safely per-feed.
    geometries.sql itself is kept as the reference/manual-`psql` version."""
    cursor.execute(
        """
        INSERT INTO shape_geoms (feed_id, shape_id, shape_geom)
        SELECT
          feed_id, shape_id,
          ST_MakeLine(ST_SetSRID(ST_MakePoint(shape_pt_lon, shape_pt_lat), 4326) ORDER BY shape_pt_sequence)
        FROM shapes
        WHERE feed_id = %s
        GROUP BY feed_id, shape_id
        ON CONFLICT (feed_id, shape_id) DO UPDATE SET shape_geom = EXCLUDED.shape_geom
        """,
        (feed_id,),
    )
    cursor.execute(
        """
        UPDATE stops
        SET stop_geom = ST_SetSRID(ST_MakePoint(stop_lon, stop_lat), 4326)
        WHERE feed_id = %s AND stop_lon IS NOT NULL AND stop_lat IS NOT NULL
        """,
        (feed_id,),
    )
    cursor.execute(
        """
        CREATE OR REPLACE VIEW stops_view AS
        SELECT feed_id, stop_id, stop_name, stop_code, wheelchair_boarding, stop_geom
        FROM stops WHERE stop_geom IS NOT NULL
        """
    )
    cursor.execute(
        """
        CREATE OR REPLACE VIEW shape_geoms_view AS
        SELECT sg.feed_id, sg.shape_id, r.route_id, r.route_short_name, r.route_long_name, sg.shape_geom
        FROM shape_geoms sg
        JOIN trips t ON t.feed_id = sg.feed_id AND t.shape_id = sg.shape_id
        JOIN routes r ON r.feed_id = t.feed_id AND r.route_id = t.route_id
        GROUP BY sg.feed_id, sg.shape_id, r.route_id, r.route_short_name, r.route_long_name, sg.shape_geom
        """
    )


def load_feed_to_postgis(feed_config: FeedConfig, feed: GTFSFeed, dsn: str) -> None:
    import psycopg

    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO feeds (feed_id, name, region, source_url, license)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (feed_id) DO UPDATE
                    SET name = EXCLUDED.name, region = EXCLUDED.region,
                        source_url = EXCLUDED.source_url, license = EXCLUDED.license
                """,
                (feed_config.id, feed_config.name, feed_config.region, feed_config.source_url, feed_config.license),
            )
            # Clear any previous load for this feed_id so re-runs are idempotent.
            for table in ["stop_times", "trips", "stops", "shapes", "calendar_dates", "calendar", "routes", "agency"]:
                cur.execute(f"DELETE FROM {table} WHERE feed_id = %s", (feed_config.id,))

            _copy_table(cur, "agency", feed_config.id, feed.agency)
            _copy_table(cur, "routes", feed_config.id, feed.routes)
            _copy_table(cur, "calendar", feed_config.id, feed.calendar)
            _copy_table(cur, "calendar_dates", feed_config.id, feed.calendar_dates)
            _copy_table(cur, "shapes", feed_config.id, feed.shapes)
            _copy_table(cur, "stops", feed_config.id, feed.stops.drop(columns="geometry"))
            _copy_table(cur, "trips", feed_config.id, feed.trips)
            _copy_table(cur, "stop_times", feed_config.id, feed.stop_times)

            _build_geometries(cur, feed_config.id)

    log.info("Feed '%s' loaded into PostGIS and geometries built.", feed_config.id)


@app.command()
def load(feed: str, dsn: str = typer.Option(None)) -> None:
    feed_config = get_feed(feed)
    gtfs_feed = load_gtfs(feed_config.raw_path, feed_config.id)
    load_feed_to_postgis(feed_config, gtfs_feed, dsn or os.environ.get("TRANSIT_DSN", DEFAULT_DSN))


if __name__ == "__main__":
    app()
