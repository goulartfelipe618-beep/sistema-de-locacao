"""Testes do condutor unificado (cliente = quem dirige)."""

from __future__ import annotations

from datetime import date, timedelta

from app.modules.cadastros.condutor import cliente_tem_cnh_valida, refresh_cnh_status
from app.modules.cadastros.models import Cliente
from app.shared.enums import MotoristaCnhStatus


def _cliente(**kwargs) -> Cliente:
    base = dict(
        tenant_id=__import__("uuid").uuid4(),
        nome="João",
        cnh_numero="123456789",
        cnh_categoria="B",
        cnh_validade=date.today() + timedelta(days=365),
        cnh_status=MotoristaCnhStatus.REGULAR,
    )
    base.update(kwargs)
    return Cliente(**base)


def test_cnh_valida_quando_regular_e_dentro_validade() -> None:
    assert cliente_tem_cnh_valida(_cliente()) is True


def test_cnh_invalida_quando_vencida() -> None:
    c = _cliente(cnh_validade=date.today() - timedelta(days=1))
    refresh_cnh_status(c)
    assert c.cnh_status == MotoristaCnhStatus.VENCIDA
    assert cliente_tem_cnh_valida(c) is False


def test_sem_numero_cnh_e_invalida() -> None:
    assert cliente_tem_cnh_valida(_cliente(cnh_numero=None)) is False
