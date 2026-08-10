"""Test fixtures for the backend service.

Tests that need a real Postgres/PostGIS database SKIP (never fail) when one isn't
reachable, so `pytest service/tests` degrades gracefully in environments without
`docker compose up` while still running for real in CI's `service-tests` job and in
local dev. This intentionally does not live under the top-level tests/ package (whose
testpaths-driven `pytest -q` run in CI's pipeline-tests job never installs the `service`
extra) — run these explicitly via `pytest service/tests -q`.

Seeds the same deterministic tests/fixtures/mini_gtfs feed the pipeline test suite uses,
via pipeline.ingest.gtfs_loader.load_gtfs + pipeline.postgis.load.load_feed_to_postgis,
rather than inventing a second fixture feed.
"""

from __future__ import annotations

import os
import zipfile
from pathlib import Path

import psycopg
import pytest

from pipeline.config import REPO_ROOT, FeedConfig
from pipeline.ingest.gtfs_loader import load_gtfs
from pipeline.postgis.load import load_feed_to_postgis
from service.migrations.runner import run_migrations

TEST_DSN = os.environ.get("TEST_DATABASE_URL", "postgresql://transit:transit@localhost:5432/transit")
TEST_FEED_ID = "mini-test"
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "mini_gtfs"


def _db_reachable(dsn: str) -> bool:
    try:
        with psycopg.connect(dsn, connect_timeout=2):
            return True
    except psycopg.OperationalError:
        return False


@pytest.fixture(scope="session")
def pg_dsn() -> str:
    if not _db_reachable(TEST_DSN):
        pytest.skip(
            f"No reachable Postgres at {TEST_DSN} — run `docker compose up` "
            "to enable service backend DB tests"
        )
    run_migrations(TEST_DSN)
    return TEST_DSN


@pytest.fixture(scope="session")
def mini_gtfs_zip(tmp_path_factory) -> Path:
    zip_path = tmp_path_factory.mktemp("gtfs") / "mini_gtfs.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for txt_file in FIXTURE_DIR.glob("*.txt"):
            zf.write(txt_file, arcname=txt_file.name)
    return zip_path


@pytest.fixture(scope="session")
def seeded_feed(pg_dsn: str, mini_gtfs_zip: Path) -> str:
    feed = load_gtfs(mini_gtfs_zip, feed_id=TEST_FEED_ID)
    feed_config = FeedConfig(
        id=TEST_FEED_ID,
        name="Mini Test Feed",
        region="Testland",
        agency_timezone="America/New_York",
        source_url="https://example.com/gtfs.zip",
        license="Public Domain",
        raw_path=mini_gtfs_zip,
        census=None,
    )
    load_feed_to_postgis(feed_config, feed, pg_dsn)
    return TEST_FEED_ID


@pytest.fixture()
def db_conn(pg_dsn: str):
    with psycopg.connect(pg_dsn) as conn:
        yield conn
