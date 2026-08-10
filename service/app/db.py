"""Postgres connection pooling for the backend service.

Follows the same raw-psycopg3 style already established in pipeline/postgis/load.py —
no ORM. A single process-wide pool is lazily created from Settings.database_url and
reused across requests via the get_db FastAPI dependency in service/app/deps.py.
"""

from __future__ import annotations

from psycopg_pool import ConnectionPool

from service.app.config import get_settings

_pool: ConnectionPool | None = None


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(get_settings().database_url, min_size=1, max_size=10, open=True)
    return _pool


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
