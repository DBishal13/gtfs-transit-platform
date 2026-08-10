"""Tenant-isolation tests: an org must never be able to read another org's private feed,
whether via tenancy_service directly or through the /geo endpoints end-to-end. Skips
automatically if no database is reachable (see service/tests/conftest.py).
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from service.app.config import get_settings
from service.app.main import app
from service.app.services import auth_service, tenancy_service


def _make_org_with_owner(conn, *, org_name: str) -> tuple[uuid.UUID, uuid.UUID]:
    org_id = tenancy_service.create_org(conn, name=org_name, slug=f"{org_name}-{uuid.uuid4().hex[:8]}")
    user_id = tenancy_service.create_user(
        conn,
        org_id=org_id,
        email=f"{org_name}-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=auth_service.hash_password("test-password"),
        role="owner",
    )
    conn.commit()
    return org_id, user_id


def _make_feed_private_to(conn, *, feed_id: str, owner_org_id: uuid.UUID) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE feeds SET owner_org_id = %(org_id)s, is_public = false WHERE feed_id = %(feed_id)s",
            {"org_id": owner_org_id, "feed_id": feed_id},
        )
    conn.commit()


def _reset_feed_to_public(conn, *, feed_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE feeds SET owner_org_id = NULL, is_public = true WHERE feed_id = %(feed_id)s",
            {"feed_id": feed_id},
        )
    conn.commit()


def test_resolve_visible_feed_ids_excludes_other_orgs_private_feeds(db_conn, seeded_feed):
    org_a, _ = _make_org_with_owner(db_conn, org_name="org-a")
    org_b, _ = _make_org_with_owner(db_conn, org_name="org-b")
    _make_feed_private_to(db_conn, feed_id=seeded_feed, owner_org_id=org_b)

    try:
        assert seeded_feed not in tenancy_service.resolve_visible_feed_ids(db_conn, org_id=org_a)
        assert seeded_feed in tenancy_service.resolve_visible_feed_ids(db_conn, org_id=org_b)
    finally:
        _reset_feed_to_public(db_conn, feed_id=seeded_feed)


def test_feed_grant_restores_access_without_ownership(db_conn, seeded_feed):
    org_a, _ = _make_org_with_owner(db_conn, org_name="org-c")
    org_b, _ = _make_org_with_owner(db_conn, org_name="org-d")
    _make_feed_private_to(db_conn, feed_id=seeded_feed, owner_org_id=org_b)

    try:
        assert seeded_feed not in tenancy_service.resolve_visible_feed_ids(db_conn, org_id=org_a)
        with db_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO feed_grants (org_id, feed_id) VALUES (%(org_id)s, %(feed_id)s)",
                {"org_id": org_a, "feed_id": seeded_feed},
            )
        db_conn.commit()
        assert seeded_feed in tenancy_service.resolve_visible_feed_ids(db_conn, org_id=org_a)
    finally:
        with db_conn.cursor() as cur:
            cur.execute(
                "DELETE FROM feed_grants WHERE org_id = %(org_id)s AND feed_id = %(feed_id)s",
                {"org_id": org_a, "feed_id": seeded_feed},
            )
        db_conn.commit()
        _reset_feed_to_public(db_conn, feed_id=seeded_feed)


def test_geo_endpoint_rejects_org_without_feed_access(db_conn, seeded_feed):
    org_a, user_a = _make_org_with_owner(db_conn, org_name="org-e")
    org_b, _ = _make_org_with_owner(db_conn, org_name="org-f")
    _make_feed_private_to(db_conn, feed_id=seeded_feed, owner_org_id=org_b)

    settings = get_settings()
    token = auth_service.issue_access_token(
        user_id=user_a, org_id=org_a, secret=settings.jwt_secret_key, minutes=15
    )

    try:
        client = TestClient(app)
        response = client.get(
            "/geo/nearest-stops",
            params={"feed_id": seeded_feed, "lon": -80.2, "lat": 26.0, "limit": 5},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
    finally:
        _reset_feed_to_public(db_conn, feed_id=seeded_feed)


def test_geo_endpoint_allows_org_with_feed_access(db_conn, seeded_feed):
    org_b, user_b = _make_org_with_owner(db_conn, org_name="org-g")
    _make_feed_private_to(db_conn, feed_id=seeded_feed, owner_org_id=org_b)

    settings = get_settings()
    token = auth_service.issue_access_token(
        user_id=user_b, org_id=org_b, secret=settings.jwt_secret_key, minutes=15
    )

    try:
        client = TestClient(app)
        response = client.get(
            "/geo/nearest-stops",
            params={"feed_id": seeded_feed, "lon": -80.2, "lat": 26.0, "limit": 5},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["stops"][0]["stop_id"] == "S1"
    finally:
        _reset_feed_to_public(db_conn, feed_id=seeded_feed)


def test_geo_endpoint_requires_auth(pg_dsn):
    client = TestClient(app)
    response = client.get(
        "/geo/nearest-stops", params={"feed_id": "mini-test", "lon": -80.2, "lat": 26.0}
    )
    assert response.status_code == 401
