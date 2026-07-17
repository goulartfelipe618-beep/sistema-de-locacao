"""Utilitários públicos da API (IBGE, etc.)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import ApiSessionDep, require_api_permission
from app.modules.identity.service import AuthenticatedUser
from app.shared.ibge import list_municipios, list_ufs

router = APIRouter(prefix="/util", tags=["Utilitários"])


@router.get("/ibge/ufs")
async def api_ibge_ufs(
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("cadastros.cliente.visualizar"))],
    _session: ApiSessionDep,
) -> list[dict[str, str]]:
    return await list_ufs()


@router.get("/ibge/municipios/{uf}")
async def api_ibge_municipios(
    uf: str,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("cadastros.cliente.visualizar"))],
    _session: ApiSessionDep,
) -> list[dict[str, str | int]]:
    return await list_municipios(uf)
