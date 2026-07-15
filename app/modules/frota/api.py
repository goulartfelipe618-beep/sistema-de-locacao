"""API REST do módulo Frota."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel, Field

from app.core.deps import ApiSessionDep, require_api_permission
from app.core.pagination import PageParams
from app.modules.frota.schemas import (
    AcessorioCreate,
    AcessorioRead,
    AcessorioUpdate,
    CategoriaCreate,
    CategoriaRead,
    CategoriaUpdate,
    CombustivelCreate,
    CombustivelRead,
    CombustivelUpdate,
    DocumentoCreate,
    DocumentoRead,
    DocumentoUpdate,
    MarcaCreate,
    MarcaRead,
    MarcaUpdate,
    ModeloCreate,
    ModeloRead,
    ModeloUpdate,
    TelemetriaDispositivoRead,
    TelemetriaDispositivoUpsert,
    TelemetriaEventoCreate,
    TelemetriaEventoRead,
    VeiculoAcessorioLink,
    VeiculoAcessorioRead,
    VeiculoCreate,
    VeiculoFotoCreate,
    VeiculoFotoRead,
    VeiculoRead,
    VeiculoUpdate,
)
from app.modules.frota.service import (
    AcessoriosService,
    CategoriasService,
    CombustiveisService,
    DocumentoService,
    FotoService,
    MarcasService,
    ModelosService,
    TelemetriaService,
    VeiculoService,
)
from app.modules.identity.service import AuthenticatedUser
from app.shared.enums import DocumentoVeiculoStatus, VeiculoStatus

router = APIRouter(prefix="/frota", tags=["Frota"])


def _page_dict(result: Any, read_cls: type) -> dict:
    return {
        "items": [read_cls.model_validate(i) for i in result.items],
        "total": result.total,
        "page": result.page,
        "size": result.size,
        "pages": result.pages,
    }


class _MotivoPayload(BaseModel):
    motivo: str = Field(min_length=1)


class _LiberarPayload(BaseModel):
    motivo: str | None = None


# ------------------------------------------------------------------ Veículos
@router.get("/veiculos", response_model=dict)
async def api_list_veiculos(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.veiculo.visualizar"))
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    q: str | None = None,
    status: VeiculoStatus | None = None,
) -> dict:
    result = await VeiculoService(session).list_items(
        PageParams(page=page, size=size), search=q, status=status
    )
    return _page_dict(result, VeiculoRead)


@router.post("/veiculos", response_model=VeiculoRead, status_code=status.HTTP_201_CREATED)
async def api_create_veiculo(
    payload: VeiculoCreate,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.veiculo.criar"))
    ],
) -> VeiculoRead:
    item = await VeiculoService(session).create(current_user.tenant_id, payload)
    return VeiculoRead.model_validate(item)


@router.get("/veiculos/{item_id}", response_model=VeiculoRead)
async def api_get_veiculo(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.veiculo.visualizar"))
    ],
) -> VeiculoRead:
    return VeiculoRead.model_validate(await VeiculoService(session).get(item_id))


@router.patch("/veiculos/{item_id}", response_model=VeiculoRead)
async def api_update_veiculo(
    item_id: uuid.UUID,
    payload: VeiculoUpdate,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.veiculo.editar"))
    ],
) -> VeiculoRead:
    return VeiculoRead.model_validate(await VeiculoService(session).update(item_id, payload))


@router.post("/veiculos/{item_id}/bloquear", response_model=VeiculoRead)
async def api_bloquear_veiculo(
    item_id: uuid.UUID,
    payload: _MotivoPayload,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.veiculo.bloquear"))
    ],
) -> VeiculoRead:
    return VeiculoRead.model_validate(
        await VeiculoService(session).bloquear(item_id, payload.motivo)
    )


@router.post("/veiculos/{item_id}/baixar", response_model=VeiculoRead)
async def api_baixar_veiculo(
    item_id: uuid.UUID,
    payload: _MotivoPayload,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.veiculo.baixar"))
    ],
) -> VeiculoRead:
    return VeiculoRead.model_validate(
        await VeiculoService(session).baixar(item_id, payload.motivo)
    )


@router.post("/veiculos/{item_id}/liberar", response_model=VeiculoRead)
async def api_liberar_veiculo(
    item_id: uuid.UUID,
    payload: _LiberarPayload,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.veiculo.bloquear"))
    ],
) -> VeiculoRead:
    return VeiculoRead.model_validate(
        await VeiculoService(session).liberar(item_id, payload.motivo)
    )


@router.get("/veiculos/{item_id}/acessorios", response_model=dict)
async def api_list_veiculo_acessorios(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.veiculo.visualizar"))
    ],
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
) -> dict:
    result = await VeiculoService(session).list_acessorios(
        PageParams(page=page, size=size), item_id
    )
    return _page_dict(result, VeiculoAcessorioRead)


@router.post(
    "/veiculos/{item_id}/acessorios",
    response_model=VeiculoAcessorioRead,
    status_code=status.HTTP_201_CREATED,
)
async def api_link_veiculo_acessorio(
    item_id: uuid.UUID,
    payload: VeiculoAcessorioLink,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.veiculo.editar"))
    ],
) -> VeiculoAcessorioRead:
    item = await VeiculoService(session).link_acessorio(
        current_user.tenant_id, item_id, payload
    )
    return VeiculoAcessorioRead.model_validate(item)


@router.delete(
    "/veiculos/{item_id}/acessorios/{acessorio_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def api_unlink_veiculo_acessorio(
    item_id: uuid.UUID,
    acessorio_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.veiculo.editar"))
    ],
) -> Response:
    await VeiculoService(session).unlink_acessorio(item_id, acessorio_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/veiculos/{item_id}/fotos", response_model=dict)
async def api_list_veiculo_fotos(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.veiculo.visualizar"))
    ],
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
) -> dict:
    result = await FotoService(session).list_by_veiculo(PageParams(page=page, size=size), item_id)
    return _page_dict(result, VeiculoFotoRead)


@router.post(
    "/veiculos/{item_id}/fotos",
    response_model=VeiculoFotoRead,
    status_code=status.HTTP_201_CREATED,
)
async def api_add_veiculo_foto(
    item_id: uuid.UUID,
    payload: VeiculoFotoCreate,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.veiculo.editar"))
    ],
) -> VeiculoFotoRead:
    item = await FotoService(session).add(current_user.tenant_id, item_id, payload)
    return VeiculoFotoRead.model_validate(item)


@router.delete(
    "/veiculos/{item_id}/fotos/{foto_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def api_remove_veiculo_foto(
    item_id: uuid.UUID,
    foto_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.veiculo.editar"))
    ],
) -> Response:
    await FotoService(session).remove(foto_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --------------------------------------------------------------- Categorias
@router.get("/categorias", response_model=dict)
async def api_list_categorias(
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.categoria.visualizar"))
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    q: str | None = None,
) -> dict:
    await CategoriasService(session).ensure_defaults(current_user.tenant_id)
    result = await CategoriasService(session).list_items(PageParams(page=page, size=size), search=q)
    return _page_dict(result, CategoriaRead)


@router.post("/categorias", response_model=CategoriaRead, status_code=status.HTTP_201_CREATED)
async def api_create_categoria(
    payload: CategoriaCreate,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.categoria.criar"))
    ],
) -> CategoriaRead:
    item = await CategoriasService(session).create(current_user.tenant_id, payload)
    return CategoriaRead.model_validate(item)


@router.get("/categorias/{item_id}", response_model=CategoriaRead)
async def api_get_categoria(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.categoria.visualizar"))
    ],
) -> CategoriaRead:
    return CategoriaRead.model_validate(await CategoriasService(session).get(item_id))


@router.patch("/categorias/{item_id}", response_model=CategoriaRead)
async def api_update_categoria(
    item_id: uuid.UUID,
    payload: CategoriaUpdate,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.categoria.editar"))
    ],
) -> CategoriaRead:
    return CategoriaRead.model_validate(await CategoriasService(session).update(item_id, payload))


# --------------------------------------------------------------------- Marcas
@router.get("/marcas", response_model=dict)
async def api_list_marcas(
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.marca.visualizar"))
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    q: str | None = None,
) -> dict:
    await MarcasService(session).ensure_defaults(current_user.tenant_id)
    result = await MarcasService(session).list_items(PageParams(page=page, size=size), search=q)
    return _page_dict(result, MarcaRead)


@router.post("/marcas", response_model=MarcaRead, status_code=status.HTTP_201_CREATED)
async def api_create_marca(
    payload: MarcaCreate,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.marca.criar"))
    ],
) -> MarcaRead:
    item = await MarcasService(session).create(current_user.tenant_id, payload)
    return MarcaRead.model_validate(item)


@router.get("/marcas/{item_id}", response_model=MarcaRead)
async def api_get_marca(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.marca.visualizar"))
    ],
) -> MarcaRead:
    return MarcaRead.model_validate(await MarcasService(session).get(item_id))


@router.patch("/marcas/{item_id}", response_model=MarcaRead)
async def api_update_marca(
    item_id: uuid.UUID,
    payload: MarcaUpdate,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.marca.editar"))
    ],
) -> MarcaRead:
    return MarcaRead.model_validate(await MarcasService(session).update(item_id, payload))


# ------------------------------------------------------------------- Modelos
@router.get("/modelos", response_model=dict)
async def api_list_modelos(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.modelo.visualizar"))
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    q: str | None = None,
    marca_id: uuid.UUID | None = None,
) -> dict:
    result = await ModelosService(session).list_items(
        PageParams(page=page, size=size), search=q, marca_id=marca_id
    )
    return _page_dict(result, ModeloRead)


@router.post("/modelos", response_model=ModeloRead, status_code=status.HTTP_201_CREATED)
async def api_create_modelo(
    payload: ModeloCreate,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.modelo.criar"))
    ],
) -> ModeloRead:
    item = await ModelosService(session).create(current_user.tenant_id, payload)
    return ModeloRead.model_validate(item)


@router.get("/modelos/{item_id}", response_model=ModeloRead)
async def api_get_modelo(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.modelo.visualizar"))
    ],
) -> ModeloRead:
    return ModeloRead.model_validate(await ModelosService(session).get(item_id))


@router.patch("/modelos/{item_id}", response_model=ModeloRead)
async def api_update_modelo(
    item_id: uuid.UUID,
    payload: ModeloUpdate,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.modelo.editar"))
    ],
) -> ModeloRead:
    return ModeloRead.model_validate(await ModelosService(session).update(item_id, payload))


# -------------------------------------------------------------- Combustíveis
@router.get("/combustiveis", response_model=dict)
async def api_list_combustiveis(
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.combustivel.visualizar"))
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    q: str | None = None,
) -> dict:
    await CombustiveisService(session).ensure_defaults(current_user.tenant_id)
    result = await CombustiveisService(session).list_items(
        PageParams(page=page, size=size), search=q
    )
    return _page_dict(result, CombustivelRead)


@router.post("/combustiveis", response_model=CombustivelRead, status_code=status.HTTP_201_CREATED)
async def api_create_combustivel(
    payload: CombustivelCreate,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.combustivel.criar"))
    ],
) -> CombustivelRead:
    item = await CombustiveisService(session).create(current_user.tenant_id, payload)
    return CombustivelRead.model_validate(item)


@router.get("/combustiveis/{item_id}", response_model=CombustivelRead)
async def api_get_combustivel(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.combustivel.visualizar"))
    ],
) -> CombustivelRead:
    return CombustivelRead.model_validate(await CombustiveisService(session).get(item_id))


@router.patch("/combustiveis/{item_id}", response_model=CombustivelRead)
async def api_update_combustivel(
    item_id: uuid.UUID,
    payload: CombustivelUpdate,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.combustivel.editar"))
    ],
) -> CombustivelRead:
    return CombustivelRead.model_validate(
        await CombustiveisService(session).update(item_id, payload)
    )


# ----------------------------------------------------------------- Acessórios
@router.get("/acessorios", response_model=dict)
async def api_list_acessorios(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.acessorio.visualizar"))
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    q: str | None = None,
) -> dict:
    result = await AcessoriosService(session).list_items(PageParams(page=page, size=size), search=q)
    return _page_dict(result, AcessorioRead)


@router.post("/acessorios", response_model=AcessorioRead, status_code=status.HTTP_201_CREATED)
async def api_create_acessorio(
    payload: AcessorioCreate,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.acessorio.criar"))
    ],
) -> AcessorioRead:
    item = await AcessoriosService(session).create(current_user.tenant_id, payload)
    return AcessorioRead.model_validate(item)


@router.get("/acessorios/{item_id}", response_model=AcessorioRead)
async def api_get_acessorio(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.acessorio.visualizar"))
    ],
) -> AcessorioRead:
    return AcessorioRead.model_validate(await AcessoriosService(session).get(item_id))


@router.patch("/acessorios/{item_id}", response_model=AcessorioRead)
async def api_update_acessorio(
    item_id: uuid.UUID,
    payload: AcessorioUpdate,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.acessorio.editar"))
    ],
) -> AcessorioRead:
    return AcessorioRead.model_validate(await AcessoriosService(session).update(item_id, payload))


# -------------------------------------------------------------- Documentação
@router.get("/documentacao", response_model=dict)
async def api_list_documentacao(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.documentacao.visualizar"))
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    veiculo_id: uuid.UUID | None = None,
    status: DocumentoVeiculoStatus | None = None,
) -> dict:
    result = await DocumentoService(session).list_items(
        PageParams(page=page, size=size), veiculo_id=veiculo_id, status=status
    )
    return _page_dict(result, DocumentoRead)


@router.get("/documentacao/vencimentos", response_model=dict)
async def api_documentacao_vencimentos(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.documentacao.visualizar"))
    ],
    days: int = Query(30, ge=1),
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
) -> dict:
    result = await DocumentoService(session).list_vencimentos(
        PageParams(page=page, size=size), days=days
    )
    return _page_dict(result, DocumentoRead)


@router.post("/documentacao", response_model=DocumentoRead, status_code=status.HTTP_201_CREATED)
async def api_create_documento(
    payload: DocumentoCreate,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.documentacao.criar"))
    ],
) -> DocumentoRead:
    item = await DocumentoService(session).create(current_user.tenant_id, payload)
    return DocumentoRead.model_validate(item)


@router.get("/documentacao/{item_id}", response_model=DocumentoRead)
async def api_get_documento(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.documentacao.visualizar"))
    ],
) -> DocumentoRead:
    return DocumentoRead.model_validate(await DocumentoService(session).get(item_id))


@router.patch("/documentacao/{item_id}", response_model=DocumentoRead)
async def api_update_documento(
    item_id: uuid.UUID,
    payload: DocumentoUpdate,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.documentacao.editar"))
    ],
) -> DocumentoRead:
    return DocumentoRead.model_validate(await DocumentoService(session).update(item_id, payload))


# --------------------------------------------------------------- Telemetria
@router.get("/telemetria/dispositivos", response_model=dict)
async def api_list_telemetria_dispositivos(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.telemetria.visualizar"))
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
) -> dict:
    result = await TelemetriaService(session).list_dispositivos(PageParams(page=page, size=size))
    return _page_dict(result, TelemetriaDispositivoRead)


@router.post(
    "/telemetria/dispositivos",
    response_model=TelemetriaDispositivoRead,
    status_code=status.HTTP_201_CREATED,
)
async def api_upsert_telemetria_dispositivo(
    payload: TelemetriaDispositivoUpsert,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.telemetria.criar"))
    ],
) -> TelemetriaDispositivoRead:
    item = await TelemetriaService(session).upsert_dispositivo(current_user.tenant_id, payload)
    return TelemetriaDispositivoRead.model_validate(item)


@router.get("/telemetria/dispositivos/{item_id}", response_model=TelemetriaDispositivoRead)
async def api_get_telemetria_dispositivo(
    item_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.telemetria.visualizar"))
    ],
) -> TelemetriaDispositivoRead:
    return TelemetriaDispositivoRead.model_validate(
        await TelemetriaService(session).get_dispositivo(item_id)
    )


@router.get("/telemetria/eventos", response_model=dict)
async def api_list_telemetria_eventos(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.telemetria.visualizar"))
    ],
    veiculo_id: uuid.UUID,
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
) -> dict:
    result = await TelemetriaService(session).list_eventos(
        PageParams(page=page, size=size), veiculo_id
    )
    return _page_dict(result, TelemetriaEventoRead)


@router.post(
    "/telemetria/eventos",
    response_model=TelemetriaEventoRead,
    status_code=status.HTTP_201_CREATED,
)
async def api_register_telemetria_evento(
    payload: TelemetriaEventoCreate,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("frota.telemetria.criar"))
    ],
) -> TelemetriaEventoRead:
    item = await TelemetriaService(session).register_evento(current_user.tenant_id, payload)
    return TelemetriaEventoRead.model_validate(item)
