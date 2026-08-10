from __future__ import annotations

from fastapi import APIRouter, Depends
from psycopg import Connection

from service.app.deps import CurrentPrincipal, get_current_principal, get_db
from service.app.schemas.auth import FeedListResponse
from service.app.services import tenancy_service

router = APIRouter(prefix="/feeds", tags=["feeds"])


@router.get("", response_model=FeedListResponse)
def list_feeds(
    principal: CurrentPrincipal = Depends(get_current_principal),
    conn: Connection = Depends(get_db),
) -> FeedListResponse:
    feed_ids = sorted(tenancy_service.resolve_visible_feed_ids(conn, org_id=principal.org_id))
    return FeedListResponse(feed_ids=feed_ids)
