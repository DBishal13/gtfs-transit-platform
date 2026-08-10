from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    org_name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class ApiKeyCreateResponse(BaseModel):
    api_key_id: uuid.UUID
    name: str
    key: str  # the full secret — shown exactly once, never retrievable again
    key_prefix: str


class UserSummary(BaseModel):
    user_id: uuid.UUID
    email: str
    role: str


class OrgSummary(BaseModel):
    org_id: uuid.UUID
    name: str
    slug: str
    plan: str
    members: list[UserSummary] = Field(default_factory=list)


class FeedListResponse(BaseModel):
    feed_ids: list[str]
