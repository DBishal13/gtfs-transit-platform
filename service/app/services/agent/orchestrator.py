"""Bounded tool-calling loop: the mechanism through which NL questions become answers.

The LLM never writes or executes SQL — it only ever sees the fixed tool vocabulary in
tool_schemas.TOOL_DEFINITIONS. Every tool call is validated against that tool's Pydantic
schema, and org_id/feed_id are ALWAYS injected here from server-resolved values, never
taken from the LLM's proposed arguments even if present (see
safety.py::strip_server_owned_fields). This is pure in-memory logic with no direct
database-connection requirement of its own beyond what tool execution needs, so it's
fully unit-testable against a mocked LLMProvider — see
service/tests/test_agent_orchestrator.py.
"""

from __future__ import annotations

import json
import uuid

import psycopg
from pydantic import ValidationError

from service.app.config import Settings
from service.app.services.agent.llm_provider import LLMProvider, LLMResponse, ToolCall
from service.app.services.agent.prompts import AGENT_SYSTEM_PROMPT
from service.app.services.agent.safety import MAX_TOOL_ITERATIONS, strip_server_owned_fields
from service.app.services.agent.tool_schemas import TOOL_DEFINITIONS
from service.app.services.agent.tools import TOOL_REGISTRY

_SUMMARY_MAX_CHARS = 300


def _summarize(result: dict) -> str:
    text = json.dumps(result)
    return text if len(text) <= _SUMMARY_MAX_CHARS else text[: _SUMMARY_MAX_CHARS - 3] + "..."


def _execute_tool_call(
    conn: psycopg.Connection,
    *,
    org_id: uuid.UUID,
    feed_id: str,
    call: ToolCall,
    settings: Settings,
) -> dict:
    entry = TOOL_REGISTRY.get(call.name)
    if entry is None:
        return {"error": f"Unknown tool '{call.name}'"}

    args_model, executor = entry
    try:
        args = args_model(**strip_server_owned_fields(call.arguments))
    except ValidationError as exc:
        return {"error": f"Invalid arguments for tool '{call.name}'", "details": exc.errors()}

    return executor(conn, org_id, feed_id, args, settings)


def _extract_map_points(tool_name: str, result: dict) -> list[dict]:
    points: list[dict] = []
    if tool_name in ("nearest_stops", "stops_within_radius"):
        for stop in result.get("stops", []):
            points.append({"lon": stop["stop_lon"], "lat": stop["stop_lat"], "label": stop.get("stop_name")})
    elif tool_name == "geocode_address" and result.get("found"):
        points.append({"lon": result["lon"], "lat": result["lat"], "label": result.get("display_name")})
    elif tool_name == "reachable_area":
        for stop in [*result.get("walk_only_stops", []), *result.get("one_hop_stops", [])]:
            points.append({"lon": stop["stop_lon"], "lat": stop["stop_lat"], "label": stop.get("stop_name")})
    return points


def run_agent_turn(
    conn: psycopg.Connection,
    *,
    org_id: uuid.UUID,
    feed_id: str,
    question: str,
    history: list[dict],
    llm: LLMProvider,
    settings: Settings,
) -> dict:
    """Runs one bounded tool-calling turn against `llm`.

    `history` is the prior canonical message list for this conversation (empty for a new
    conversation — see service/app/services/agent/store.py, which persists only the plain
    question/answer text per turn, not intermediate tool exchanges, keeping cross-turn
    token usage bounded).

    Returns {"answer": str, "map_points": list[dict], "tool_trace": list[dict],
    "usage": {"input_tokens": int, "output_tokens": int}} — usage is summed across every
    llm.chat() call made during this turn (Phase 6's api_usage_events metering reads it).
    """
    messages = [*history, {"role": "user", "content": question}]
    tool_trace: list[dict] = []
    map_points: list[dict] = []
    total_input_tokens = 0
    total_output_tokens = 0

    def _usage() -> dict:
        return {"input_tokens": total_input_tokens, "output_tokens": total_output_tokens}

    for _ in range(MAX_TOOL_ITERATIONS):
        response: LLMResponse = llm.chat(messages=messages, tools=TOOL_DEFINITIONS, system=AGENT_SYSTEM_PROMPT)
        total_input_tokens += response.usage.input_tokens
        total_output_tokens += response.usage.output_tokens

        if not response.tool_calls:
            return {
                "answer": response.text or "",
                "map_points": map_points,
                "tool_trace": tool_trace,
                "usage": _usage(),
            }

        assistant_blocks: list[dict] = []
        if response.text:
            assistant_blocks.append({"type": "text", "text": response.text})
        for call in response.tool_calls:
            assistant_blocks.append({"type": "tool_use", "id": call.id, "name": call.name, "input": call.arguments})
        messages.append({"role": "assistant", "content": assistant_blocks})

        tool_result_blocks: list[dict] = []
        for call in response.tool_calls:
            result = _execute_tool_call(conn, org_id=org_id, feed_id=feed_id, call=call, settings=settings)
            tool_trace.append(
                {"tool_name": call.name, "arguments": call.arguments, "result_summary": _summarize(result)}
            )
            map_points.extend(_extract_map_points(call.name, result))
            tool_result_blocks.append(
                {"type": "tool_result", "tool_use_id": call.id, "content": json.dumps(result)}
            )
        messages.append({"role": "user", "content": tool_result_blocks})

    # Iteration cap exceeded: force a final answer with no further tools offered, rather
    # than looping forever or erroring out.
    final = llm.chat(messages=messages, tools=[], system=AGENT_SYSTEM_PROMPT)
    total_input_tokens += final.usage.input_tokens
    total_output_tokens += final.usage.output_tokens
    fallback_text = final.text or "I wasn't able to fully answer within the allowed number of steps."
    return {
        "answer": fallback_text,
        "map_points": map_points,
        "tool_trace": tool_trace,
        "usage": _usage(),
    }
