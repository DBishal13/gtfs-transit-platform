from __future__ import annotations

from fastapi import APIRouter, Depends
from psycopg import Connection

from service.app.deps import get_db

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict:
    """Liveness probe: the process is up. Does not touch the database."""
    return {"status": "ok"}


@router.get("/readyz")
def readyz(conn: Connection = Depends(get_db)) -> dict:
    """Readiness probe: the process is up AND can reach the database."""
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
        cur.fetchone()
    return {"status": "ok", "database": "reachable"}
