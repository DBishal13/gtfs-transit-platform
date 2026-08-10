"""Pydantic response models for /geo/* endpoints. These are also the vocabulary the
agent's tool layer (Phase 4) validates LLM tool-call arguments against, so keep request
bounds (limit/radius caps) here rather than duplicating them ad hoc in routers."""

from __future__ import annotations

from pydantic import BaseModel, Field


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


class GeocodeRequest(BaseModel):
    query: str = Field(min_length=1, max_length=300)


class GeocodeResponse(BaseModel):
    lon: float
    lat: float
    display_name: str


class ReachabilityRequest(BaseModel):
    lon: float = Field(ge=-180, le=180)
    lat: float = Field(ge=-90, le=90)
    minutes: int = Field(gt=0, le=60)


class ReachablePoint(BaseModel):
    stop_id: str
    stop_name: str | None = None
    stop_lat: float
    stop_lon: float


class ReachabilityResponse(BaseModel):
    minutes: int
    walk_radius_m: float
    walk_only_stops: list[ReachablePoint]
    one_hop_stops: list[ReachablePoint]
