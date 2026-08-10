"""Pydantic response models for /geo/* endpoints. These are also the vocabulary the
agent's tool layer (Phase 4) validates LLM tool-call arguments against, so keep request
bounds (limit/radius caps) here rather than duplicating them ad hoc in routers."""

from __future__ import annotations

from pydantic import BaseModel


class StopResult(BaseModel):
    stop_id: str
    stop_name: str | None = None
    stop_lat: float
    stop_lon: float
    distance_m: float


class NearestStopsResponse(BaseModel):
    stops: list[StopResult]


class RadiusStopsResponse(BaseModel):
    stops: list[StopResult]
