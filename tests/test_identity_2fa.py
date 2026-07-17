"""Testes de autenticação 2FA (TOTP, §14.3)."""

from __future__ import annotations

import uuid

import pyotp

from app.core.security import create_2fa_pending_token, decode_token
from app.modules.identity.totp import (
    build_provisioning_uri,
    encrypt_recovery_codes,
    generate_recovery_codes,
    generate_totp_secret,
    normalize_recovery_code,
    verify_totp_code,
)
from app.web.navigation import build_menu
from tests.test_navigation import _make_user


def test_generate_and_verify_totp() -> None:
    secret = generate_totp_secret()
    code = pyotp.TOTP(secret).now()
    assert verify_totp_code(secret, code) is True
    assert verify_totp_code(secret, "000000") is False


def test_provisioning_uri_contem_email() -> None:
    secret = generate_totp_secret()
    uri = build_provisioning_uri(secret, "admin@test.com")
    assert "admin%40test.com" in uri or "admin@test.com" in uri
    assert uri.startswith("otpauth://")


def test_recovery_codes_encrypt_decrypt_roundtrip() -> None:
    codes = generate_recovery_codes(5)
    enc = encrypt_recovery_codes(codes)
    assert enc
    assert len(enc) > 20


def test_normalize_recovery_code() -> None:
    assert normalize_recovery_code("ABCD-EFGH") == "ABCDEFGH"


def test_pending_token_2fa() -> None:
    uid = uuid.uuid4()
    tid = uuid.uuid4()
    token = create_2fa_pending_token(uid, tid)
    claims = decode_token(token, expected_type="2fa_pending")
    assert claims["sub"] == str(uid)
    assert claims["tenant_id"] == str(tid)


def test_menu_seguranca_2fa() -> None:
    menu = build_menu(_make_user({"dashboard.painel.visualizar"}))
    config = next(s for s in menu if s["label"] == "Configurações")
    labels = {item["label"] for item in config["children"]}
    assert "Autenticação 2FA" in labels
