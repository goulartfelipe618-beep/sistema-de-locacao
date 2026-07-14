"""Primitivas de segurança: hashing de senha e tokens JWT.

Nenhuma regra de negócio aqui — apenas funções puras de criptografia/token,
consumidas pelos serviços de autenticação.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import bcrypt
import jwt

from app.core.config import settings
from app.core.exceptions import AuthenticationError

_JWT_ALGORITHM = "HS256"
TokenType = Literal["access", "refresh"]


# ----------------------------------------------------------------- Senhas
def hash_password(plain_password: str) -> str:
    """Gera o hash bcrypt de uma senha em texto plano."""
    salt = bcrypt.gensalt(rounds=12)
    digest = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return digest.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha em texto plano corresponde ao hash armazenado."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


# ------------------------------------------------------------------ JWT
def _create_token(
    subject: str,
    token_type: TokenType,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(tz=UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.secret_key, algorithm=_JWT_ALGORITHM)


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    """Cria um token de acesso (curta duração) para a API REST."""
    return _create_token(
        subject,
        "access",
        timedelta(minutes=settings.access_token_expire_minutes),
        extra_claims,
    )


def create_refresh_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    """Cria um token de refresh (longa duração) para a API REST."""
    return _create_token(
        subject,
        "refresh",
        timedelta(days=settings.refresh_token_expire_days),
        extra_claims,
    )


def decode_token(token: str, *, expected_type: TokenType | None = None) -> dict[str, Any]:
    """Decodifica e valida um token JWT.

    Raises:
        AuthenticationError: token inválido, expirado ou de tipo inesperado.
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[_JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Token expirado.", code="token_expired") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError("Token inválido.", code="token_invalid") from exc

    if expected_type is not None and payload.get("type") != expected_type:
        raise AuthenticationError("Tipo de token inesperado.", code="token_type_invalid")
    return payload
