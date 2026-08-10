"""Direct REST endpoints for spatial queries. Phase 1 ships without auth (see the plan's
phased milestones) — `feed_id` is taken at face value here. Phase 2 retrofits this router
to require get_current_org and validate feed_id against resolve_visible_feed_ids before
any query below runs, closing the tenant-isolation gap deliberately left open for now.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from psycopg import Connection

from service.app.deps import get_db
from service.app.schemas.geo import NearestStopsResponse, RadiusStopsResponse
from service.app.services import geo_service

router = APIRouter(prefix="/geo", tags=["geo"])

MAX_LIMIT = 50
MAX_RADIUS_M = 5000


@router.get("/nearest-stops", response_model=NearestStopsResponse)
def get_nearest_stops(
    feed_id: str,
    lon: float = Query(..., ge=-180, le=180),
    lat: float = Query(..., ge=-90, le=90),
    limit: int = Query(10, ge=1, le=MAX_LIMIT),
    conn: Connection = Depends(get_db),
) -> NearestStopsResponse:
    stops = geo_service.nearest_stops(conn, feed_id=feed_id, lon=lon, lat=lat, limit=limit)
    return NearestStopsResponse(stops=stops)


@router.get("/stops-within-radius", response_model=RadiusStopsResponse)
def get_stops_within_radius(
    feed_id: str,
    lon: float = Query(..., ge=-180, le=180),
    lat: float = Query(..., ge=-90, le=90),
    radius_m: float = Query(400, gt=0, le=MAX_RADIUS_M),
    conn: Connection = Depends(get_db),
) -> RadiusStopsResponse:
    stops = geo_service.stops_within_radius(
        conn, feed_id=feed_id, lon=lon, lat=lat, radius_m=radius_m
    )
    return RadiusStopsResponse(stops=stops)
