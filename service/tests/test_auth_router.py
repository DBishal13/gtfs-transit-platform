"""End-to-end tests for the /auth, /orgs, and /feeds routers against a real database.
Skips automatically if no database is reachable (see service/tests/conftest.py).
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from service.app.main import app


def _client() -> TestClient:
    return TestClient(app)


def test_signup_then_login_round_trip(pg_dsn):
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    client = _client()

    signup_response = client.post(
        "/auth/signup",
        json={"org_name": "Acme Transit", "email": email, "password": "correct horse battery"},
    )
    assert signup_response.status_code == 201
    assert "access_token" in signup_response.json()

    login_response = client.post(
        "/auth/login", json={"email": email, "password": "correct horse battery"}
    )
    assert login_response.status_code == 200
    assert "access_token" in login_response.json()


def test_signup_rejects_duplicate_email(pg_dsn):
    email = f"dup-{uuid.uuid4().hex[:8]}@example.com"
    client = _client()
    body = {"org_name": "Acme Transit", "email": email, "password": "correct horse battery"}
    assert client.post("/auth/signup", json=body).status_code == 201
    assert client.post("/auth/signup", json=body).status_code == 409


def test_login_rejects_wrong_password(pg_dsn):
    email = f"wrongpw-{uuid.uuid4().hex[:8]}@example.com"
    client = _client()
    client.post(
        "/auth/signup", json={"org_name": "Acme", "email": email, "password": "right-password"}
    )
    response = client.post("/auth/login", json={"email": email, "password": "wrong-password"})
    assert response.status_code == 401


def test_refresh_token_issues_new_access_token(pg_dsn):
    email = f"refresh-{uuid.uuid4().hex[:8]}@example.com"
    client = _client()
    signup = client.post(
        "/auth/signup",
        json={"org_name": "Acme", "email": email, "password": "correct horse battery"},
    )
    refresh_token = signup.json()["refresh_token"]

    response = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_orgs_me_returns_org_and_owner(pg_dsn):
    email = f"orgme-{uuid.uuid4().hex[:8]}@example.com"
    client = _client()
    signup = client.post(
        "/auth/signup",
        json={"org_name": "Acme Transit", "email": email, "password": "correct horse battery"},
    )
    token = signup.json()["access_token"]

    response = client.get("/orgs/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Acme Transit"
    assert any(m["email"] == email and m["role"] == "owner" for m in body["members"])


def test_api_key_created_by_owner_authenticates_geo_requests(pg_dsn, seeded_feed):
    email = f"apikey-{uuid.uuid4().hex[:8]}@example.com"
    client = _client()
    signup = client.post(
        "/auth/signup",
        json={"org_name": "Acme Transit", "email": email, "password": "correct horse battery"},
    )
    access_token = signup.json()["access_token"]

    key_response = client.post(
        "/auth/api-keys",
        json={"name": "ci-test-key"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert key_response.status_code == 201
    api_key = key_response.json()["key"]

    # seeded_feed is public by default (Phase 1 loading leaves is_public=true), so any
    # org — including this freshly-signed-up one — should see it.
    feeds_response = client.get("/feeds", headers={"X-API-Key": api_key})
    assert feeds_response.status_code == 200
    assert seeded_feed in feeds_response.json()["feed_ids"]


def test_revoked_api_key_is_rejected(pg_dsn):
    email = f"revoke-{uuid.uuid4().hex[:8]}@example.com"
    client = _client()
    signup = client.post(
        "/auth/signup",
        json={"org_name": "Acme Transit", "email": email, "password": "correct horse battery"},
    )
    access_token = signup.json()["access_token"]

    key_response = client.post(
        "/auth/api-keys",
        json={"name": "revoke-me"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    api_key_id = key_response.json()["api_key_id"]
    api_key = key_response.json()["key"]

    revoke_response = client.delete(
        f"/auth/api-keys/{api_key_id}", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert revoke_response.status_code == 204

    feeds_response = client.get("/feeds", headers={"X-API-Key": api_key})
    assert feeds_response.status_code == 401


def test_api_key_cannot_mint_further_api_keys(pg_dsn):
    email = f"nested-{uuid.uuid4().hex[:8]}@example.com"
    client = _client()
    signup = client.post(
        "/auth/signup",
        json={"org_name": "Acme Transit", "email": email, "password": "correct horse battery"},
    )
    access_token = signup.json()["access_token"]
    key_response = client.post(
        "/auth/api-keys",
        json={"name": "first-key"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    api_key = key_response.json()["key"]

    response = client.post(
        "/auth/api-keys", json={"name": "second-key"}, headers={"X-API-Key": api_key}
    )
    assert response.status_code == 403
