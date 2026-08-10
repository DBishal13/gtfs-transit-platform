"""End-to-end tests for the /geo/geocode and /geo/reachability endpoints. Skips
automatically if no database is reachable (see service/tests/conftest.py).
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from service.app.config import get_settings
from service.app.main import app
from service.app.services import auth_service, geocoding_service, tenancy_service


def _client() -> TestClient:
    return TestClient(app)


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


def _auth_header(org_id: uuid.UUID, user_id: uuid.UUID) -> dict:
    settings = get_settings()
    token = auth_service.issue_access_token(
        user_id=user_id, org_id=org_id, secret=settings.jwt_secret_key, minutes=15
    )
    return {"Authorization": f"Bearer {token}"}


def test_reachability_requires_auth(pg_dsn, seeded_feed):
    response = _client().post(
        "/geo/reachability",
        params={"feed_id": seeded_feed},
        json={"lon": -80.2, "lat": 26.0, "minutes": 15},
    )
    assert response.status_code == 401


def test_reachability_end_to_end(db_conn, seeded_feed):
    org_id, user_id = _make_org_with_owner(db_conn, org_name="geo-router")
    response = _client().post(
        "/geo/reachability",
        params={"feed_id": seeded_feed},
        json={"lon": -80.2, "lat": 26.0, "minutes": 15},
        headers=_auth_header(org_id, user_id),
    )
    assert response.status_code == 200
    body = response.json()
    assert {s["stop_id"] for s in body["walk_only_stops"]} == {"S1", "S4"}
    assert {s["stop_id"] for s in body["one_hop_stops"]} == {"S2"}


def test_reachability_minutes_above_cap_is_rejected(db_conn, seeded_feed):
    org_id, user_id = _make_org_with_owner(db_conn, org_name="geo-router-cap")
    response = _client().post(
        "/geo/reachability",
        params={"feed_id": seeded_feed},
        json={"lon": -80.2, "lat": 26.0, "minutes": 999},
        headers=_auth_header(org_id, user_id),
    )
    assert response.status_code == 422


def test_geocode_requires_auth(pg_dsn):
    response = _client().post("/geo/geocode", json={"query": "Some Address"})
    assert response.status_code == 401


def test_geocode_end_to_end(db_conn, monkeypatch):
    org_id, user_id = _make_org_with_owner(db_conn, org_name="geocode-router")

    def fake_get(url, params=None, headers=None, timeout=None):
        class _FakeResponse:
            def raise_for_status(self) -> None:
                pass

            def json(self):
                return [{"lon": "-80.15", "lat": "26.15", "display_name": "Test Place, FL"}]

        return _FakeResponse()

    monkeypatch.setattr(geocoding_service.httpx, "get", fake_get)

    response = _client().post(
        "/geo/geocode",
        json={"query": f"unique geocode router query {uuid.uuid4().hex}"},
        headers=_auth_header(org_id, user_id),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["display_name"] == "Test Place, FL"


class _EmptyResponse:
    def raise_for_status(self) -> None:
        pass

    def json(self):
        return []


def test_geocode_returns_404_when_no_match(db_conn, monkeypatch):
    org_id, user_id = _make_org_with_owner(db_conn, org_name="geocode-nomatch")
    monkeypatch.setattr(geocoding_service.httpx, "get", lambda *a, **k: _EmptyResponse())

    response = _client().post(
        "/geo/geocode",
        json={"query": f"unique geocode no match query {uuid.uuid4().hex}"},
        headers=_auth_header(org_id, user_id),
    )
    assert response.status_code == 404
