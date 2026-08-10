"""End-to-end tests for the /agent/ask and /agent/conversations endpoints, with the LLM
provider mocked (no real API key or network call — see FakeLLMProvider in
test_agent_orchestrator.py). Skips automatically if no database is reachable (see
service/tests/conftest.py).
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from service.app.config import get_settings
from service.app.main import app
from service.app.routers import agent as agent_router
from service.app.services import auth_service, tenancy_service
from service.app.services.agent.llm_provider import LLMResponse
from service.tests.test_agent_orchestrator import FakeLLMProvider


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


def test_ask_requires_auth(pg_dsn, seeded_feed):
    response = _client().post("/agent/ask", json={"feed_id": seeded_feed, "question": "hi"})
    assert response.status_code == 401


def test_ask_rejects_feed_without_access(db_conn, seeded_feed):
    org_a, user_a = _make_org_with_owner(db_conn, org_name="agent-org-a")
    org_b, _ = _make_org_with_owner(db_conn, org_name="agent-org-b")
    with db_conn.cursor() as cur:
        cur.execute(
            "UPDATE feeds SET owner_org_id = %(org_id)s, is_public = false WHERE feed_id = %(feed_id)s",
            {"org_id": org_b, "feed_id": seeded_feed},
        )
    db_conn.commit()
    try:
        response = _client().post(
            "/agent/ask",
            json={"feed_id": seeded_feed, "question": "hi"},
            headers=_auth_header(org_a, user_a),
        )
        assert response.status_code == 403
    finally:
        with db_conn.cursor() as cur:
            cur.execute(
                "UPDATE feeds SET owner_org_id = NULL, is_public = true WHERE feed_id = %(feed_id)s",
                {"feed_id": seeded_feed},
            )
        db_conn.commit()


def test_ask_end_to_end_with_mocked_llm(db_conn, seeded_feed, monkeypatch):
    org_id, user_id = _make_org_with_owner(db_conn, org_name="agent-e2e")

    fake_llm = FakeLLMProvider(
        [LLMResponse(text="There are stops near you.", tool_calls=[], stop_reason="end_turn")]
    )
    monkeypatch.setattr(agent_router, "get_llm_provider", lambda settings: fake_llm)

    response = _client().post(
        "/agent/ask",
        json={"feed_id": seeded_feed, "question": "What stops are near me?"},
        headers=_auth_header(org_id, user_id),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "There are stops near you."
    assert "conversation_id" in body

    conv_response = _client().get(
        f"/agent/conversations/{body['conversation_id']}", headers=_auth_header(org_id, user_id)
    )
    assert conv_response.status_code == 200
    messages = conv_response.json()["messages"]
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[0]["content"] == "What stops are near me?"
    assert messages[1]["content"] == "There are stops near you."


def test_ask_continues_existing_conversation(db_conn, seeded_feed, monkeypatch):
    org_id, user_id = _make_org_with_owner(db_conn, org_name="agent-continue")
    fake_llm = FakeLLMProvider(
        [
            LLMResponse(text="First answer.", tool_calls=[], stop_reason="end_turn"),
            LLMResponse(text="Second answer.", tool_calls=[], stop_reason="end_turn"),
        ]
    )
    monkeypatch.setattr(agent_router, "get_llm_provider", lambda settings: fake_llm)

    first = _client().post(
        "/agent/ask",
        json={"feed_id": seeded_feed, "question": "First question"},
        headers=_auth_header(org_id, user_id),
    )
    conversation_id = first.json()["conversation_id"]

    second = _client().post(
        "/agent/ask",
        json={
            "feed_id": seeded_feed,
            "question": "Second question",
            "conversation_id": conversation_id,
        },
        headers=_auth_header(org_id, user_id),
    )
    assert second.status_code == 200
    assert second.json()["conversation_id"] == conversation_id
    assert second.json()["answer"] == "Second answer."

    second_call_messages = fake_llm.calls[1]["messages"]
    assert second_call_messages[0]["content"] == "First question"
    assert second_call_messages[1]["content"] == "First answer."
    assert second_call_messages[2]["content"] == "Second question"


def test_conversations_list_scoped_to_own_org(db_conn, seeded_feed, monkeypatch):
    org_a, user_a = _make_org_with_owner(db_conn, org_name="agent-list-a")
    org_b, user_b = _make_org_with_owner(db_conn, org_name="agent-list-b")
    fake_llm = FakeLLMProvider([LLMResponse(text="ok", tool_calls=[], stop_reason="end_turn")])
    monkeypatch.setattr(agent_router, "get_llm_provider", lambda settings: fake_llm)

    _client().post(
        "/agent/ask",
        json={"feed_id": seeded_feed, "question": "q"},
        headers=_auth_header(org_a, user_a),
    )

    response = _client().get("/agent/conversations", headers=_auth_header(org_b, user_b))
    assert response.status_code == 200
    assert response.json() == []
