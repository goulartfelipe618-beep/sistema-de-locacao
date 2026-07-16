"""Repositório de acesso à trilha de auditoria."""

from __future__ import annotations

import uuid

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Page, PageParams
from app.modules.audit.models import AuditLog


class AuditRepository:
    """Consulta e inserção de registros de auditoria (somente leitura + append)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def add(self, log: AuditLog) -> AuditLog:
        """Adiciona um registro de auditoria à sessão."""
        self.session.add(log)
        return log

    def _query(
        self,
        *,
        tenant_id: uuid.UUID | None,
        action: str | None,
        actions: list[str] | None = None,
        entity: str | None,
        user_id: uuid.UUID | None,
    ) -> Select[tuple[AuditLog]]:
        stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
        if tenant_id is not None:
            stmt = stmt.where(AuditLog.tenant_id == tenant_id)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if actions:
            stmt = stmt.where(AuditLog.action.in_(actions))
        if entity:
            stmt = stmt.where(AuditLog.entity == entity)
        if user_id is not None:
            stmt = stmt.where(AuditLog.user_id == user_id)
        return stmt

    async def paginate(
        self,
        params: PageParams,
        *,
        tenant_id: uuid.UUID | None = None,
        action: str | None = None,
        actions: list[str] | None = None,
        entity: str | None = None,
        user_id: uuid.UUID | None = None,
    ) -> Page[AuditLog]:
        """Lista registros de auditoria paginados e filtrados."""
        stmt = self._query(
            tenant_id=tenant_id,
            action=action,
            actions=actions,
            entity=entity,
            user_id=user_id,
        )
        from sqlalchemy import func  # local para evitar import não usado em outros pontos

        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()
        page_stmt = stmt.offset(params.offset).limit(params.limit)
        items = list((await self.session.execute(page_stmt)).scalars().all())
        return Page(items=items, total=total, page=params.page, size=params.size)
