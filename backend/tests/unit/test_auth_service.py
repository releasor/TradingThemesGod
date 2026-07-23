"""认证相关单元测试。"""

import jwt
import pytest

from app.core.auth import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.core.config import get_settings


def test_password_hash_round_trip():
    hashed = hash_password("secret123")
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)


def test_create_access_token(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "unit-test-secret")
    get_settings.cache_clear()
    token = create_access_token(user_id=42, username="alice")
    payload = jwt.decode(token, "unit-test-secret", algorithms=["HS256"])
    assert payload["sub"] == "42"
    assert payload["username"] == "alice"
    get_settings.cache_clear()
