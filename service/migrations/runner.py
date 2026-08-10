"""Minimal, idempotent SQL migration runner for the backend service's database.

Deliberately not Alembic: the rest of this repo's Postgres access
(pipeline/postgis/load.py, pipeline/postgis/schema.sql) is raw, hand-written SQL, and this
runner matches that idiom rather than introducing a second, SQLAlchemy-flavored query
layer. It does two things:

  1. Applies pipeline/postgis/schema.sql (the shared GTFS DDL foundation, tracked as if it
     were the first migration) if not already applied.
  2. Applies every service/migrations/*.sql file, in filename order, that isn't yet
     recorded in the schema_migrations tracking table.

Usage:
    python -m service.migrations.runner
    python -m service.migrations.runner --dsn postgresql://...
"""

from __future__ import annotations

import os
from pathlib import Path

import psycopg
import typer

from pipeline.config import REPO_ROOT
from pipeline.utils.logging import get_logger

log = get_logger(__name__)
app = typer.Typer(add_completion=False)

MIGRATIONS_DIR = Path(__file__).resolve().parent
BASE_SCHEMA = REPO_ROOT / "pipeline" / "postgis" / "schema.sql"
DEFAULT_DSN = "postgresql://transit:transit@localhost:5432/transit"

_TRACKING_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
  filename text PRIMARY KEY,
  applied_at timestamptz NOT NULL DEFAULT now()
);
"""


def _applied(cur: psycopg.Cursor) -> set[str]:
    cur.execute("SELECT filename FROM schema_migrations")
    return {row[0] for row in cur.fetchall()}


def _apply(conn: psycopg.Connection, name: str, sql: str) -> None:
    log.info("Applying migration: %s", name)
    with conn.cursor() as cur:
        cur.execute(sql)
        cur.execute(
            "INSERT INTO schema_migrations (filename) VALUES (%s) ON CONFLICT DO NOTHING",
            (name,),
        )
    conn.commit()


def run_migrations(dsn: str) -> None:
    with psycopg.connect(dsn, autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS postgis")
            cur.execute(_TRACKING_TABLE_SQL)
        conn.commit()

        with conn.cursor() as cur:
            already = _applied(cur)
        if BASE_SCHEMA.name not in already:
            _apply(conn, BASE_SCHEMA.name, BASE_SCHEMA.read_text(encoding="utf-8"))

        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            with conn.cursor() as cur:
                already = _applied(cur)
            if path.name in already:
                continue
            _apply(conn, path.name, path.read_text(encoding="utf-8"))

    log.info("Migrations up to date.")


@app.command()
def migrate(dsn: str = typer.Option(None, help="Postgres DSN; defaults to $DATABASE_URL")) -> None:
    run_migrations(dsn or os.environ.get("DATABASE_URL", DEFAULT_DSN))


if __name__ == "__main__":
    app()
