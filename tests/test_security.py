"""Testes das primitivas de segurança (hash de senha e JWT)."""

from __future__ import annotations

import pytest

from app.core.exceptions import AuthenticationError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_and_verify() -> None:
    hashed = hash_password("SenhaForte@123")
    assert hashed != "SenhaForte@123"
    assert verify_password("SenhaForte@123", hashed) is True
    assert verify_password("senhaErrada", hashed) is False


def test_password_verify_invalid_hash() -> None:
    assert verify_password("qualquer", "hash-invalido") is False


def test_access_token_roundtrip() -> None:
    token = create_access_token("user-123", {"tenant_id": "t-1", "is_superuser": True})
    payload = decode_token(token, expected_type="access")
    assert payload["sub"] == "user-123"
    assert payload["tenant_id"] == "t-1"
    assert payload["is_superuser"] is True


def test_refresh_token_type_enforced() -> None:
    token = create_refresh_token("user-123", {"tenant_id": "t-1"})
    with pytest.raises(AuthenticationError):
        decode_token(token, expected_type="access")


def test_invalid_token_raises() -> None:
    with pytest.raises(AuthenticationError):
        decode_token("not-a-token", expected_type="access")
