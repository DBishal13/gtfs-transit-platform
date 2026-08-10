"""Persistence for agent conversations/messages — the audit trail referenced throughout
this package's docstrings. Kept separate from orchestrator.py (pure in-memory logic,
unit-testable with a mocked LLMProvider and no database) so all DB I/O for the agent
lives in one place.

Only the plain question text and final answer text are persisted per turn — not the
intermediate tool_use/tool_result exchanges that happen mid-turn. This keeps token usage
bounded when a conversation continues across multiple turns, at the cost of the LLM not
literally re-seeing prior tool call details (its own prior answers still carry the
relevant information forward in plain language).
"""

from __future__ import annotations

import uuid

import psycopg
from psycopg.types.json import Jsonb


def create_conversation(
    conn: psycopg.Connection, *, org_id: uuid.UUID, user_id: uuid.UUID | None, feed_id: str
) -> uuid.UUID:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO agent_conversations (org_id, user_id, feed_id)
            VALUES (%(org_id)s, %(user_id)s, %(feed_id)s)
            RETURNING conversation_id
            """,
            {"org_id": org_id, "user_id": user_id, "feed_id": feed_id},
        )
        return cur.fetchone()[0]


def get_conversation(
    conn: psycopg.Connection, *, org_id: uuid.UUID, conversation_id: uuid.UUID
) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT conversation_id, org_id, user_id, feed_id, created_at
            FROM agent_conversations
            WHERE conversation_id = %(conversation_id)s AND org_id = %(org_id)s
            """,
            {"conversation_id": conversation_id, "org_id": org_id},
        )
        row = cur.fetchone()
        if row is None:
            return None
        columns = [d.name for d in cur.description]
        return dict(zip(columns, row))


def append_message(
    conn: psycopg.Connection,
    *,
    conversation_id: uuid.UUID,
    role: str,
    content: str,
    tool_calls: list[dict] | None = None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO agent_messages (conversation_id, role, content, tool_calls)
            VALUES (%(conversation_id)s, %(role)s, %(content)s, %(tool_calls)s)
            """,
            {
                "conversation_id": conversation_id,
                "role": role,
                "content": Jsonb(content),
                "tool_calls": Jsonb(tool_calls) if tool_calls is not None else None,
            },
        )


def list_messages(conn: psycopg.Connection, *, conversation_id: uuid.UUID) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT role, content, tool_calls, created_at
            FROM agent_messages
            WHERE conversation_id = %(conversation_id)s
            ORDER BY created_at
            """,
            {"conversation_id": conversation_id},
        )
        columns = [d.name for d in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]


def list_conversations(conn: psycopg.Connection, *, org_id: uuid.UUID) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT conversation_id, feed_id, created_at
            FROM agent_conversations
            WHERE org_id = %(org_id)s
            ORDER BY created_at DESC
            """,
            {"org_id": org_id},
        )
        columns = [d.name for d in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]
