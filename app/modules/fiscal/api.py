"""API REST do módulo Fiscal (§10)."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import StreamingResponse

from app.core.deps import ApiSessionDep, require_api_permission
from app.core.pagination import PageParams
from app.modules.fiscal.schemas import (
    AliquotaCreate,
    AliquotaRead,
    ApuracaoImpostoLinha,
    CancelamentoCreate,
    CancelamentoRead,
    CancelarInput,
    ImpostoConfigCreate,
    ImpostoConfigRead,
    ImpostoConfigUpdate,
    NfeCreate,
    NfeRead,
    NfseCreate,
    NfseRead,
    PrazoCancelamentoCreate,
    PrazoCancelamentoRead,
    XmlImportInput,
    XmlRead,
)
from app.modules.fiscal.service import (
    CancelamentoService,
    ImpostoService,
    NfeService,
    NfseService,
    XmlService,
)
from app.modules.identity.service import AuthenticatedUser
from app.shared.enums import (
    CancelamentoStatus,
    FiscalDocumentoTipo,
    FiscalXmlDirecao,
    FiscalXmlTipo,
    NfeStatus,
    NfseStatus,
)

router = APIRouter(prefix="/fiscal", tags=["Fiscal"])


def _page_dict(result: Any, read_cls: type) -> dict:
    return {
        "items": [read_cls.model_validate(i) for i in result.items],
        "total": result.total,
        "page": result.page,
        "size": result.size,
        "pages": result.pages,
    }


# ------------------------------------------------------------------ NFS-e
@router.get("/nfse", response_model=dict)
async def api_list_nfse(
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("fiscal.nfse.visualizar"))],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    status_: NfseStatus | None = Query(None, alias="status"),
) -> dict:
    result = await NfseService(session).list_items(PageParams(page=page, size=size), status=status_)
    return _page_dict(result, NfseRead)


@router.post("/nfse", response_model=NfseRead, status_code=status.HTTP_201_CREATED)
async def api_create_nfse(
    payload: NfseCreate,
    session: ApiSessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_api_permission("fiscal.nfse.criar"))],
) -> NfseRead:
    return NfseRead.model_validate(await NfseService(session).create(current_user.tenant_id, payload))


@router.get("/nfse/{nfse_id}", response_model=NfseRead)
async def api_get_nfse(
    nfse_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("fiscal.nfse.visualizar"))],
) -> NfseRead:
    return NfseRead.model_validate(await NfseService(session).get(nfse_id))


@router.post("/nfse/{nfse_id}/emitir", response_model=NfseRead)
async def api_emitir_nfse(
    nfse_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("fiscal.nfse.criar"))],
) -> NfseRead:
    return NfseRead.model_validate(await NfseService(session).emitir(nfse_id))


@router.post("/nfse/{nfse_id}/cancelar", response_model=NfseRead)
async def api_cancelar_nfse(
    nfse_id: uuid.UUID,
    payload: CancelarInput,
    session: ApiSessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_api_permission("fiscal.nfse.cancelar"))],
) -> NfseRead:
    return NfseRead.model_validate(
        await NfseService(session).cancelar(nfse_id, payload.motivo, user_id=current_user.id)
    )


# ------------------------------------------------------------------ NF-e
@router.get("/nfe", response_model=dict)
async def api_list_nfe(
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("fiscal.nfe.visualizar"))],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    status_: NfeStatus | None = Query(None, alias="status"),
) -> dict:
    result = await NfeService(session).list_items(PageParams(page=page, size=size), status=status_)
    return _page_dict(result, NfeRead)


@router.post("/nfe", response_model=NfeRead, status_code=status.HTTP_201_CREATED)
async def api_create_nfe(
    payload: NfeCreate,
    session: ApiSessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_api_permission("fiscal.nfe.criar"))],
) -> NfeRead:
    return NfeRead.model_validate(await NfeService(session).create(current_user.tenant_id, payload))


@router.get("/nfe/{nfe_id}", response_model=NfeRead)
async def api_get_nfe(
    nfe_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("fiscal.nfe.visualizar"))],
) -> NfeRead:
    return NfeRead.model_validate(await NfeService(session).get(nfe_id))


@router.post("/nfe/{nfe_id}/emitir", response_model=NfeRead)
async def api_emitir_nfe(
    nfe_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("fiscal.nfe.criar"))],
) -> NfeRead:
    return NfeRead.model_validate(await NfeService(session).emitir(nfe_id))


@router.post("/nfe/{nfe_id}/cancelar", response_model=NfeRead)
async def api_cancelar_nfe(
    nfe_id: uuid.UUID,
    payload: CancelarInput,
    session: ApiSessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_api_permission("fiscal.nfe.cancelar"))],
) -> NfeRead:
    return NfeRead.model_validate(
        await NfeService(session).cancelar(nfe_id, payload.motivo, user_id=current_user.id)
    )


# ------------------------------------------------------------------ XML
@router.get("/xml", response_model=dict)
async def api_list_xml(
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("fiscal.xml.visualizar"))],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    tipo: FiscalXmlTipo | None = Query(None),
    direcao: FiscalXmlDirecao | None = Query(None),
) -> dict:
    result = await XmlService(session).list_items(
        PageParams(page=page, size=size), tipo=tipo, direcao=direcao
    )
    return _page_dict(result, XmlRead)


@router.post("/xml/importar", response_model=XmlRead, status_code=status.HTTP_201_CREATED)
async def api_importar_xml(
    payload: XmlImportInput,
    session: ApiSessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_api_permission("fiscal.xml.criar"))],
) -> XmlRead:
    arquivo = await XmlService(session).importar_xml_fornecedor(
        current_user.tenant_id,
        payload.conteudo_xml,
        filial_id=payload.filial_id,
        filename=payload.filename,
    )
    return XmlRead.model_validate(arquivo)


@router.get("/xml/exportar", response_class=StreamingResponse)
async def api_exportar_xml(
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("fiscal.xml.visualizar"))],
    periodo_inicio: date = Query(...),
    periodo_fim: date = Query(...),
) -> StreamingResponse:
    import io

    conteudo = await XmlService(session).exportar_lote(periodo_inicio, periodo_fim)
    return StreamingResponse(
        io.BytesIO(conteudo),
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f'attachment; filename="xml_{periodo_inicio}_{periodo_fim}.zip"'
            )
        },
    )


@router.get("/xml/{xml_id}", response_model=XmlRead)
async def api_get_xml(
    xml_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("fiscal.xml.visualizar"))],
) -> XmlRead:
    return XmlRead.model_validate(await XmlService(session).get(xml_id))


# ------------------------------------------------------------------ Cancelamentos
@router.get("/cancelamentos", response_model=dict)
async def api_list_cancelamentos(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("fiscal.cancelamentos.visualizar"))
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    status_: CancelamentoStatus | None = Query(None, alias="status"),
    documento_tipo: FiscalDocumentoTipo | None = Query(None),
) -> dict:
    result = await CancelamentoService(session).list_items(
        PageParams(page=page, size=size), status=status_, documento_tipo=documento_tipo
    )
    return _page_dict(result, CancelamentoRead)


@router.post("/cancelamentos", response_model=CancelamentoRead, status_code=status.HTTP_201_CREATED)
async def api_create_cancelamento(
    payload: CancelamentoCreate,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("fiscal.cancelamentos.criar"))
    ],
) -> CancelamentoRead:
    svc = CancelamentoService(session)
    evento = await svc.solicitar(current_user.tenant_id, payload, user_id=current_user.id)
    await svc.processar(evento.id)
    return CancelamentoRead.model_validate(evento)


@router.get("/prazos", response_model=dict)
async def api_list_prazos(
    session: ApiSessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("fiscal.cancelamentos.visualizar"))
    ],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
) -> dict:
    result = await CancelamentoService(session).list_prazos(PageParams(page=page, size=size))
    return _page_dict(result, PrazoCancelamentoRead)


@router.post("/prazos", response_model=PrazoCancelamentoRead, status_code=status.HTTP_201_CREATED)
async def api_create_prazo(
    payload: PrazoCancelamentoCreate,
    session: ApiSessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_api_permission("fiscal.cancelamentos.editar"))
    ],
) -> PrazoCancelamentoRead:
    return PrazoCancelamentoRead.model_validate(
        await CancelamentoService(session).create_prazo(current_user.tenant_id, payload)
    )


# ------------------------------------------------------------------ Impostos
@router.get("/impostos/configs", response_model=dict)
async def api_list_imposto_configs(
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("fiscal.impostos.visualizar"))],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
) -> dict:
    result = await ImpostoService(session).list_configs(PageParams(page=page, size=size))
    return _page_dict(result, ImpostoConfigRead)


@router.post("/impostos/configs", response_model=ImpostoConfigRead, status_code=status.HTTP_201_CREATED)
async def api_create_imposto_config(
    payload: ImpostoConfigCreate,
    session: ApiSessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_api_permission("fiscal.impostos.criar"))],
) -> ImpostoConfigRead:
    return ImpostoConfigRead.model_validate(
        await ImpostoService(session).create_config(current_user.tenant_id, payload)
    )


@router.put("/impostos/configs/{config_id}", response_model=ImpostoConfigRead)
async def api_update_imposto_config(
    config_id: uuid.UUID,
    payload: ImpostoConfigUpdate,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("fiscal.impostos.editar"))],
) -> ImpostoConfigRead:
    return ImpostoConfigRead.model_validate(
        await ImpostoService(session).update_config(config_id, payload)
    )


@router.get("/impostos/configs/{config_id}/aliquotas", response_model=list[AliquotaRead])
async def api_list_aliquotas(
    config_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("fiscal.impostos.visualizar"))],
) -> list[AliquotaRead]:
    return [AliquotaRead.model_validate(a) for a in await ImpostoService(session).list_aliquotas(config_id)]


@router.post("/impostos/aliquotas", response_model=AliquotaRead, status_code=status.HTTP_201_CREATED)
async def api_create_aliquota(
    payload: AliquotaCreate,
    session: ApiSessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_api_permission("fiscal.impostos.criar"))],
) -> AliquotaRead:
    return AliquotaRead.model_validate(
        await ImpostoService(session).create_aliquota(current_user.tenant_id, payload)
    )


@router.delete(
    "/impostos/aliquotas/{aliquota_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def api_delete_aliquota(
    aliquota_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("fiscal.impostos.editar"))],
) -> Response:
    await ImpostoService(session).delete_aliquota(aliquota_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/impostos/apuracao", response_model=list[ApuracaoImpostoLinha])
async def api_apuracao(
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("fiscal.impostos.visualizar"))],
    periodo_inicio: date = Query(...),
    periodo_fim: date = Query(...),
) -> list[ApuracaoImpostoLinha]:
    linhas = await ImpostoService(session).apuracao(periodo_inicio, periodo_fim)
    return [ApuracaoImpostoLinha(**linha) for linha in linhas]
