"""Ganchos de automação e eventos — intermediação."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.automacoes.hooks import fire_regra_event
from app.shared.enums import AutoEventoGatilho

_EVENT_MAP = {
    "intermediacao_pendente": AutoEventoGatilho.INTERMEDIACAO_PENDENTE,
    "intermediacao_aprovada": AutoEventoGatilho.INTERMEDIACAO_APROVADA,
    "intermediacao_rejeitada": AutoEventoGatilho.INTERMEDIACAO_REJEITADA,
}


async def fire_intermediacao_event(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    event_key: str,
    context: dict[str, Any],
) -> None:
    evento = _EVENT_MAP.get(event_key)
    if evento is None:
        return
    await fire_regra_event(session, tenant_id, evento, context)
