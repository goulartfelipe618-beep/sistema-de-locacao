"""Camada de acesso a dados: engine assíncrono, sessões e Unit of Work.

Responsabilidades:
    * Criar o engine assíncrono (asyncpg) com pool configurável.
    * Fornecer a dependência :func:`get_db_session` (Unit of Work por requisição).
    * Aplicar o contexto multiempresa no PostgreSQL para o Row-Level Security,
      definindo a variável de sessão ``app.current_tenant_id``.
    * Expor a classe :class:`UnitOfWork` para uso fora do ciclo de requisição
      (workers Celery, scripts, seeds).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.context import get_tenant_id
from app.core.logging import get_logger

logger = get_logger(__name__)


def _uses_supabase_transaction_pooler() -> bool:
    return ":6543" in settings.supabase_db_url and "pooler.supabase.com" in settings.supabase_db_url


def _asyncpg_connect_args() -> dict[str, int]:
    """Desabilita cache de prepared statements no PgBouncer transaction mode."""
    if _uses_supabase_transaction_pooler():
        return {"statement_cache_size": 0}
    return {}


def _engine_kwargs() -> dict:
    """Parâmetros do engine SQLAlchemy."""
    kwargs: dict = {
        "echo": settings.db_echo,
        "pool_pre_ping": True,
        "pool_recycle": 1800,
        "future": True,
        "connect_args": _asyncpg_connect_args(),
        "pool_size": settings.db_pool_size,
        "max_overflow": settings.db_max_overflow,
    }
    if _uses_supabase_transaction_pooler():
        kwargs["poolclass"] = NullPool
        kwargs.pop("pool_size", None)
        kwargs.pop("max_overflow", None)
        kwargs.pop("pool_recycle", None)
    return kwargs


# Engine assíncrono único da aplicação.
engine = create_async_engine(settings.database_url_async, **_engine_kwargs())

# Fábrica de sessões assíncronas. ``expire_on_commit=False`` permite usar os
# objetos após o commit (útil para renderização de templates/serialização).
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Nome da variável de sessão do PostgreSQL usada pelas políticas de RLS.
_TENANT_GUC = "app.current_tenant_id"


async def _apply_tenant_context(session: AsyncSession, tenant_id: uuid.UUID | None) -> None:
    """Define, na conexão, o tenant corrente para o Row-Level Security.

    Um valor vazio faz as políticas de RLS não retornarem nenhuma linha de
    tabelas multiempresa (comportamento seguro por padrão). Se ``enforce_rls``
    estiver desligado (somente testes controlados), o GUC ainda é setado, mas
    a ausência de valor não altera o comportamento das policies no banco.
    """
    value = str(tenant_id) if tenant_id else ""
    if settings.enforce_rls and not value:
        logger.debug("Sessão aberta sem tenant_id; RLS isolara dados multiempresa.")
    await session.execute(
        text(f"SELECT set_config('{_TENANT_GUC}', :value, false)"),
        {"value": value},
    )


async def _reset_tenant_context(session: AsyncSession) -> None:
    """Limpa o tenant da conexão antes de devolvê-la ao pool (anti-vazamento).

    Se a limpeza falhar, a conexão é invalidada no pool para impedir vazamento
    residual do GUC entre requisições.
    """
    try:
        await session.execute(text(f"SELECT set_config('{_TENANT_GUC}', '', false)"))
    except Exception:  # pragma: no cover - conexão pode já estar inválida
        logger.warning("Falha ao resetar GUC de tenant; invalidando conexão do pool.")
        try:
            await session.invalidate()
        except Exception:
            logger.debug("Não foi possível invalidar a conexão após falha de reset.")


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Dependência FastAPI que fornece uma sessão transacional por requisição.

    Implementa o padrão *Unit of Work* por requisição: aplica o contexto de
    tenant, entrega a sessão, confirma (commit) em caso de sucesso e desfaz
    (rollback) em caso de erro, sempre limpando o contexto e fechando a sessão.
    """
    session = async_session_factory()
    try:
        await _apply_tenant_context(session, get_tenant_id())
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await _reset_tenant_context(session)
        await session.close()


class UnitOfWork:
    """Unit of Work explícito para contextos fora de requisição HTTP.

    Uso típico::

        async with UnitOfWork(tenant_id=tid) as uow:
            repo = UserRepository(uow.session)
            ...  # operações
            # commit automático ao sair sem exceção
    """

    def __init__(self, tenant_id: uuid.UUID | None = None) -> None:
        self._tenant_id = tenant_id if tenant_id is not None else get_tenant_id()
        self._session: AsyncSession | None = None

    @property
    def session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("UnitOfWork não iniciado. Use 'async with UnitOfWork() as uow'.")
        return self._session

    async def __aenter__(self) -> UnitOfWork:
        self._session = async_session_factory()
        await _apply_tenant_context(self._session, self._tenant_id)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        assert self._session is not None
        try:
            if exc_type is None:
                await self._session.commit()
            else:
                await self._session.rollback()
        finally:
            await _reset_tenant_context(self._session)
            await self._session.close()
            self._session = None

    async def commit(self) -> None:
        """Confirma a transação atual sem encerrar a unidade de trabalho."""
        await self.session.commit()

    async def rollback(self) -> None:
        """Desfaz a transação atual."""
        await self.session.rollback()


@asynccontextmanager
async def session_scope(tenant_id: uuid.UUID | None = None) -> AsyncIterator[AsyncSession]:
    """Atalho de context manager que entrega diretamente a sessão do UoW."""
    async with UnitOfWork(tenant_id=tenant_id) as uow:
        yield uow.session


async def check_database() -> bool:
    """Verifica a conectividade com o banco (usado no health check de readiness)."""
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # pragma: no cover - depende de infraestrutura
        logger.warning("Health check do banco falhou: %s", exc)
        return False


async def dispose_engine() -> None:
    """Encerra o pool de conexões (chamado no shutdown da aplicação)."""
    await engine.dispose()
