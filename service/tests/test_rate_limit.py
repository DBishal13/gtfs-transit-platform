"""Tests for the per-org rate limiter (service/app/middleware/rate_limit.py).

The pure check_rate_limit() tests always run (no DB). The endpoint-level test requires a
database — skips automatically if none is reachable (see service/tests/conftest.py).
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from service.app.config import Settings, get_settings
from service.app.main import app
from service.app.middleware import rate_limit
from service.app.services import auth_service, tenancy_service


def test_check_rate_limit_allows_up_to_the_limit():
    org_id = uuid.uuid4()
    now = 1000.0
    assert rate_limit.check_rate_limit(org_id, limit_per_min=3, now=now) is True
    assert rate_limit.check_rate_limit(org_id, limit_per_min=3, now=now) is True
    assert rate_limit.check_rate_limit(org_id, limit_per_min=3, now=now) is True


def test_check_rate_limit_rejects_beyond_the_limit():
    org_id = uuid.uuid4()
    now = 2000.0
    for _ in range(5):
        rate_limit.check_rate_limit(org_id, limit_per_min=5, now=now)
    assert rate_limit.check_rate_limit(org_id, limit_per_min=5, now=now) is False


def test_check_rate_limit_resets_after_the_window_elapses():
    org_id = uuid.uuid4()
    for _ in range(3):
        rate_limit.check_rate_limit(org_id, limit_per_min=3, now=3000.0)
    assert rate_limit.check_rate_limit(org_id, limit_per_min=3, now=3000.0) is False
    # 61 seconds later, the earlier requests have aged out of the 60s window.
    assert rate_limit.check_rate_limit(org_id, limit_per_min=3, now=3061.0) is True


def test_check_rate_limit_tracks_orgs_independently():
    org_a, org_b = uuid.uuid4(), uuid.uuid4()
    now = 4000.0
    assert rate_limit.check_rate_limit(org_a, limit_per_min=1, now=now) is True
    assert rate_limit.check_rate_limit(org_a, limit_per_min=1, now=now) is False
    assert rate_limit.check_rate_limit(org_b, limit_per_min=1, now=now) is True


def test_rate_limited_endpoint_returns_429_once_exceeded(db_conn, seeded_feed):
    org_id = tenancy_service.create_org(
        db_conn, name="rate-limit-org", slug=f"rl-{uuid.uuid4().hex[:8]}"
    )
    user_id = tenancy_service.create_user(
        db_conn,
        org_id=org_id,
        email=f"rl-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=auth_service.hash_password("test-password"),
        role="owner",
    )
    db_conn.commit()

    settings = get_settings()
    token = auth_service.issue_access_token(
        user_id=user_id, org_id=org_id, secret=settings.jwt_secret_key, minutes=15
    )

    app.dependency_overrides[get_settings] = lambda: Settings(rate_limit_default_per_min=2)
    try:
        client = TestClient(app)
        headers = {"Authorization": f"Bearer {token}"}
        params = {"feed_id": seeded_feed, "lon": -80.2, "lat": 26.0, "limit": 1}
        assert client.get("/geo/nearest-stops", params=params, headers=headers).status_code == 200
        assert client.get("/geo/nearest-stops", params=params, headers=headers).status_code == 200
        assert client.get("/geo/nearest-stops", params=params, headers=headers).status_code == 429
    finally:
        app.dependency_overrides.pop(get_settings, None)
        rate_limit.reset_for_tests(org_id)
