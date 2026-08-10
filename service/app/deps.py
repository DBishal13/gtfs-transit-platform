"""Shared FastAPI dependencies.

Auth-related dependencies (get_current_org, require_role) are added in Phase 2 once the
orgs/users/api_keys tables exist; for now every router only depends on a pooled DB
connection and endpoints are unauthenticated (Phase 1 explicitly ships without auth —
see the plan's phased milestones).
"""

from __future__ import annotations

from collections.abc import Iterator

from psycopg import Connection

from service.app.db import get_pool


def get_db() -> Iterator[Connection]:
    with get_pool().connection() as conn:
        yield conn
