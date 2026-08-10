"""Org/user/API-key persistence and feed-visibility resolution.

resolve_visible_feed_ids is THE tenant-isolation boundary: every geo/agent query must
check its requested feed_id against this set before running (enforced in
service/app/routers/geo.py, and from Phase 4, service/app/services/agent/tools.py). It is
layered on top of — not a replacement for — the existing feed_id-scoping convention
already used throughout pipeline/postgis/schema.sql.
"""

from __future__ import annotations

import uuid

import psycopg


def resolve_visible_feed_ids(conn: psycopg.Connection, *, org_id: uuid.UUID) -> set[str]:
    """Feeds `org_id` may query: publicly-visible feeds, feeds it owns, and feeds
    explicitly granted to it."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT feed_id FROM feeds WHERE is_public = true
            UNION
            SELECT feed_id FROM feeds WHERE owner_org_id = %(org_id)s
            UNION
            SELECT feed_id FROM feed_grants WHERE org_id = %(org_id)s
            """,
            {"org_id": org_id},
        )
        return {row[0] for row in cur.fetchall()}


def create_org(conn: psycopg.Connection, *, name: str, slug: str) -> uuid.UUID:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO orgs (name, slug) VALUES (%(name)s, %(slug)s) RETURNING org_id",
            {"name": name, "slug": slug},
        )
        return cur.fetchone()[0]


def get_org(conn: psycopg.Connection, *, org_id: uuid.UUID) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT org_id, name, slug, plan FROM orgs WHERE org_id = %(org_id)s",
            {"org_id": org_id},
        )
        row = cur.fetchone()
        if row is None:
            return None
        columns = [d.name for d in cur.description]
        return dict(zip(columns, row))


def create_user(
    conn: psycopg.Connection,
    *,
    org_id: uuid.UUID,
    email: str,
    password_hash: str,
    role: str = "owner",
) -> uuid.UUID:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (org_id, email, password_hash, role)
            VALUES (%(org_id)s, %(email)s, %(password_hash)s, %(role)s)
            RETURNING user_id
            """,
            {"org_id": org_id, "email": email, "password_hash": password_hash, "role": role},
        )
        return cur.fetchone()[0]


def get_user_by_email(conn: psycopg.Connection, *, email: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT user_id, org_id, email, password_hash, role FROM users WHERE email = %(email)s",
            {"email": email},
        )
        row = cur.fetchone()
        if row is None:
            return None
        columns = [d.name for d in cur.description]
        return dict(zip(columns, row))


def list_org_users(conn: psycopg.Connection, *, org_id: uuid.UUID) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT user_id, email, role FROM users WHERE org_id = %(org_id)s ORDER BY created_at",
            {"org_id": org_id},
        )
        columns = [d.name for d in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]


def touch_last_login(conn: psycopg.Connection, *, user_id: uuid.UUID) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE users SET last_login_at = now() WHERE user_id = %(user_id)s",
            {"user_id": user_id},
        )


def create_api_key(
    conn: psycopg.Connection,
    *,
    org_id: uuid.UUID,
    name: str,
    key_prefix: str,
    key_hash: str,
    created_by: uuid.UUID | None,
) -> uuid.UUID:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO api_keys (org_id, name, key_prefix, key_hash, created_by)
            VALUES (%(org_id)s, %(name)s, %(key_prefix)s, %(key_hash)s, %(created_by)s)
            RETURNING api_key_id
            """,
            {
                "org_id": org_id,
                "name": name,
                "key_prefix": key_prefix,
                "key_hash": key_hash,
                "created_by": created_by,
            },
        )
        return cur.fetchone()[0]


def get_org_id_for_active_api_key(conn: psycopg.Connection, *, key_hash: str) -> uuid.UUID | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT org_id FROM api_keys WHERE key_hash = %(key_hash)s AND revoked_at IS NULL",
            {"key_hash": key_hash},
        )
        row = cur.fetchone()
        return row[0] if row else None


def touch_api_key_last_used(conn: psycopg.Connection, *, key_hash: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE api_keys SET last_used_at = now() WHERE key_hash = %(key_hash)s",
            {"key_hash": key_hash},
        )


def revoke_api_key(conn: psycopg.Connection, *, org_id: uuid.UUID, api_key_id: uuid.UUID) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE api_keys SET revoked_at = now()
            WHERE api_key_id = %(api_key_id)s AND org_id = %(org_id)s AND revoked_at IS NULL
            """,
            {"api_key_id": api_key_id, "org_id": org_id},
        )
        return cur.rowcount > 0
