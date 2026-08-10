"""Shared FastAPI dependencies: database connection, and auth resolution.

get_current_principal accepts EITHER a valid `Authorization: Bearer <JWT>` header (the
browser SPA session) OR an `X-API-Key: <key>` header (programmatic/agent access) and
resolves both to the same CurrentPrincipal shape, so every router downstream is
auth-mechanism-agnostic — see docs on this in the plan's Auth section.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass

import jwt
from fastapi import Depends, Header, HTTPException, status
from psycopg import Connection

from service.app.config import Settings, get_settings
from service.app.db import get_pool
from service.app.services import auth_service, tenancy_service


def get_db() -> Iterator[Connection]:
    with get_pool().connection() as conn:
        yield conn


@dataclass(frozen=True)
class CurrentPrincipal:
    org_id: uuid.UUID
    user_id: uuid.UUID | None  # None for API-key-authenticated requests
    role: str  # "owner" | "admin" | "member" | "viewer" | "api_key"


def _resolve_from_jwt(token: str, settings: Settings) -> tuple[uuid.UUID, uuid.UUID] | None:
    try:
        payload = auth_service.decode_token(token, secret=settings.jwt_secret_key)
    except jwt.PyJWTError:
        return None
    if payload.get("type") != "access":
        return None
    try:
        return uuid.UUID(payload["org_id"]), uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        return None


def get_current_principal(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
    conn: Connection = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> CurrentPrincipal:
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
        resolved = _resolve_from_jwt(token, settings)
        if resolved is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
        org_id, user_id = resolved
        with conn.cursor() as cur:
            cur.execute("SELECT role FROM users WHERE user_id = %(user_id)s", {"user_id": user_id})
            row = cur.fetchone()
        if row is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists")
        return CurrentPrincipal(org_id=org_id, user_id=user_id, role=row[0])

    if x_api_key:
        key_hash = auth_service.hash_api_key(x_api_key)
        org_id = tenancy_service.get_org_id_for_active_api_key(conn, key_hash=key_hash)
        if org_id is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or revoked API key")
        tenancy_service.touch_api_key_last_used(conn, key_hash=key_hash)
        return CurrentPrincipal(org_id=org_id, user_id=None, role="api_key")

    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing Authorization or X-API-Key header")


def require_role(*allowed_roles: str):
    """Dependency factory: 403s unless the resolved principal's role is one of
    `allowed_roles`. API-key principals have role "api_key" and so are excluded from
    any owner/admin-only action (e.g. minting further API keys) unless explicitly listed."""

    def _check(principal: CurrentPrincipal = Depends(get_current_principal)) -> CurrentPrincipal:
        if principal.role not in allowed_roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
        return principal

    return _check
