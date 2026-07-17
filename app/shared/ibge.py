"""Consulta de UFs e municípios via API pública IBGE."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.exceptions import ValidationError

_UFS = (
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
)


async def list_ufs() -> list[dict[str, str]]:
    """Retorna UFs brasileiras (sigla + nome)."""
    url = "https://servicodados.ibge.gov.br/api/v1/localidades/estados"
    async with httpx.AsyncClient(timeout=8.0) as client:
        response = await client.get(url, params={"orderBy": "nome"})
        response.raise_for_status()
        data = response.json()

    return [{"sigla": item["sigla"], "nome": item["nome"]} for item in data]


async def list_municipios(uf: str) -> list[dict[str, Any]]:
    """Lista municípios de uma UF (sigla de 2 letras)."""
    sigla = (uf or "").strip().upper()
    if len(sigla) != 2 or sigla not in _UFS:
        raise ValidationError("UF inválida.")

    url = f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{sigla}/municipios"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, params={"orderBy": "nome"})
        response.raise_for_status()
        data = response.json()

    return [{"id": item["id"], "nome": item["nome"]} for item in data]
