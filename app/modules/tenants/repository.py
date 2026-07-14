"""Repositórios do módulo de Empresas/Filiais."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.modules.tenants.models import Filial, Tenant
from app.shared.repository import BaseRepository


class TenantRepository(BaseRepository[Tenant]):
    """Acesso ao registro-mestre de empresas (tenants)."""

    model = Tenant

    async def get_by_slug(self, slug: str) -> Tenant | None:
        stmt = select(Tenant).where(Tenant.slug == slug, Tenant.deleted_at.is_(None))
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_cnpj(self, cnpj: str) -> Tenant | None:
        stmt = select(Tenant).where(Tenant.cnpj == cnpj, Tenant.deleted_at.is_(None))
        return (await self.session.execute(stmt)).scalar_one_or_none()


class FilialRepository(BaseRepository[Filial]):
    """Acesso às filiais/unidades de um tenant (protegido por RLS)."""

    model = Filial

    async def get_by_code(self, tenant_id: uuid.UUID, code: str) -> Filial | None:
        stmt = select(Filial).where(
            Filial.tenant_id == tenant_id,
            Filial.code == code,
            Filial.deleted_at.is_(None),
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_ordered(self) -> list[Filial]:
        stmt = (
            select(Filial)
            .where(Filial.deleted_at.is_(None))
            .order_by(Filial.is_headquarters.desc(), Filial.name)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def clear_headquarters(self, tenant_id: uuid.UUID) -> None:
        """Remove a marcação de matriz de todas as filiais do tenant."""
        for filial in await self.list_ordered():
            if filial.is_headquarters:
                filial.is_headquarters = False
