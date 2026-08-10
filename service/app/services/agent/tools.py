"""Tool execution layer: each entry wraps a geo_service/geocoding_service/
reachability_service function — the exact same functions the direct REST endpoints in
service/app/routers/geo.py call. org_id/feed_id are ALWAYS supplied by the caller
(service/app/services/agent/orchestrator.py) from server-resolved values, never taken
from LLM-proposed tool arguments. This is the single load-bearing security control that
keeps the agent from being tricked (via prompt injection or adversarial phrasing) into
querying a tenant/feed it wasn't granted — see safety.py and
service/tests/test_agent_tools_safety.py.

TOOL_REGISTRY is the fixed, server-side tool allowlist: the orchestrator rejects any tool
name not present here before validating arguments, and this list never changes based on
tool output or model behavior.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

import psycopg
from pydantic import BaseModel

from service.app.config import Settings
from service.app.services import geo_service, geocoding_service, reachability_service
from service.app.services.agent.tool_schemas import (
    GeocodeAddressArgs,
    NearestStopsArgs,
    ReachableAreaArgs,
    StopsWithinRadiusArgs,
)

ToolExecutor = Callable[[psycopg.Connection, uuid.UUID, str, BaseModel, Settings], dict]


def run_nearest_stops(
    conn: psycopg.Connection, org_id: uuid.UUID, feed_id: str, args: NearestStopsArgs, settings: Settings
) -> dict:
    del org_id, settings
    stops = geo_service.nearest_stops(conn, feed_id=feed_id, lon=args.lon, lat=args.lat, limit=args.limit)
    return {"stops": [s.model_dump() for s in stops]}


def run_stops_within_radius(
    conn: psycopg.Connection,
    org_id: uuid.UUID,
    feed_id: str,
    args: StopsWithinRadiusArgs,
    settings: Settings,
) -> dict:
    del org_id, settings
    stops = geo_service.stops_within_radius(
        conn, feed_id=feed_id, lon=args.lon, lat=args.lat, radius_m=args.radius_m
    )
    return {"stops": [s.model_dump() for s in stops]}


def run_geocode_address(
    conn: psycopg.Connection,
    org_id: uuid.UUID,
    feed_id: str,
    args: GeocodeAddressArgs,
    settings: Settings,
) -> dict:
    del conn, org_id, feed_id
    provider = geocoding_service.get_geocoding_provider(settings)
    result = provider.geocode(args.query)
    if result is None:
        return {"found": False}
    return {"found": True, "lon": result.lon, "lat": result.lat, "display_name": result.display_name}


def run_reachable_area(
    conn: psycopg.Connection,
    org_id: uuid.UUID,
    feed_id: str,
    args: ReachableAreaArgs,
    settings: Settings,
) -> dict:
    del org_id, settings
    result = reachability_service.compute_reachability(
        conn, feed_id=feed_id, lon=args.lon, lat=args.lat, minutes=args.minutes
    )
    return {
        "minutes": result["minutes"],
        "walk_radius_m": result["walk_radius_m"],
        "walk_only_stops": [s.model_dump() for s in result["walk_only_stops"]],
        "one_hop_stops": [s.model_dump() for s in result["one_hop_stops"]],
    }


TOOL_REGISTRY: dict[str, tuple[type[BaseModel], ToolExecutor]] = {
    "nearest_stops": (NearestStopsArgs, run_nearest_stops),
    "stops_within_radius": (StopsWithinRadiusArgs, run_stops_within_radius),
    "geocode_address": (GeocodeAddressArgs, run_geocode_address),
    "reachable_area": (ReachableAreaArgs, run_reachable_area),
}
