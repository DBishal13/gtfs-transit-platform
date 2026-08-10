"""Signup, login, token refresh, and org-scoped API-key management."""

from __future__ import annotations

import re
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from psycopg import Connection

from service.app.config import Settings, get_settings
from service.app.deps import CurrentPrincipal, get_db, require_role
from service.app.schemas.auth import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    LoginRequest,
    RefreshRequest,
    SignupRequest,
    TokenResponse,
)
from service.app.services import auth_service, tenancy_service

router = APIRouter(prefix="/auth", tags=["auth"])

_SLUG_UNSAFE_RE = re.compile(r"[^a-z0-9]+")


def _slugify(name: str) -> str:
    base = _SLUG_UNSAFE_RE.sub("-", name.strip().lower()).strip("-") or "org"
    return f"{base}-{secrets.token_hex(3)}"


def _issue_token_pair(*, user_id: uuid.UUID, org_id: uuid.UUID, settings: Settings) -> TokenResponse:
    return TokenResponse(
        access_token=auth_service.issue_access_token(
            user_id=user_id,
            org_id=org_id,
            secret=settings.jwt_secret_key,
            minutes=settings.jwt_access_token_minutes,
        ),
        refresh_token=auth_service.issue_refresh_token(
            user_id=user_id,
            org_id=org_id,
            secret=settings.jwt_secret_key,
            days=settings.jwt_refresh_token_days,
        ),
    )


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(
    body: SignupRequest,
    conn: Connection = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    if tenancy_service.get_user_by_email(conn, email=body.email) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    org_id = tenancy_service.create_org(conn, name=body.org_name, slug=_slugify(body.org_name))
    password_hash = auth_service.hash_password(body.password)
    user_id = tenancy_service.create_user(
        conn, org_id=org_id, email=body.email, password_hash=password_hash, role="owner"
    )
    conn.commit()
    return _issue_token_pair(user_id=user_id, org_id=org_id, settings=settings)


@router.post("/login", response_model=TokenResponse)
def login(
    body: LoginRequest,
    conn: Connection = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    user = tenancy_service.get_user_by_email(conn, email=body.email)
    if user is None or not auth_service.verify_password(body.password, user["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    tenancy_service.touch_last_login(conn, user_id=user["user_id"])
    conn.commit()
    return _issue_token_pair(user_id=user["user_id"], org_id=user["org_id"], settings=settings)


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, settings: Settings = Depends(get_settings)) -> TokenResponse:
    try:
        payload = auth_service.decode_token(body.refresh_token, secret=settings.jwt_secret_key)
    except Exception as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token") from exc
    if payload.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not a refresh token")

    return _issue_token_pair(
        user_id=uuid.UUID(payload["sub"]), org_id=uuid.UUID(payload["org_id"]), settings=settings
    )


@router.post("/api-keys", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    body: ApiKeyCreateRequest,
    principal: CurrentPrincipal = Depends(require_role("owner", "admin")),
    conn: Connection = Depends(get_db),
) -> ApiKeyCreateResponse:
    full_key, prefix, key_hash = auth_service.generate_api_key()
    api_key_id = tenancy_service.create_api_key(
        conn,
        org_id=principal.org_id,
        name=body.name,
        key_prefix=prefix,
        key_hash=key_hash,
        created_by=principal.user_id,
    )
    conn.commit()
    return ApiKeyCreateResponse(api_key_id=api_key_id, name=body.name, key=full_key, key_prefix=prefix)


@router.delete("/api-keys/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    api_key_id: uuid.UUID,
    principal: CurrentPrincipal = Depends(require_role("owner", "admin")),
    conn: Connection = Depends(get_db),
) -> None:
    revoked = tenancy_service.revoke_api_key(conn, org_id=principal.org_id, api_key_id=api_key_id)
    conn.commit()
    if not revoked:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")
