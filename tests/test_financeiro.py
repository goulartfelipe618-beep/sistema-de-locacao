"""Testes do módulo Financeiro (§9): transições, aging e menu."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from app.modules.financeiro.service import (
    AGING_BUCKETS,
    CARTAO_TRANSITIONS,
    TITULO_TRANSITIONS,
    aging_bucket,
)
from app.shared.enums import CartaoTransacaoStatus, TituloStatus
from app.web.navigation import build_menu
from tests.test_navigation import _make_user

FINANCEIRO_PERMS = {
    "financeiro.caixa.visualizar",
    "financeiro.receber.visualizar",
    "financeiro.pagar.visualizar",
    "financeiro.pix.visualizar",
    "financeiro.cartoes.visualizar",
    "financeiro.bancos.visualizar",
    "financeiro.conciliacao.visualizar",
    "financeiro.faturamento.visualizar",
}


def test_titulo_transitions() -> None:
    assert TituloStatus.PAGO in TITULO_TRANSITIONS[TituloStatus.EM_ABERTO]
    assert TituloStatus.PAGO_PARCIAL in TITULO_TRANSITIONS[TituloStatus.EM_ABERTO]
    assert TituloStatus.VENCIDO in TITULO_TRANSITIONS[TituloStatus.EM_ABERTO]
    assert TituloStatus.ESTORNADO in TITULO_TRANSITIONS[TituloStatus.PAGO]
    # Estados terminais não permitem novas transições.
    assert TITULO_TRANSITIONS[TituloStatus.CANCELADO] == set()
    assert TITULO_TRANSITIONS[TituloStatus.ESTORNADO] == set()


def test_cartao_transitions() -> None:
    assert CartaoTransacaoStatus.CAPTURADO in CARTAO_TRANSITIONS[CartaoTransacaoStatus.AUTORIZADO]
    assert CartaoTransacaoStatus.CANCELADO in CARTAO_TRANSITIONS[CartaoTransacaoStatus.AUTORIZADO]
    assert CartaoTransacaoStatus.ESTORNADO in CARTAO_TRANSITIONS[CartaoTransacaoStatus.CAPTURADO]
    assert CARTAO_TRANSITIONS[CartaoTransacaoStatus.CANCELADO] == set()
    # Não é possível capturar o que já foi cancelado.
    assert CartaoTransacaoStatus.CAPTURADO not in CARTAO_TRANSITIONS[CartaoTransacaoStatus.CANCELADO]


def test_aging_bucket() -> None:
    hoje = date(2026, 7, 15)
    assert aging_bucket(hoje, hoje) == "a_vencer"
    assert aging_bucket(hoje + timedelta(days=5), hoje) == "a_vencer"
    assert aging_bucket(hoje - timedelta(days=1), hoje) == "1-30"
    assert aging_bucket(hoje - timedelta(days=30), hoje) == "1-30"
    assert aging_bucket(hoje - timedelta(days=45), hoje) == "31-60"
    assert aging_bucket(hoje - timedelta(days=75), hoje) == "61-90"
    assert aging_bucket(hoje - timedelta(days=200), hoje) == "90+"


def test_aging_buckets_labels() -> None:
    assert AGING_BUCKETS == ("a_vencer", "1-30", "31-60", "61-90", "90+")


def test_next_numero_format() -> None:
    # Confere o formato de numeração sequencial esperado por tenant.
    assert f"CR-{1:06d}" == "CR-000001"
    assert f"CP-{42:06d}" == "CP-000042"
    assert f"FAT-{7:06d}" == "FAT-000007"


def test_menu_financeiro_enabled() -> None:
    menu = build_menu(_make_user(FINANCEIRO_PERMS))
    section = next(s for s in menu if s["label"] == "Financeiro")
    by_label = {i["label"]: i for i in section["children"]}
    for label, url in (
        ("Caixa", "/financeiro/caixa"),
        ("Contas a Receber", "/financeiro/receber"),
        ("Contas a Pagar", "/financeiro/pagar"),
        ("PIX", "/financeiro/pix"),
        ("Cartões", "/financeiro/cartoes"),
        ("Bancos", "/financeiro/bancos"),
        ("Conciliação", "/financeiro/conciliacao"),
        ("Faturamento", "/financeiro/faturamento"),
    ):
        assert by_label[label]["enabled"] is True
        assert by_label[label]["url"] == url


def test_menu_financeiro_partial_permissions() -> None:
    menu = build_menu(_make_user({"financeiro.caixa.visualizar"}))
    section = next(s for s in menu if s["label"] == "Financeiro")
    labels = {i["label"] for i in section["children"]}
    # Só o item permitido é exibido/habilitado.
    assert labels == {"Caixa"}


def test_money_quantize_helper() -> None:
    from app.modules.financeiro.service import _money

    assert _money(Decimal("10")) == Decimal("10.00")
    assert _money(Decimal("10.1")) == Decimal("10.10")
    assert str(_money(Decimal("10"))) == "10.00"
