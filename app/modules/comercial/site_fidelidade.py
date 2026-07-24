"""Payload público do programa de fidelidade para o site."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.comercial.service import FidelidadeService


async def fidelidade_programa_public(session: AsyncSession, tenant_id: uuid.UUID) -> dict:
    svc = FidelidadeService(session)
    regra = await svc.get_regra()
    if regra is None or not regra.ativo:
        return {"ativo": False, "regra": None, "tiers": []}

    tiers = await svc.list_tiers()
    tiers_sorted = sorted(tiers, key=lambda row: (row.ordem, row.pontos_minimos))
    return {
        "ativo": True,
        "regra": {
            "nome": regra.nome,
            "pontos_por_real": float(regra.pontos_por_real),
            "pontos_por_diaria": float(regra.pontos_por_diaria),
            "valor_por_ponto": float(regra.valor_por_ponto),
            "validade_meses": regra.validade_meses,
        },
        "tiers": [
            {
                "nome": tier.nome,
                "pontos_minimos": tier.pontos_minimos,
                "beneficio": tier.beneficio_descricao,
                "ordem": tier.ordem,
            }
            for tier in tiers_sorted
        ],
    }
