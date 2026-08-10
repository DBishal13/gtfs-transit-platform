"""Direct REST endpoints for spatial queries.

Requires authentication (JWT or API key — see service/app/deps.py::get_current_principal)
and enforces tenant scope: a request for a feed_id outside
tenancy_service.resolve_visible_feed_ids(org_id) is rejected with 403 before any geo query
runs. This is the exact same boundary the agent's tool layer (Phase 4) relies on — both
entry points share it, so there is only one place tenant isolation can go wrong.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from psycopg import Connection

from service.app.deps import CurrentPrincipal, get_current_principal, get_db
from service.app.schemas.geo import NearestStopsResponse, RadiusStopsResponse
from service.app.services import geo_service, tenancy_service

router = APIRouter(prefix="/geo", tags=["geo"])

MAX_LIMIT = 50
MAX_RADIUS_M = 5000


def _require_feed_access(conn: Connection, principal: CurrentPrincipal, feed_id: str) -> None:
    visible = tenancy_service.resolve_visible_feed_ids(conn, org_id=principal.org_id)
    if feed_id not in visible:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"No access to feed '{feed_id}'")


@router.get("/nearest-stops", response_model=NearestStopsResponse)
def get_nearest_stops(
    feed_id: str,
    lon: float = Query(..., ge=-180, le=180),
    lat: float = Query(..., ge=-90, le=90),
    limit: int = Query(10, ge=1, le=MAX_LIMIT),
    principal: CurrentPrincipal = Depends(get_current_principal),
    conn: Connection = Depends(get_db),
) -> NearestStopsResponse:
    _require_feed_access(conn, principal, feed_id)
    stops = geo_service.nearest_stops(conn, feed_id=feed_id, lon=lon, lat=lat, limit=limit)
    return NearestStopsResponse(stops=stops)


@router.get("/stops-within-radius", response_model=RadiusStopsResponse)
def get_stops_within_radius(
    feed_id: str,
    lon: float = Query(..., ge=-180, le=180),
    lat: float = Query(..., ge=-90, le=90),
    radius_m: float = Query(400, gt=0, le=MAX_RADIUS_M),
    principal: CurrentPrincipal = Depends(get_current_principal),
    conn: Connection = Depends(get_db),
) -> RadiusStopsResponse:
    _require_feed_access(conn, principal, feed_id)
    stops = geo_service.stops_within_radius(
        conn, feed_id=feed_id, lon=lon, lat=lat, radius_m=radius_m
    )
    return RadiusStopsResponse(stops=stops)
