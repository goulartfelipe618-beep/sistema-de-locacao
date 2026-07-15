"""Rotas Web (HTML/Jinja2) do módulo Fiscal (§10)."""

from __future__ import annotations

import io
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_web_permission
from app.core.exceptions import AppError
from app.core.pagination import PageParams
from app.core.templating import render
from app.modules.cadastros.service import ClienteService
from app.modules.fiscal.schemas import (
    AliquotaCreate,
    CancelamentoCreate,
    ImpostoConfigCreate,
    NfeCreate,
    NfeItemInput,
    NfseCreate,
    PrazoCancelamentoCreate,
)
from app.modules.fiscal.service import (
    CancelamentoService,
    ImpostoService,
    NfeService,
    NfseService,
    XmlService,
)
from app.modules.frota.service import VeiculoService
from app.modules.identity.service import AuthenticatedUser
from app.modules.tenants.service import FilialService
from app.shared.enums import (
    CancelamentoEventoTipo,
    FiscalDocumentoTipo,
    FiscalXmlTipo,
    ImpostoTipo,
    NfeOperacao,
    NfeStatus,
    NfseStatus,
    RegimeTributario,
)

router = APIRouter()
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


def _dec(raw: str | None, default: str = "0") -> Decimal:
    value = (raw or default).strip() or default
    if "," in value and "." in value:
        value = value.replace(".", "").replace(",", ".")
    elif "," in value:
        value = value.replace(",", ".")
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("Valor numérico inválido.") from exc


def _uuid(raw: str | None) -> uuid.UUID | None:
    if not raw or not raw.strip():
        return None
    return uuid.UUID(raw.strip())


def _date(raw: str | None) -> date | None:
    if not raw or not raw.strip():
        return None
    return date.fromisoformat(raw.strip())


def _bool(raw: str | None) -> bool:
    return (raw or "").strip().lower() in ("on", "true", "1", "sim")


def _msg(exc: AppError | ValueError) -> str:
    return exc.message if isinstance(exc, AppError) else str(exc)


async def _lookups(session: AsyncSession) -> dict[str, Any]:
    filiais = await FilialService(session).list_filiais(PageParams(page=1, size=100))
    clientes = await ClienteService(session).list_clientes(PageParams(page=1, size=300))
    return {
        "filiais": filiais.items,
        "clientes": clientes.items,
        "filial_nomes": {str(f.id): f.name for f in filiais.items},
        "cliente_nomes": {str(c.id): c.nome for c in clientes.items},
    }


# ================================================================ NFS-e
@router.get("/fiscal/nfse", response_class=HTMLResponse)
async def nfse_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("fiscal.nfse.visualizar"))],
    page: int = 1,
    status: str = "",
) -> HTMLResponse:
    st = NfseStatus(status) if status else None
    result = await NfseService(session).list_items(PageParams(page=page, size=25), status=st)
    lookups = await _lookups(session)
    return render(
        request,
        "fiscal/nfse_list.html",
        {"page_result": result, "title": "NFS-e", "status": status, **lookups},
    )


@router.get("/fiscal/nfse/novo", response_class=HTMLResponse)
async def nfse_novo_form(
    request: Request,
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("fiscal.nfse.criar"))],
) -> HTMLResponse:
    lookups = await _lookups(session)
    return render(request, "fiscal/nfse_form.html", {"title": "Nova NFS-e", "error": None, **lookups})


@router.post("/fiscal/nfse/novo", response_class=HTMLResponse)
async def nfse_novo_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_permission("fiscal.nfse.criar"))],
    filial_id: Annotated[str, Form()],
    valor_servico: Annotated[str, Form()],
    cliente_id: Annotated[str, Form()] = "",
    municipio_nome: Annotated[str, Form()] = "",
    municipio_ibge: Annotated[str, Form()] = "",
    aliquota_iss: Annotated[str, Form()] = "",
    retencao_iss: Annotated[str, Form()] = "",
    discriminacao: Annotated[str, Form()] = "",
    emitir: Annotated[str, Form()] = "",
) -> HTMLResponse:
    lookups = await _lookups(session)
    ctx = {"title": "Nova NFS-e", "error": None, **lookups}
    try:
        svc = NfseService(session)
        nfse = await svc.create(
            current_user.tenant_id,
            NfseCreate(
                filial_id=uuid.UUID(filial_id),
                cliente_id=_uuid(cliente_id),
                valor_servico=_dec(valor_servico),
                municipio_nome=municipio_nome or None,
                municipio_ibge=municipio_ibge or None,
                aliquota_iss=_dec(aliquota_iss) if aliquota_iss.strip() else None,
                retencao_iss=_bool(retencao_iss),
                discriminacao=discriminacao or None,
            ),
        )
        if _bool(emitir):
            await svc.emitir(nfse.id)
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _msg(exc)
        return render(request, "fiscal/nfse_form.html", ctx, status_code=400)
    return RedirectResponse(f"/fiscal/nfse/{nfse.id}", status_code=303)


@router.get("/fiscal/nfse/{nfse_id}", response_class=HTMLResponse)
async def nfse_detalhe(
    request: Request,
    session: SessionDep,
    nfse_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("fiscal.nfse.visualizar"))],
) -> HTMLResponse:
    nfse = await NfseService(session).get(nfse_id)
    lookups = await _lookups(session)
    return render(
        request,
        "fiscal/nfse_detalhe.html",
        {"nfse": nfse, "title": f"NFS-e {nfse.serie}-{nfse.numero}", **lookups},
    )


@router.post("/fiscal/nfse/{nfse_id}/emitir", response_class=HTMLResponse)
async def nfse_emitir(
    request: Request,
    session: SessionDep,
    nfse_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("fiscal.nfse.criar"))],
) -> RedirectResponse:
    try:
        await NfseService(session).emitir(nfse_id)
    except AppError:
        await session.rollback()
    return RedirectResponse(f"/fiscal/nfse/{nfse_id}", status_code=303)


@router.post("/fiscal/nfse/{nfse_id}/cancelar", response_class=HTMLResponse)
async def nfse_cancelar(
    request: Request,
    session: SessionDep,
    nfse_id: uuid.UUID,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_permission("fiscal.nfse.cancelar"))],
    motivo: Annotated[str, Form()],
) -> HTMLResponse:
    try:
        await NfseService(session).cancelar(nfse_id, motivo, user_id=current_user.id)
    except (AppError, ValueError) as exc:
        await session.rollback()
        nfse = await NfseService(session).get(nfse_id)
        lookups = await _lookups(session)
        return render(
            request,
            "fiscal/nfse_detalhe.html",
            {
                "nfse": nfse,
                "title": f"NFS-e {nfse.serie}-{nfse.numero}",
                "error": _msg(exc),
                **lookups,
            },
            status_code=400,
        )
    return RedirectResponse(f"/fiscal/nfse/{nfse_id}", status_code=303)


@router.get("/fiscal/nfse/{nfse_id}/danfse", response_class=HTMLResponse)
async def nfse_danfse(
    request: Request,
    session: SessionDep,
    nfse_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("fiscal.nfse.visualizar"))],
) -> HTMLResponse:
    nfse = await NfseService(session).get(nfse_id)
    lookups = await _lookups(session)
    return render(
        request,
        "fiscal/danfse.html",
        {"nfse": nfse, "title": f"DANFSE {nfse.numero}", **lookups},
    )


# ================================================================ NF-e
@router.get("/fiscal/nfe", response_class=HTMLResponse)
async def nfe_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("fiscal.nfe.visualizar"))],
    page: int = 1,
    status: str = "",
) -> HTMLResponse:
    st = NfeStatus(status) if status else None
    result = await NfeService(session).list_items(PageParams(page=page, size=25), status=st)
    lookups = await _lookups(session)
    return render(
        request,
        "fiscal/nfe_list.html",
        {"page_result": result, "title": "NF-e", "status": status, **lookups},
    )


@router.get("/fiscal/nfe/novo", response_class=HTMLResponse)
async def nfe_novo_form(
    request: Request,
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("fiscal.nfe.criar"))],
) -> HTMLResponse:
    lookups = await _lookups(session)
    veiculos = await VeiculoService(session).list_items(PageParams(page=1, size=300))
    return render(
        request,
        "fiscal/nfe_form.html",
        {
            "title": "Nova NF-e",
            "error": None,
            "operacoes": [o.value for o in NfeOperacao],
            "veiculos": veiculos.items,
            **lookups,
        },
    )


@router.post("/fiscal/nfe/novo", response_class=HTMLResponse)
async def nfe_novo_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_permission("fiscal.nfe.criar"))],
    filial_id: Annotated[str, Form()],
    destinatario_nome: Annotated[str, Form()],
    item_descricao: Annotated[str, Form()],
    item_valor_unitario: Annotated[str, Form()],
    operacao: Annotated[str, Form()] = "venda",
    destinatario_doc: Annotated[str, Form()] = "",
    veiculo_id: Annotated[str, Form()] = "",
    natureza_operacao: Annotated[str, Form()] = "",
    cfop_padrao: Annotated[str, Form()] = "",
    item_quantidade: Annotated[str, Form()] = "1",
    item_ncm: Annotated[str, Form()] = "",
    item_cfop: Annotated[str, Form()] = "",
    item_icms_aliquota: Annotated[str, Form()] = "0",
    item_ipi_aliquota: Annotated[str, Form()] = "0",
    emitir: Annotated[str, Form()] = "",
) -> HTMLResponse:
    lookups = await _lookups(session)
    veiculos = await VeiculoService(session).list_items(PageParams(page=1, size=300))
    ctx = {
        "title": "Nova NF-e",
        "error": None,
        "operacoes": [o.value for o in NfeOperacao],
        "veiculos": veiculos.items,
        **lookups,
    }
    try:
        svc = NfeService(session)
        nfe = await svc.create(
            current_user.tenant_id,
            NfeCreate(
                filial_id=uuid.UUID(filial_id),
                destinatario_nome=destinatario_nome,
                destinatario_doc=destinatario_doc or None,
                operacao=NfeOperacao(operacao),
                veiculo_id=_uuid(veiculo_id),
                natureza_operacao=natureza_operacao or None,
                cfop_padrao=cfop_padrao or None,
                itens=[
                    NfeItemInput(
                        descricao=item_descricao,
                        quantidade=_dec(item_quantidade, "1"),
                        valor_unitario=_dec(item_valor_unitario),
                        ncm=item_ncm or None,
                        cfop=item_cfop or None,
                        icms_aliquota=_dec(item_icms_aliquota),
                        ipi_aliquota=_dec(item_ipi_aliquota),
                    )
                ],
            ),
        )
        if _bool(emitir):
            await svc.emitir(nfe.id)
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _msg(exc)
        return render(request, "fiscal/nfe_form.html", ctx, status_code=400)
    return RedirectResponse(f"/fiscal/nfe/{nfe.id}", status_code=303)


@router.get("/fiscal/nfe/{nfe_id}", response_class=HTMLResponse)
async def nfe_detalhe(
    request: Request,
    session: SessionDep,
    nfe_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("fiscal.nfe.visualizar"))],
) -> HTMLResponse:
    svc = NfeService(session)
    nfe = await svc.get(nfe_id)
    itens = await svc.list_nfe_itens(nfe_id)
    lookups = await _lookups(session)
    return render(
        request,
        "fiscal/nfe_detalhe.html",
        {"nfe": nfe, "itens": itens, "title": f"NF-e {nfe.serie}-{nfe.numero}", **lookups},
    )


@router.post("/fiscal/nfe/{nfe_id}/emitir", response_class=HTMLResponse)
async def nfe_emitir(
    request: Request,
    session: SessionDep,
    nfe_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("fiscal.nfe.criar"))],
) -> RedirectResponse:
    try:
        await NfeService(session).emitir(nfe_id)
    except AppError:
        await session.rollback()
    return RedirectResponse(f"/fiscal/nfe/{nfe_id}", status_code=303)


@router.post("/fiscal/nfe/{nfe_id}/cancelar", response_class=HTMLResponse)
async def nfe_cancelar(
    request: Request,
    session: SessionDep,
    nfe_id: uuid.UUID,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_permission("fiscal.nfe.cancelar"))],
    motivo: Annotated[str, Form()],
) -> HTMLResponse:
    try:
        await NfeService(session).cancelar(nfe_id, motivo, user_id=current_user.id)
    except (AppError, ValueError) as exc:
        await session.rollback()
        svc = NfeService(session)
        nfe = await svc.get(nfe_id)
        itens = await svc.list_nfe_itens(nfe_id)
        lookups = await _lookups(session)
        return render(
            request,
            "fiscal/nfe_detalhe.html",
            {
                "nfe": nfe,
                "itens": itens,
                "title": f"NF-e {nfe.serie}-{nfe.numero}",
                "error": _msg(exc),
                **lookups,
            },
            status_code=400,
        )
    return RedirectResponse(f"/fiscal/nfe/{nfe_id}", status_code=303)


@router.get("/fiscal/nfe/{nfe_id}/danfe", response_class=HTMLResponse)
async def nfe_danfe(
    request: Request,
    session: SessionDep,
    nfe_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("fiscal.nfe.visualizar"))],
) -> HTMLResponse:
    svc = NfeService(session)
    nfe = await svc.get(nfe_id)
    itens = await svc.list_nfe_itens(nfe_id)
    lookups = await _lookups(session)
    return render(
        request,
        "fiscal/danfe.html",
        {"nfe": nfe, "itens": itens, "title": f"DANFE {nfe.numero}", **lookups},
    )


# ================================================================ XML
@router.get("/fiscal/xml", response_class=HTMLResponse)
async def xml_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("fiscal.xml.visualizar"))],
    page: int = 1,
    tipo: str = "",
) -> HTMLResponse:
    t = FiscalXmlTipo(tipo) if tipo else None
    result = await XmlService(session).list_items(PageParams(page=page, size=25), tipo=t)
    lookups = await _lookups(session)
    return render(
        request,
        "fiscal/xml_list.html",
        {
            "page_result": result,
            "title": "XML Fiscal",
            "tipo": tipo,
            "tipos": [t.value for t in FiscalXmlTipo],
            **lookups,
        },
    )


@router.get("/fiscal/xml/importar", response_class=HTMLResponse)
async def xml_import_form(
    request: Request,
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("fiscal.xml.criar"))],
) -> HTMLResponse:
    lookups = await _lookups(session)
    return render(request, "fiscal/xml_import.html", {"title": "Importar XML", "error": None, **lookups})


@router.post("/fiscal/xml/importar", response_class=HTMLResponse)
async def xml_import_post(
    request: Request,
    session: SessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_permission("fiscal.xml.criar"))],
    conteudo_xml: Annotated[str, Form()],
    filial_id: Annotated[str, Form()] = "",
    filename: Annotated[str, Form()] = "",
) -> HTMLResponse:
    lookups = await _lookups(session)
    try:
        await XmlService(session).importar_xml_fornecedor(
            current_user.tenant_id,
            conteudo_xml,
            filial_id=_uuid(filial_id),
            filename=filename or None,
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        return render(
            request,
            "fiscal/xml_import.html",
            {"title": "Importar XML", "error": _msg(exc), **lookups},
            status_code=400,
        )
    return RedirectResponse("/fiscal/xml", status_code=303)


@router.get("/fiscal/xml/exportar", response_class=StreamingResponse)
async def xml_exportar(
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("fiscal.xml.visualizar"))],
    periodo_inicio: str,
    periodo_fim: str,
    tipo: str = "",
) -> StreamingResponse:
    inicio = _date(periodo_inicio) or date.today().replace(day=1)
    fim = _date(periodo_fim) or date.today()
    tipos = [FiscalXmlTipo(tipo)] if tipo else None
    conteudo = await XmlService(session).exportar_lote(inicio, fim, tipos=tipos)
    return StreamingResponse(
        io.BytesIO(conteudo),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="xml_{inicio}_{fim}.zip"'},
    )


@router.get("/fiscal/xml/{xml_id}/download", response_class=StreamingResponse)
async def xml_download(
    session: SessionDep,
    xml_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("fiscal.xml.visualizar"))],
) -> StreamingResponse:
    arquivo = await XmlService(session).get(xml_id)
    return StreamingResponse(
        io.BytesIO(arquivo.conteudo_xml.encode("utf-8")),
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{arquivo.filename}"'},
    )


# ================================================================ Cancelamentos
@router.get("/fiscal/cancelamentos", response_class=HTMLResponse)
async def cancelamentos_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("fiscal.cancelamentos.visualizar"))
    ],
    page: int = 1,
) -> HTMLResponse:
    svc = CancelamentoService(session)
    result = await svc.list_items(PageParams(page=page, size=25))
    prazos = await svc.list_prazos(PageParams(page=1, size=100))
    return render(
        request,
        "fiscal/cancelamentos_list.html",
        {
            "page_result": result,
            "prazos": prazos.items,
            "title": "Cancelamentos e Eventos Fiscais",
            "error": None,
        },
    )


@router.get("/fiscal/cancelamentos/novo", response_class=HTMLResponse)
async def cancelamento_novo_form(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("fiscal.cancelamentos.criar"))
    ],
) -> HTMLResponse:
    return render(
        request,
        "fiscal/cancelamentos_form.html",
        {
            "title": "Novo Evento Fiscal",
            "error": None,
            "documento_tipos": [t.value for t in FiscalDocumentoTipo],
            "evento_tipos": [t.value for t in CancelamentoEventoTipo],
        },
    )


@router.post("/fiscal/cancelamentos/novo", response_class=HTMLResponse)
async def cancelamento_novo_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("fiscal.cancelamentos.criar"))
    ],
    documento_tipo: Annotated[str, Form()],
    documento_id: Annotated[str, Form()],
    motivo: Annotated[str, Form()],
    tipo_evento: Annotated[str, Form()] = "cancelamento",
    justificativa_completa: Annotated[str, Form()] = "",
) -> HTMLResponse:
    ctx = {
        "title": "Novo Evento Fiscal",
        "error": None,
        "documento_tipos": [t.value for t in FiscalDocumentoTipo],
        "evento_tipos": [t.value for t in CancelamentoEventoTipo],
    }
    try:
        svc = CancelamentoService(session)
        evento = await svc.solicitar(
            current_user.tenant_id,
            CancelamentoCreate(
                documento_tipo=FiscalDocumentoTipo(documento_tipo),
                documento_id=uuid.UUID(documento_id),
                tipo_evento=CancelamentoEventoTipo(tipo_evento),
                motivo=motivo,
                justificativa_completa=justificativa_completa or None,
            ),
            user_id=current_user.id,
        )
        await svc.processar(evento.id)
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _msg(exc)
        return render(request, "fiscal/cancelamentos_form.html", ctx, status_code=400)
    return RedirectResponse("/fiscal/cancelamentos", status_code=303)


@router.post("/fiscal/cancelamentos/prazos/novo", response_class=HTMLResponse)
async def cancelamento_prazo_criar(
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("fiscal.cancelamentos.editar"))
    ],
    tipo_documento: Annotated[str, Form()],
    horas_limite: Annotated[str, Form()],
    uf: Annotated[str, Form()] = "",
    municipio_ibge: Annotated[str, Form()] = "",
    descricao: Annotated[str, Form()] = "",
) -> RedirectResponse:
    await CancelamentoService(session).create_prazo(
        current_user.tenant_id,
        PrazoCancelamentoCreate(
            tipo_documento=FiscalDocumentoTipo(tipo_documento),
            horas_limite=int(horas_limite) if horas_limite.strip() else 24,
            uf=uf or None,
            municipio_ibge=municipio_ibge or None,
            descricao=descricao or None,
        ),
    )
    return RedirectResponse("/fiscal/cancelamentos", status_code=303)


# ================================================================ Impostos
@router.get("/fiscal/impostos", response_class=HTMLResponse)
async def impostos_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("fiscal.impostos.visualizar"))],
    page: int = 1,
) -> HTMLResponse:
    result = await ImpostoService(session).list_configs(PageParams(page=page, size=25))
    lookups = await _lookups(session)
    return render(
        request,
        "fiscal/impostos_list.html",
        {
            "page_result": result,
            "title": "Impostos",
            "regimes": [r.value for r in RegimeTributario],
            "error": None,
            **lookups,
        },
    )


@router.post("/fiscal/impostos/novo", response_class=HTMLResponse)
async def imposto_config_criar(
    request: Request,
    session: SessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_permission("fiscal.impostos.criar"))],
    regime: Annotated[str, Form()],
    vigencia_inicio: Annotated[str, Form()],
    filial_id: Annotated[str, Form()] = "",
    nfse_automatica: Annotated[str, Form()] = "",
    vigencia_fim: Annotated[str, Form()] = "",
) -> HTMLResponse:
    try:
        inicio = _date(vigencia_inicio)
        if not inicio:
            raise ValueError("Vigência inicial é obrigatória.")
        await ImpostoService(session).create_config(
            current_user.tenant_id,
            ImpostoConfigCreate(
                filial_id=_uuid(filial_id),
                regime=RegimeTributario(regime),
                vigencia_inicio=inicio,
                vigencia_fim=_date(vigencia_fim),
                nfse_automatica=_bool(nfse_automatica),
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        result = await ImpostoService(session).list_configs(PageParams(page=1, size=25))
        lookups = await _lookups(session)
        return render(
            request,
            "fiscal/impostos_list.html",
            {
                "page_result": result,
                "title": "Impostos",
                "regimes": [r.value for r in RegimeTributario],
                "error": _msg(exc),
                **lookups,
            },
            status_code=400,
        )
    return RedirectResponse("/fiscal/impostos", status_code=303)


@router.get("/fiscal/impostos/{config_id}", response_class=HTMLResponse)
async def imposto_config_detalhe(
    request: Request,
    session: SessionDep,
    config_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("fiscal.impostos.visualizar"))],
) -> HTMLResponse:
    svc = ImpostoService(session)
    config = await svc.get_config(config_id)
    aliquotas = await svc.list_aliquotas(config_id)
    lookups = await _lookups(session)
    return render(
        request,
        "fiscal/impostos_form.html",
        {
            "config": config,
            "aliquotas": aliquotas,
            "title": f"Config Fiscal ({config.regime.value})",
            "error": None,
            "imposto_tipos": [t.value for t in ImpostoTipo],
            **lookups,
        },
    )


@router.post("/fiscal/impostos/{config_id}/aliquotas/novo", response_class=HTMLResponse)
async def imposto_aliquota_criar(
    request: Request,
    session: SessionDep,
    config_id: uuid.UUID,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_permission("fiscal.impostos.criar"))],
    tipo: Annotated[str, Form()],
    aliquota_percentual: Annotated[str, Form()],
    vigencia_inicio: Annotated[str, Form()],
    servico_produto_codigo: Annotated[str, Form()] = "",
    descricao: Annotated[str, Form()] = "",
    retencao: Annotated[str, Form()] = "",
    vigencia_fim: Annotated[str, Form()] = "",
) -> HTMLResponse:
    try:
        inicio = _date(vigencia_inicio)
        if not inicio:
            raise ValueError("Vigência inicial é obrigatória.")
        await ImpostoService(session).create_aliquota(
            current_user.tenant_id,
            AliquotaCreate(
                config_id=config_id,
                tipo=ImpostoTipo(tipo),
                aliquota_percentual=_dec(aliquota_percentual),
                servico_produto_codigo=servico_produto_codigo or None,
                descricao=descricao or None,
                retencao=_bool(retencao),
                vigencia_inicio=inicio,
                vigencia_fim=_date(vigencia_fim),
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        svc = ImpostoService(session)
        config = await svc.get_config(config_id)
        aliquotas = await svc.list_aliquotas(config_id)
        lookups = await _lookups(session)
        return render(
            request,
            "fiscal/impostos_form.html",
            {
                "config": config,
                "aliquotas": aliquotas,
                "title": f"Config Fiscal ({config.regime.value})",
                "error": _msg(exc),
                "imposto_tipos": [t.value for t in ImpostoTipo],
                **lookups,
            },
            status_code=400,
        )
    return RedirectResponse(f"/fiscal/impostos/{config_id}", status_code=303)


@router.post("/fiscal/impostos/aliquotas/{aliquota_id}/excluir", response_class=HTMLResponse)
async def imposto_aliquota_excluir(
    session: SessionDep,
    aliquota_id: uuid.UUID,
    config_id: Annotated[str, Form()],
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("fiscal.impostos.editar"))],
) -> RedirectResponse:
    await ImpostoService(session).delete_aliquota(aliquota_id)
    return RedirectResponse(f"/fiscal/impostos/{config_id}", status_code=303)


@router.get("/fiscal/impostos/apuracao/periodo", response_class=HTMLResponse)
async def impostos_apuracao(
    request: Request,
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("fiscal.impostos.visualizar"))],
    periodo_inicio: str = "",
    periodo_fim: str = "",
) -> HTMLResponse:
    inicio = _date(periodo_inicio) or date.today().replace(day=1)
    fim = _date(periodo_fim) or date.today()
    linhas = await ImpostoService(session).apuracao(inicio, fim)
    return render(
        request,
        "fiscal/impostos_apuracao.html",
        {
            "linhas": linhas,
            "periodo_inicio": inicio,
            "periodo_fim": fim,
            "title": "Apuração de Impostos",
        },
    )
