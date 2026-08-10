"""Adversarial tests for the agent's tool-execution safety controls
(service/app/services/agent/safety.py, orchestrator.py::_execute_tool_call).

Tests that don't touch the database always run; the one exercising a real tool against
real data skips automatically if no database is reachable (see service/tests/conftest.py).
"""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from service.app.config import Settings
from service.app.services.agent import orchestrator, safety
from service.app.services.agent.llm_provider import ToolCall
from service.app.services.agent.tool_schemas import NearestStopsArgs


def test_strip_server_owned_fields_removes_org_and_feed_id():
    cleaned = safety.strip_server_owned_fields(
        {"lon": 1.0, "lat": 2.0, "org_id": "attacker-org", "feed_id": "attacker-feed"}
    )
    assert cleaned == {"lon": 1.0, "lat": 2.0}


def test_execute_tool_call_rejects_unknown_tool_name():
    result = orchestrator._execute_tool_call(
        None,
        org_id=uuid.uuid4(),
        feed_id="feed-1",
        call=ToolCall(id="x", name="drop_all_tables", arguments={}),
        settings=Settings(),
    )
    assert "error" in result
    assert "Unknown tool" in result["error"]


def test_execute_tool_call_rejects_oversized_radius_before_touching_db():
    result = orchestrator._execute_tool_call(
        None,  # conn=None: proves this never reaches SQL — validation fails first
        org_id=uuid.uuid4(),
        feed_id="feed-1",
        call=ToolCall(
            id="x", name="stops_within_radius", arguments={"lon": 0, "lat": 0, "radius_m": 999_999_999}
        ),
        settings=Settings(),
    )
    assert "error" in result


def test_execute_tool_call_rejects_oversized_limit_before_touching_db():
    result = orchestrator._execute_tool_call(
        None,
        org_id=uuid.uuid4(),
        feed_id="feed-1",
        call=ToolCall(id="x", name="nearest_stops", arguments={"lon": 0, "lat": 0, "limit": 10_000}),
        settings=Settings(),
    )
    assert "error" in result


def test_nearest_stops_args_model_rejects_out_of_range_arguments():
    with pytest.raises(ValidationError):
        NearestStopsArgs(lon=0, lat=0, limit=51)  # cap is 50


def test_execute_tool_call_ignores_llm_proposed_org_and_feed_id(db_conn, seeded_feed):
    """The load-bearing security property: even if the LLM's tool arguments include an
    org_id/feed_id (e.g. via prompt injection), the tool executes against the real,
    server-resolved org_id/feed_id — never the proposed ones."""
    real_org_id = uuid.uuid4()
    call = ToolCall(
        id="x",
        name="nearest_stops",
        arguments={
            "lon": -80.200,
            "lat": 26.000,
            "limit": 5,
            "org_id": str(uuid.uuid4()),  # attacker-proposed, must be ignored
            "feed_id": "some-other-tenants-feed",  # attacker-proposed, must be ignored
        },
    )
    result = orchestrator._execute_tool_call(
        db_conn, org_id=real_org_id, feed_id=seeded_feed, call=call, settings=Settings()
    )
    assert "error" not in result
    # Queried against seeded_feed (the real, server-injected feed_id), not the proposed one.
    assert result["stops"][0]["stop_id"] == "S1"
