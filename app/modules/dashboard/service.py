"""Serviço de agregação de indicadores do dashboard."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import User
from app.modules.tenants.models import Filial
from app.shared.enums import FilialStatus


@dataclass(slots=True)
class DashboardMetrics:
    """Indicadores exibidos na visão geral do dashboard."""

    total_users: int
    active_users: int
    total_filiais: int
    active_filiais: int


class DashboardService:
    """Calcula os indicadores da visão geral (escopados por tenant via RLS)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _count(self, stmt) -> int:
        return (await self.session.execute(stmt)).scalar_one()

    async def get_overview(self) -> DashboardMetrics:
        """Retorna os indicadores agregados do tenant atual."""
        total_users = await self._count(
            select(func.count()).select_from(User).where(User.deleted_at.is_(None))
        )
        active_users = await self._count(
            select(func.count())
            .select_from(User)
            .where(User.deleted_at.is_(None), User.is_active.is_(True))
        )
        total_filiais = await self._count(
            select(func.count()).select_from(Filial).where(Filial.deleted_at.is_(None))
        )
        active_filiais = await self._count(
            select(func.count())
            .select_from(Filial)
            .where(Filial.deleted_at.is_(None), Filial.status == FilialStatus.ACTIVE)
        )
        return DashboardMetrics(
            total_users=total_users,
            active_users=active_users,
            total_filiais=total_filiais,
            active_filiais=active_filiais,
        )
