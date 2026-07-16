"""Testes do módulo Integrações (§12)."""

from __future__ import annotations

import hashlib
import hmac
import json

from app.core.crypto import decrypt_secret, encrypt_secret
from app.core.rbac import PERMISSIONS_BY_CODE
from app.modules.integracoes.adapters.simulador_credito import SimuladorCredito
from app.modules.integracoes.adapters.simulador_pagamento import SimuladorPagamento
from app.modules.integracoes.adapters.simulador_transito import SimuladorTransito
from app.shared.enums import IntegracaoTipo, PagamentoWebhookEvento
from app.web.navigation import build_menu
from tests.test_navigation import _make_user

INT_PERMS = {
    "dashboard.painel.visualizar",
    "integracoes.pagamentos.visualizar",
    "integracoes.transito.visualizar",
    "integracoes.credito.visualizar",
    "integracoes.telemetria.visualizar",
    "integracoes.api_publica.visualizar",
}


def test_permissoes_integracoes_registradas() -> None:
    for code in (
        "integracoes.pagamentos.visualizar",
        "integracoes.transito.consultar",
        "integracoes.api_publica.criar",
    ):
        assert code in PERMISSIONS_BY_CODE


def test_menu_integracoes_completo() -> None:
    menu = build_menu(_make_user(INT_PERMS))
    section = next(s for s in menu if s["label"] == "Integrações")
    labels = {item["label"] for item in section["children"]}
    assert labels >= {"Pagamentos", "Trânsito (DETRAN)", "Crédito", "Telemetria", "API Pública"}


def test_crypto_roundtrip() -> None:
    raw = "client_secret_123"
    enc = encrypt_secret(raw)
    assert decrypt_secret(enc) == raw


def test_simulador_pagamento_webhook() -> None:
    gw = SimuladorPagamento()
    body = json.dumps({"evento": "pago", "txid": "ABC123", "valor": "50.00"}).encode()
    secret = "segredo"
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert gw.validar_assinatura(body=body, signature=sig, secret=secret)
    payload = gw.parse_webhook(body=body)
    assert payload.evento == PagamentoWebhookEvento.PAGO
    assert payload.referencia_externa == "ABC123"


def test_simulador_transito_multas() -> None:
    multas = SimuladorTransito().consultar_multas_veiculo(
        placa="ABC1D23", renavam=None, credenciais={}
    )
    assert len(multas) == 1
    assert multas[0].orgao == "DETRAN-SIM"


def test_simulador_credito_score() -> None:
    r = SimuladorCredito().consultar_score(
        documento="12345678901", tipo_pessoa="pf", credenciais={}
    )
    assert 300 <= r.score <= 900


def test_integracao_tipo_enum() -> None:
    assert IntegracaoTipo.PAGAMENTOS.value == "pagamentos"
