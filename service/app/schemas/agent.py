from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    feed_id: str
    question: str = Field(min_length=1, max_length=2000)
    conversation_id: uuid.UUID | None = None


class MapPoint(BaseModel):
    lon: float
    lat: float
    label: str | None = None


class MapPayload(BaseModel):
    points: list[MapPoint] = Field(default_factory=list)


class ToolTraceEntry(BaseModel):
    tool_name: str
    arguments: dict
    result_summary: str


class AskResponse(BaseModel):
    conversation_id: uuid.UUID
    answer: str
    map_payload: MapPayload
    tool_trace: list[ToolTraceEntry]


class ConversationSummary(BaseModel):
    conversation_id: uuid.UUID
    feed_id: str
    created_at: datetime


class ConversationMessage(BaseModel):
    role: str
    content: str | list[dict]


class ConversationDetail(BaseModel):
    conversation_id: uuid.UUID
    feed_id: str
    created_at: datetime
    messages: list[ConversationMessage]
