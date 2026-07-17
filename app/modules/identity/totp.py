"""Utilitários TOTP (Google Authenticator / Authy) e códigos de recuperação."""

from __future__ import annotations

import base64
import io
import json
import secrets

import pyotp
import qrcode

from app.core.config import settings
from app.core.crypto import decrypt_secret, encrypt_secret


def generate_totp_secret() -> str:
    """Gera segredo base32 para aplicativo autenticador."""
    return pyotp.random_base32()


def build_provisioning_uri(secret: str, email: str) -> str:
    """URI otpauth:// para QR Code."""
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=settings.app_name)


def qr_data_uri(provisioning_uri: str) -> str:
    """QR Code em data URI (PNG base64) para exibição inline."""
    img = qrcode.make(provisioning_uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def verify_totp_code(secret: str, code: str, *, valid_window: int = 1) -> bool:
    """Valida código TOTP de 6 dígitos."""
    normalized = code.strip().replace(" ", "")
    if not normalized.isdigit() or len(normalized) != 6:
        return False
    return pyotp.TOTP(secret).verify(normalized, valid_window=valid_window)


def generate_recovery_codes(count: int = 10) -> list[str]:
    """Gera códigos de recuperação únicos (formato XXXX-XXXX)."""
    return [f"{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}" for _ in range(count)]


def normalize_recovery_code(code: str) -> str:
    """Normaliza código de recuperação para comparação."""
    return code.upper().replace("-", "").replace(" ", "")


def encrypt_recovery_codes(codes: list[str]) -> str:
    """Persiste códigos de recuperação criptografados."""
    normalized = [normalize_recovery_code(c) for c in codes]
    return encrypt_secret(json.dumps(normalized))


def decrypt_recovery_codes(encrypted: str | None) -> list[str]:
    """Carrega códigos de recuperação do armazenamento criptografado."""
    if not encrypted:
        return []
    return json.loads(decrypt_secret(encrypted))
