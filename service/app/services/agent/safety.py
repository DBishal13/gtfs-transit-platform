"""Prompt-injection and abuse mitigations for the agent's tool-calling loop.

These are structural controls enforced in code, not prose warnings to the model:

  1. MAX_TOOL_ITERATIONS bounds how many tool-calling round trips a single /agent/ask
     request can trigger — bounds both cost and the blast radius of any injection that
     partially succeeds.
  2. strip_server_owned_fields removes any org_id/feed_id the LLM proposed in tool
     arguments BEFORE those arguments are validated. The orchestrator always injects the
     real, server-resolved org_id/feed_id afterward (see orchestrator.py::_execute_tool_call),
     so an injected instruction telling the model to "use feed_id=X" cannot succeed — that
     argument is discarded outright, not merely overridden.
  3. Tool results are passed back to the LLM as tool_result content blocks (structurally
     labeled as data, not instructions), never appended as plain assistant/system text —
     see orchestrator.py's message construction.
  4. The tool allowlist (service/app/services/agent/tools.py::TOOL_REGISTRY) is fixed in
     server code and is never influenced by tool output — no tool result can register a
     new tool or change what's callable on a later iteration.

See service/tests/test_agent_tools_safety.py for the adversarial tests exercising these.
"""

from __future__ import annotations

MAX_TOOL_ITERATIONS = 5

_SERVER_OWNED_ARG_NAMES = {"org_id", "feed_id"}


def strip_server_owned_fields(arguments: dict) -> dict:
    return {k: v for k, v in arguments.items() if k not in _SERVER_OWNED_ARG_NAMES}
