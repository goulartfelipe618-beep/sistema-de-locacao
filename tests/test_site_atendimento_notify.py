"""Notificações de contato do site."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.integracoes.public_schemas import PublicContatoSiteCreate
from app.modules.integracoes.site_atendimento import SiteAtendimentoService


@pytest.mark.asyncio
async def test_registrar_contato_notifica_equipe() -> None:
    session = AsyncMock()
    session.flush = AsyncMock()

    opp = MagicMock()
    opp.id = uuid.uuid4()
    opp.numero = "OPP-001"

    payload = PublicContatoSiteCreate(
        nome="Maria Silva",
        email="maria@example.com",
        telefone="11999998888",
        mensagem="Quero alugar um SUV.",
        origem="chat",
    )

    svc = SiteAtendimentoService(session)
    svc._find_cliente_by_email = AsyncMock(return_value=None)

    with patch.object(SiteAtendimentoService, "_notificar_equipe", new_callable=AsyncMock) as notify:
        with patch("app.modules.integracoes.site_atendimento.FunilService") as funil_cls:
            funil = funil_cls.return_value
            funil.create = AsyncMock(return_value=opp)
            funil.add_interacao = AsyncMock()

            result = await svc.registrar_contato(uuid.uuid4(), payload)

    notify.assert_awaited_once()
    assert result["oportunidade_id"] == str(opp.id)
