"""Objetos de valor e validadores de domínio reutilizáveis.

São imutáveis e autovalidados. Utilizados por schemas Pydantic e serviços para
garantir integridade de dados sensíveis (documentos, e-mail, slug).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Annotated

from pydantic import BeforeValidator

_NON_DIGITS = re.compile(r"\D")
_SLUG_INVALID = re.compile(r"[^a-z0-9]+")
_EMAIL_BASIC = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_app_email(value: str) -> str:
    """Valida e-mail de login/cadastro (aceita domínios reservados como ``.local`` em dev)."""
    email = str(value).strip().lower()
    if not _EMAIL_BASIC.match(email):
        raise ValueError("E-mail inválido.")
    return email


AppEmail = Annotated[str, BeforeValidator(normalize_app_email)]


def only_digits(value: str) -> str:
    """Remove todos os caracteres que não são dígitos."""
    return _NON_DIGITS.sub("", value or "")


def slugify(value: str) -> str:
    """Converte um texto em *slug* seguro (minúsculas, sem acentos, com hífens)."""
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = _SLUG_INVALID.sub("-", ascii_text).strip("-")
    return slug


def is_valid_cpf(cpf: str) -> bool:
    """Valida um CPF pelos dígitos verificadores."""
    digits = only_digits(cpf)
    if len(digits) != 11 or digits == digits[0] * 11:
        return False

    def _check_digit(partial: str, factor: int) -> int:
        total = sum(int(d) * (factor - i) for i, d in enumerate(partial))
        remainder = (total * 10) % 11
        return 0 if remainder == 10 else remainder

    first = _check_digit(digits[:9], 10)
    second = _check_digit(digits[:10], 11)
    return first == int(digits[9]) and second == int(digits[10])


def is_valid_cnpj(cnpj: str) -> bool:
    """Valida um CNPJ pelos dígitos verificadores."""
    digits = only_digits(cnpj)
    if len(digits) != 14 or digits == digits[0] * 14:
        return False

    def _check_digit(partial: str, weights: list[int]) -> int:
        total = sum(int(d) * w for d, w in zip(partial, weights, strict=True))
        remainder = total % 11
        return 0 if remainder < 2 else 11 - remainder

    first = _check_digit(digits[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    second = _check_digit(digits[:13], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    return first == int(digits[12]) and second == int(digits[13])


def format_cpf(cpf: str) -> str:
    """Formata um CPF no padrão ``000.000.000-00``."""
    d = only_digits(cpf)
    if len(d) != 11:
        return cpf
    return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"


def format_cnpj(cnpj: str) -> str:
    """Formata um CNPJ no padrão ``00.000.000/0000-00``."""
    d = only_digits(cnpj)
    if len(d) != 14:
        return cnpj
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
