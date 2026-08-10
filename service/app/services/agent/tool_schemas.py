"""Pydantic models defining the ONLY vocabulary the LLM can invoke.

org_id/feed_id are never part of these schemas — service/app/services/agent/tools.py
injects them server-side, so the LLM cannot name a tenant/feed it wasn't already granted
(see tenancy_service.resolve_visible_feed_ids). Bounds here (limit/radius_m/minutes caps)
are the actual security boundary, not just input hygiene: they're enforced by Pydantic
before a tool function ever runs, so a request for e.g. radius_m=999999999 is rejected at
validation time, never reaches SQL.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field


class NearestStopsArgs(BaseModel):
    lon: float = Field(ge=-180, le=180)
    lat: float = Field(ge=-90, le=90)
    limit: int = Field(default=10, ge=1, le=50)


class StopsWithinRadiusArgs(BaseModel):
    lon: float = Field(ge=-180, le=180)
    lat: float = Field(ge=-90, le=90)
    radius_m: float = Field(default=400, gt=0, le=5000)


class GeocodeAddressArgs(BaseModel):
    query: str = Field(min_length=1, max_length=300)


class ReachableAreaArgs(BaseModel):
    lon: float = Field(ge=-180, le=180)
    lat: float = Field(ge=-90, le=90)
    minutes: int = Field(gt=0, le=60)


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    args_model: type[BaseModel]

    @property
    def input_schema(self) -> dict:
        return self.args_model.model_json_schema()


TOOL_DEFINITIONS: list[ToolDefinition] = [
    ToolDefinition(
        "nearest_stops",
        "Find the N nearest transit stops to a coordinate, ordered by distance.",
        NearestStopsArgs,
    ),
    ToolDefinition(
        "stops_within_radius",
        "Find all transit stops within a radius (in meters) of a coordinate.",
        StopsWithinRadiusArgs,
    ),
    ToolDefinition(
        "geocode_address",
        "Resolve a free-text address or place name to coordinates.",
        GeocodeAddressArgs,
    ),
    ToolDefinition(
        "reachable_area",
        "Compute what's reachable within N minutes (walking, plus one transit boarding) "
        "from a coordinate. This is an approximation, not turn-by-turn routing.",
        ReachableAreaArgs,
    ),
]
