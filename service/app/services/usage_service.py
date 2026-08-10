"""Basic per-org API usage metering (service/migrations/0004_usage_events.sql).

Currently only called from service/app/routers/agent.py::ask, since /agent/ask is the
one endpoint expensive enough (an LLM call plus tool executions) to be worth metering
individually. Not wired to any billing/invoicing — see service/README.md's out-of-scope
list. A simple "usage this month" query per org is straightforward against this table;
a dashboard over it does not exist yet.
"""

from __future__ import annotations

import uuid

import psycopg


def record_usage_event(
    conn: psycopg.Connection,
    *,
    org_id: uuid.UUID,
    route: str,
    method: str,
    status_code: int,
    latency_ms: int,
    llm_input_tokens: int | None = None,
    llm_output_tokens: int | None = None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO api_usage_events
              (org_id, route, method, status_code, latency_ms, llm_input_tokens, llm_output_tokens)
            VALUES (%(org_id)s, %(route)s, %(method)s, %(status_code)s, %(latency_ms)s,
                    %(llm_input_tokens)s, %(llm_output_tokens)s)
            """,
            {
                "org_id": org_id,
                "route": route,
                "method": method,
                "status_code": status_code,
                "latency_ms": latency_ms,
                "llm_input_tokens": llm_input_tokens,
                "llm_output_tokens": llm_output_tokens,
            },
        )
