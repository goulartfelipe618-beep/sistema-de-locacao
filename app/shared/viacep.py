"""Consulta de CEP via API pública ViaCEP (§2.1 autopreenchimento de endereço)."""

from __future__ import annotations

import re
from typing import Any

import httpx

from app.core.exceptions import NotFoundError, ValidationError

_CEP_DIGITS = re.compile(r"\D")


def normalize_cep(cep: str) -> str:
    """Retorna apenas os 8 dígitos do CEP."""
    return _CEP_DIGITS.sub("", cep or "")


async def consultar_cep(cep: str) -> dict[str, Any]:
    """Consulta endereço pelo CEP. Levanta ``ValidationError`` ou ``NotFoundError``."""
    digits = normalize_cep(cep)
    if len(digits) != 8:
        raise ValidationError("CEP deve conter 8 dígitos.")

    url = f"https://viacep.com.br/ws/{digits}/json/"
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()

    if data.get("erro"):
        raise NotFoundError("CEP não encontrado.")

    return {
        "cep": digits,
        "endereco": data.get("logradouro") or "",
        "complemento": data.get("complemento") or "",
        "bairro": data.get("bairro") or "",
        "cidade": data.get("localidade") or "",
        "uf": data.get("uf") or "",
        "ibge": data.get("ibge") or "",
    }
