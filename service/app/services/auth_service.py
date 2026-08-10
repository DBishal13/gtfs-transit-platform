"""Password hashing, JWT issuance/verification, and API-key generation/hashing.

Password hashing: argon2id via argon2-cffi — the modern default, avoiding bcrypt's
72-byte input truncation footgun. JWT: short-lived access tokens plus longer-lived
refresh tokens, HS256-signed with Settings.jwt_secret_key (an RS256 upgrade is the
documented path if this backend is ever split across multiple independently-verifying
services — not needed for a single backend). API keys: the full secret is only ever
shown to the caller once, at creation time; only its sha256 hash and a display prefix
are persisted (service/migrations/0002_tenancy.sql::api_keys).
"""

from __future__ import annotations

import hashlib
import secrets
import time
import uuid

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_ph = PasswordHasher()

API_KEY_PREFIX = "gtp_live_"


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def generate_api_key() -> tuple[str, str, str]:
    """Returns (full_key_shown_once, key_prefix_for_display, key_hash_to_store)."""
    secret = secrets.token_urlsafe(32)
    full_key = f"{API_KEY_PREFIX}{secret}"
    key_hash = hash_api_key(full_key)
    display_prefix = full_key[: len(API_KEY_PREFIX) + 8]
    return full_key, display_prefix, key_hash


def hash_api_key(full_key: str) -> str:
    return hashlib.sha256(full_key.encode("utf-8")).hexdigest()


def _issue_token(*, user_id: uuid.UUID, org_id: uuid.UUID, secret: str, seconds: int, token_type: str) -> str:
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "org_id": str(org_id),
        "type": token_type,
        "iat": now,
        "exp": now + seconds,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def issue_access_token(*, user_id: uuid.UUID, org_id: uuid.UUID, secret: str, minutes: int) -> str:
    return _issue_token(
        user_id=user_id, org_id=org_id, secret=secret, seconds=minutes * 60, token_type="access"
    )


def issue_refresh_token(*, user_id: uuid.UUID, org_id: uuid.UUID, secret: str, days: int) -> str:
    return _issue_token(
        user_id=user_id, org_id=org_id, secret=secret, seconds=days * 86400, token_type="refresh"
    )


def decode_token(token: str, *, secret: str) -> dict:
    """Raises a jwt.PyJWTError subclass on any invalid/expired/malformed token — callers
    (service/app/deps.py, service/app/routers/auth.py) translate that into a 401."""
    return jwt.decode(token, secret, algorithms=["HS256"])
