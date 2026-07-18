"""Consulta de UFs e municípios via API pública IBGE."""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.core.exceptions import ValidationError

_UFS = (
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
)

_CACHE_TTL_SECONDS = 60 * 60 * 24
_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}


def _cache_get(key: str) -> list[dict[str, Any]] | None:
    row = _cache.get(key)
    if not row:
        return None
    ts, data = row
    if time.time() - ts > _CACHE_TTL_SECONDS:
        _cache.pop(key, None)
        return None
    return data


def _cache_set(key: str, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    _cache[key] = (time.time(), data)
    return data


async def list_ufs() -> list[dict[str, str]]:
    """Retorna UFs brasileiras (sigla + nome)."""
    cached = _cache_get("ufs")
    if cached is not None:
        return cached  # type: ignore[return-value]

    url = "https://servicodados.ibge.gov.br/api/v1/localidades/estados"
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.get(url, params={"orderBy": "nome"})
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        raise ValidationError(f"Serviço IBGE indisponível: {exc}") from exc

    result = [{"sigla": item["sigla"], "nome": item["nome"]} for item in data]
    return _cache_set("ufs", result)  # type: ignore[return-value]


async def list_municipios(uf: str) -> list[dict[str, Any]]:
    """Lista municípios de uma UF (sigla de 2 letras)."""
    sigla = (uf or "").strip().upper()
    if len(sigla) != 2 or sigla not in _UFS:
        raise ValidationError("UF inválida.")

    cache_key = f"municipios:{sigla}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    url = f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{sigla}/municipios"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, params={"orderBy": "nome"})
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        raise ValidationError(f"Serviço IBGE indisponível para {sigla}: {exc}") from exc

    result = [{"id": item["id"], "nome": item["nome"]} for item in data]
    return _cache_set(cache_key, result)
