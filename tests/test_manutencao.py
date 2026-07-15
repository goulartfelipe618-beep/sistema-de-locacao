"""Testes unitários do módulo Manutenção."""

from __future__ import annotations

from decimal import Decimal

from app.modules.manutencao.service import LIMITE_APROVACAO_OS, OS_TRANSITIONS
from app.shared.enums import OrdemServicoStatus
from app.web.navigation import build_menu
from tests.test_navigation import _make_user


def test_os_transitions_concluida_terminal() -> None:
    assert OS_TRANSITIONS[OrdemServicoStatus.CONCLUIDA] == set()
    assert OS_TRANSITIONS[OrdemServicoStatus.CANCELADA] == set()
    assert OrdemServicoStatus.EM_EXECUCAO in OS_TRANSITIONS[OrdemServicoStatus.ABERTA]


def test_limite_aprovacao_padrao() -> None:
    assert LIMITE_APROVACAO_OS == Decimal("5000")


def test_menu_manutencao_habilitado() -> None:
    perms = {
        "manutencao.os.visualizar",
        "manutencao.preventiva.visualizar",
        "manutencao.corretiva.visualizar",
        "manutencao.peca.visualizar",
        "manutencao.pneu.visualizar",
    }
    menu = build_menu(_make_user(perms))
    section = next(s for s in menu if s["label"] == "Manutenção")
    by_label = {i["label"]: i for i in section["children"]}
    for label, url in (
        ("Ordens de Serviço", "/manutencao/os"),
        ("Preventiva", "/manutencao/preventiva"),
        ("Corretiva", "/manutencao/corretiva"),
        ("Peças / Estoque", "/manutencao/pecas"),
        ("Pneus", "/manutencao/pneus"),
    ):
        assert by_label[label]["enabled"] is True
        assert by_label[label]["url"] == url
