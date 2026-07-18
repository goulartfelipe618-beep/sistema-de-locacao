"""Rotas Web de dados de referência (IBGE, CEP) para formulários autenticados."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.core.deps import require_web_user
from app.core.exceptions import AppError
from app.modules.identity.service import AuthenticatedUser
from app.shared.ibge import list_municipios, list_ufs
from app.shared.viacep import consultar_cep

router = APIRouter()


@router.get("/referencia/ibge/ufs")
async def referencia_ibge_ufs(
    _user: Annotated[AuthenticatedUser, Depends(require_web_user)],
) -> JSONResponse:
    """Lista UFs (qualquer usuário autenticado — usado em formulários de endereço)."""
    try:
        return JSONResponse(content=await list_ufs())
    except AppError:
        raise
    except Exception as exc:
        return JSONResponse(
            status_code=502,
            content={"error": f"Não foi possível consultar o IBGE: {exc}"},
        )


@router.get("/referencia/ibge/municipios/{uf}")
async def referencia_ibge_municipios(
    uf: str,
    _user: Annotated[AuthenticatedUser, Depends(require_web_user)],
) -> JSONResponse:
    """Lista municípios por UF (qualquer usuário autenticado)."""
    try:
        return JSONResponse(content=await list_municipios(uf))
    except AppError as exc:
        return JSONResponse(status_code=exc.status_code, content={"error": exc.message})
    except Exception as exc:
        return JSONResponse(
            status_code=502,
            content={"error": f"Não foi possível consultar municípios: {exc}"},
        )


@router.get("/referencia/cep/{cep}")
async def referencia_cep(
    cep: str,
    _user: Annotated[AuthenticatedUser, Depends(require_web_user)],
) -> JSONResponse:
    """Consulta CEP via ViaCEP (qualquer usuário autenticado)."""
    try:
        return JSONResponse(content=await consultar_cep(cep))
    except AppError as exc:
        return JSONResponse(status_code=exc.status_code, content={"error": exc.message})
    except Exception as exc:
        return JSONResponse(
            status_code=502,
            content={"error": f"Não foi possível consultar o CEP: {exc}"},
        )
