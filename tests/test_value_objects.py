"""Testes dos objetos de valor / validadores de domínio."""

from __future__ import annotations

from app.shared.value_objects import (
    format_cnpj,
    format_cpf,
    is_valid_cnpj,
    is_valid_cpf,
    only_digits,
    slugify,
)


def test_cpf_validation() -> None:
    assert is_valid_cpf("529.982.247-25") is True
    assert is_valid_cpf("111.111.111-11") is False
    assert is_valid_cpf("123") is False


def test_cnpj_validation() -> None:
    assert is_valid_cnpj("11.222.333/0001-81") is True
    assert is_valid_cnpj("11.111.111/1111-11") is False
    assert is_valid_cnpj("abc") is False


def test_only_digits() -> None:
    assert only_digits("11.222.333/0001-81") == "11222333000181"


def test_slugify() -> None:
    assert slugify("Locadora São Paulo Ltda.") == "locadora-sao-paulo-ltda"
    assert slugify("  Múltiplos   Espaços ") == "multiplos-espacos"


def test_formatters() -> None:
    assert format_cpf("52998224725") == "529.982.247-25"
    assert format_cnpj("11222333000181") == "11.222.333/0001-81"
