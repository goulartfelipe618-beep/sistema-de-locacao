"""Proteção global: emissão fiscal só quando habilitada no tenant."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError
from app.modules.tenants.models import Tenant

FISCAL_EMISSAO_DISABLED_MSG = (
    "Emissão fiscal desativada nas configurações da empresa. "
    "Para emitir NFS-e ou NF-e, ative em Configurações → Sistema."
)


class FiscalEmissaoDisabledError(BusinessRuleError):
    """Emissão fiscal desligada nas configurações do tenant."""

    code = "fiscal_emissao_disabled"


async def fiscal_emissao_habilitada(session: AsyncSession, tenant_id: uuid.UUID) -> bool:
    tenant = await session.get(Tenant, tenant_id)
    return bool(tenant and tenant.fiscal_emissao_habilitada)


async def assert_fiscal_emissao_habilitada(session: AsyncSession, tenant_id: uuid.UUID) -> None:
    if not await fiscal_emissao_habilitada(session, tenant_id):
        raise FiscalEmissaoDisabledError(FISCAL_EMISSAO_DISABLED_MSG)
