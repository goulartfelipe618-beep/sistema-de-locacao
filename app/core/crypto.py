"""Criptografia simétrica para credenciais de integração (§12.1)."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.secret_key.encode()).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_secret(value: str) -> str:
    """Criptografa um segredo (credencial/webhook) para armazenamento."""
    if not value:
        return ""
    return _fernet().encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str:
    """Descriptografa um segredo armazenado."""
    if not value:
        return ""
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Credencial criptografada inválida.") from exc
