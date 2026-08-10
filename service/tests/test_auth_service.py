"""Pure unit tests for password hashing and JWT issuance/verification — no database
required, so these always run regardless of docker compose availability."""

from __future__ import annotations

import uuid

import jwt
import pytest

from service.app.services import auth_service


def test_password_hash_round_trip():
    hashed = auth_service.hash_password("correct horse battery staple")
    assert auth_service.verify_password("correct horse battery staple", hashed)
    assert not auth_service.verify_password("wrong password", hashed)


def test_access_token_round_trip():
    user_id, org_id = uuid.uuid4(), uuid.uuid4()
    token = auth_service.issue_access_token(user_id=user_id, org_id=org_id, secret="s3cr3t", minutes=15)
    payload = auth_service.decode_token(token, secret="s3cr3t")
    assert payload["sub"] == str(user_id)
    assert payload["org_id"] == str(org_id)
    assert payload["type"] == "access"


def test_refresh_token_has_refresh_type():
    user_id, org_id = uuid.uuid4(), uuid.uuid4()
    token = auth_service.issue_refresh_token(user_id=user_id, org_id=org_id, secret="s3cr3t", days=7)
    payload = auth_service.decode_token(token, secret="s3cr3t")
    assert payload["type"] == "refresh"


def test_expired_token_is_rejected():
    user_id, org_id = uuid.uuid4(), uuid.uuid4()
    token = auth_service.issue_access_token(user_id=user_id, org_id=org_id, secret="s3cr3t", minutes=-1)
    with pytest.raises(jwt.ExpiredSignatureError):
        auth_service.decode_token(token, secret="s3cr3t")


def test_token_rejected_with_wrong_secret():
    user_id, org_id = uuid.uuid4(), uuid.uuid4()
    token = auth_service.issue_access_token(user_id=user_id, org_id=org_id, secret="s3cr3t", minutes=15)
    with pytest.raises(jwt.InvalidSignatureError):
        auth_service.decode_token(token, secret="different-secret")


def test_api_key_generation_and_hash_lookup():
    full_key, prefix, key_hash = auth_service.generate_api_key()
    assert full_key.startswith(auth_service.API_KEY_PREFIX)
    assert full_key.startswith(prefix)
    assert auth_service.hash_api_key(full_key) == key_hash


def test_api_key_is_unique_per_call():
    key_a, _, _ = auth_service.generate_api_key()
    key_b, _, _ = auth_service.generate_api_key()
    assert key_a != key_b
