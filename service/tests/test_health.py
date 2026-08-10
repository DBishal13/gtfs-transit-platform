from __future__ import annotations

from fastapi.testclient import TestClient

from service.app.main import app


def test_healthz_requires_no_database():
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
