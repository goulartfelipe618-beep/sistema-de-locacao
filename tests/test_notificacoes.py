"""Testes do módulo Notificações e ViaCEP."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.core.rbac import PERMISSIONS_BY_CODE
from app.modules.notificacoes.adapters.registry import get_email_provider, get_sms_provider
from app.modules.notificacoes.adapters.simulador_email import SimuladorEmail
from app.modules.notificacoes.adapters.simulador_sms import SimuladorSms
from app.modules.notificacoes.schemas import NotificacaoSendInput
from app.shared.enums import NotificacaoCanal, NotificacaoEnvioStatus
from app.shared.viacep import consultar_cep, normalize_cep
from app.web.navigation import build_menu
from tests.test_navigation import _make_user

NOTIF_PERMS = {
    "dashboard.painel.visualizar",
    "notificacoes.inbox.visualizar",
    "notificacoes.envios.visualizar",
}


def test_permissoes_notificacoes_registradas() -> None:
    for code in (
        "notificacoes.inbox.visualizar",
        "notificacoes.envios.visualizar",
        "notificacoes.enviar.criar",
    ):
        assert code in PERMISSIONS_BY_CODE


def test_menu_notificacoes_completo() -> None:
    menu = build_menu(_make_user(NOTIF_PERMS))
    section = next(s for s in menu if s["label"] == "Notificações")
    labels = {item["label"] for item in section["children"]}
    assert labels >= {"Caixa de Entrada", "Histórico de Envios"}


def test_provedores_simulador() -> None:
    assert isinstance(get_email_provider(), SimuladorEmail)
    assert isinstance(get_sms_provider(), SimuladorSms)


def test_simulador_email_nao_levanta() -> None:
    SimuladorEmail().send(to="a@b.com", subject="Teste", body="Olá")


def test_normalize_cep() -> None:
    assert normalize_cep("01310-100") == "01310100"
    assert normalize_cep("01310100") == "01310100"


@pytest.mark.asyncio
async def test_consultar_cep_mock() -> None:
    fake = {
        "cep": "01310100",
        "logradouro": "Av Paulista",
        "complemento": "",
        "bairro": "Bela Vista",
        "localidade": "São Paulo",
        "uf": "SP",
        "ibge": "3550308",
    }
    with patch("app.shared.viacep.httpx.AsyncClient") as mock_client:
        mock_resp = AsyncMock()
        mock_resp.json = lambda: fake
        mock_resp.raise_for_status = lambda: None
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
        result = await consultar_cep("01310-100")
    assert result["cidade"] == "São Paulo"
    assert result["endereco"] == "Av Paulista"


def test_notificacao_send_input_defaults() -> None:
    payload = NotificacaoSendInput(titulo="T", mensagem="M")
    assert payload.canais == [NotificacaoCanal.IN_APP]
    assert payload.async_send is True


def test_enums_notificacao() -> None:
    assert NotificacaoCanal.EMAIL.value == "email"
    assert NotificacaoEnvioStatus.ENVIADO.value == "enviado"
