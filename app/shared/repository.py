"""Repositório base genérico (Repository Pattern).

Centraliza operações CRUD comuns sobre modelos que herdam de ``BaseModel``,
respeitando *soft delete* e paginação. Repositórios concretos herdam desta
classe e adicionam consultas específicas do agregado.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Page, PageParams
from app.shared.base_model import BaseModel

ModelT = TypeVar("ModelT", bound=BaseModel)


class BaseRepository(Generic[ModelT]):
    """Repositório genérico assíncrono para um modelo ORM."""

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------ Consultas
    def _base_query(self, *, include_deleted: bool = False) -> Select[tuple[ModelT]]:
        """Query base que, por padrão, oculta registros com *soft delete*."""
        stmt = select(self.model)
        if not include_deleted:
            stmt = stmt.where(self.model.deleted_at.is_(None))
        return stmt

    async def get(self, entity_id: uuid.UUID, *, include_deleted: bool = False) -> ModelT | None:
        """Retorna a entidade pelo ID ou ``None`` se não existir/visível."""
        stmt = self._base_query(include_deleted=include_deleted).where(self.model.id == entity_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self, *, include_deleted: bool = False) -> list[ModelT]:
        """Retorna todas as entidades visíveis (sem paginação)."""
        result = await self.session.execute(self._base_query(include_deleted=include_deleted))
        return list(result.scalars().all())

    async def paginate(
        self,
        params: PageParams,
        *,
        stmt: Select[tuple[ModelT]] | None = None,
    ) -> Page[ModelT]:
        """Executa paginação sobre uma query (ou a query base)."""
        base_stmt = stmt if stmt is not None else self._base_query()

        count_stmt = select(func.count()).select_from(base_stmt.order_by(None).subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        page_stmt = base_stmt.offset(params.offset).limit(params.limit)
        items = list((await self.session.execute(page_stmt)).scalars().all())
        return Page(items=items, total=total, page=params.page, size=params.size)

    # --------------------------------------------------------- Modificações
    def add(self, entity: ModelT) -> ModelT:
        """Registra uma nova entidade na sessão (persistida no commit)."""
        self.session.add(entity)
        return entity

    async def delete(self, entity: ModelT) -> None:
        """Aplica *soft delete* marcando o registro como excluído."""
        entity.deleted_at = datetime.now(tz=UTC)

    async def hard_delete(self, entity: ModelT) -> None:
        """Remove fisicamente o registro (uso restrito e auditado)."""
        await self.session.delete(entity)

    async def flush(self) -> None:
        """Descarrega alterações pendentes para o banco (sem commit)."""
        await self.session.flush()
