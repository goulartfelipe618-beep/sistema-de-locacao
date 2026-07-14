"""Contexto de execução por requisição/tarefa.

Usa :mod:`contextvars` para propagar, de forma segura em ambientes assíncronos,
informações do contexto atual (tenant, filial, usuário, correlação) sem precisar
passá-las explicitamente por todas as camadas.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from dataclasses import dataclass

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_tenant_id: ContextVar[uuid.UUID | None] = ContextVar("tenant_id", default=None)
_filial_id: ContextVar[uuid.UUID | None] = ContextVar("filial_id", default=None)
_user_id: ContextVar[uuid.UUID | None] = ContextVar("user_id", default=None)
_is_superuser: ContextVar[bool] = ContextVar("is_superuser", default=False)


@dataclass(frozen=True, slots=True)
class RequestContext:
    """Instantâneo imutável do contexto atual."""

    correlation_id: str | None
    tenant_id: uuid.UUID | None
    filial_id: uuid.UUID | None
    user_id: uuid.UUID | None
    is_superuser: bool


# ------------------------------------------------------------- Correlation ID
def set_correlation_id(value: str) -> None:
    _correlation_id.set(value)


def get_correlation_id() -> str | None:
    return _correlation_id.get()


def new_correlation_id() -> str:
    """Gera e registra um novo identificador de correlação."""
    value = uuid.uuid4().hex
    _correlation_id.set(value)
    return value


# -------------------------------------------------------------------- Tenant
def set_tenant_id(value: uuid.UUID | None) -> None:
    _tenant_id.set(value)


def get_tenant_id() -> uuid.UUID | None:
    return _tenant_id.get()


# -------------------------------------------------------------------- Filial
def set_filial_id(value: uuid.UUID | None) -> None:
    _filial_id.set(value)


def get_filial_id() -> uuid.UUID | None:
    return _filial_id.get()


# ---------------------------------------------------------------------- User
def set_user_id(value: uuid.UUID | None) -> None:
    _user_id.set(value)


def get_user_id() -> uuid.UUID | None:
    return _user_id.get()


def set_is_superuser(value: bool) -> None:
    _is_superuser.set(value)


def get_is_superuser() -> bool:
    return _is_superuser.get()


# -------------------------------------------------------------------- Helpers
def current_context() -> RequestContext:
    """Retorna o contexto atual como objeto imutável."""
    return RequestContext(
        correlation_id=_correlation_id.get(),
        tenant_id=_tenant_id.get(),
        filial_id=_filial_id.get(),
        user_id=_user_id.get(),
        is_superuser=_is_superuser.get(),
    )


def reset_context() -> None:
    """Limpa todo o contexto (útil em workers e testes)."""
    _correlation_id.set(None)
    _tenant_id.set(None)
    _filial_id.set(None)
    _user_id.set(None)
    _is_superuser.set(False)
