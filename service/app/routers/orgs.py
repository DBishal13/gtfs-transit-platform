from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from psycopg import Connection

from service.app.deps import CurrentPrincipal, get_current_principal, get_db
from service.app.schemas.auth import OrgSummary
from service.app.services import tenancy_service

router = APIRouter(prefix="/orgs", tags=["orgs"])


@router.get("/me", response_model=OrgSummary)
def get_my_org(
    principal: CurrentPrincipal = Depends(get_current_principal),
    conn: Connection = Depends(get_db),
) -> OrgSummary:
    org = tenancy_service.get_org(conn, org_id=principal.org_id)
    if org is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Org not found")
    members = tenancy_service.list_org_users(conn, org_id=principal.org_id)
    return OrgSummary(**org, members=members)
