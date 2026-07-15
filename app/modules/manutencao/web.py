"""Rotas Web (HTML/Jinja2) do módulo Manutenção."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_web_permission
from app.core.exceptions import AppError
from app.core.pagination import PageParams
from app.core.templating import render
from app.modules.cadastros.service_extra import FornecedorService
from app.modules.frota.service import VeiculoService
from app.modules.identity.service import AuthenticatedUser
from app.modules.manutencao.schemas import (
    EstoqueAjuste,
    EstoqueEntrada,
    EstoqueSaida,
    OrdemServicoAprovar,
    OrdemServicoCancelar,
    OrdemServicoConcluir,
    OrdemServicoCreate,
    OrdemServicoFotoCreate,
    OrdemServicoItemCreate,
    OrdemServicoStatusChange,
    OrdemServicoUpdate,
    PecaCreate,
    PecaUpdate,
    PlanoChecklistItemCreate,
    PlanoPreventivoCreate,
    PlanoPreventivoUpdate,
    PneuCreate,
    PneuDescartar,
    PneuInstalar,
    PneuInspecionar,
    PneuRodizio,
    PneuUpdate,
    VeiculoPlanoLink,
)
from app.modules.manutencao.service import (
    EstoqueService,
    OrdemServicoService,
    OsFotoRepository,
    OsItemRepository,
    PecaService,
    PlanoChecklistRepository,
    PlanoPreventivoService,
    PneuHistoricoRepository,
    PneuService,
    VeiculoPlanoRepository,
)
from app.modules.tenants.service import FilialService
from app.shared.enums import (
    CadastroStatus,
    CorretivaCausa,
    CorretivaResponsavel,
    OrdemServicoItemTipo,
    OrdemServicoOrigem,
    OrdemServicoStatus,
    OrdemServicoTipo,
    PneuPosicao,
    PneuStatus,
)

router = APIRouter()
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


def _dec(raw: str | None, default: str = "0") -> Decimal:
    value = (raw or default).strip() or default
    if "," in value:
        value = value.replace(".", "").replace(",", ".")
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("Valor numérico inválido.") from exc


def _date(raw: str | None) -> date | None:
    if not raw or not raw.strip():
        return None
    return date.fromisoformat(raw.strip())


def _uuid(raw: str | None) -> uuid.UUID | None:
    if not raw or not raw.strip():
        return None
    return uuid.UUID(raw.strip())


def _app_error_message(exc: AppError | ValueError) -> str:
    return exc.message if isinstance(exc, AppError) else str(exc)


def _checklist_from_text(raw: str) -> list[PlanoChecklistItemCreate]:
    items: list[PlanoChecklistItemCreate] = []
    for idx, line in enumerate(raw.splitlines()):
        text = line.strip()
        if text:
            items.append(PlanoChecklistItemCreate(item_descricao=text, ordem=idx))
    return items


def _checklist_to_text(items: list) -> str:
    return "\n".join(i.item_descricao for i in sorted(items, key=lambda x: x.ordem))


async def _os_lookups(session: AsyncSession) -> dict[str, Any]:
    veiculos = await VeiculoService(session).list_items(PageParams(page=1, size=300))
    fornecedores = await FornecedorService(session).list_items(PageParams(page=1, size=200))
    filiais = await FilialService(session).list_filiais(PageParams(page=1, size=100))
    pecas = await PecaService(session).list_items(PageParams(page=1, size=300))
    return {
        "veiculos": veiculos.items,
        "fornecedores": fornecedores.items,
        "filiais": filiais.items,
        "pecas": pecas.items,
        "veiculo_placas": {str(v.id): v.placa for v in veiculos.items},
        "fornecedor_nomes": {str(f.id): f.nome for f in fornecedores.items},
    }


async def _os_extras(session: AsyncSession, os_id: uuid.UUID) -> dict[str, Any]:
    item_repo = OsItemRepository(session)
    foto_repo = OsFotoRepository(session)
    itens = list((await session.execute(item_repo.list_by_os(os_id))).scalars().all())
    fotos = list((await session.execute(foto_repo.list_by_os(os_id))).scalars().all())
    pecas = await PecaService(session).list_items(PageParams(page=1, size=300))
    peca_nomes = {str(p.id): f"{p.codigo} — {p.nome}" for p in pecas.items}
    return {"itens": itens, "fotos": fotos, "peca_nomes": peca_nomes}


# ================================================================ Ordens de Serviço
@router.get("/manutencao/os", response_class=HTMLResponse)
async def os_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.os.visualizar"))
    ],
    page: int = 1,
    q: str = "",
    status: str = "",
    tipo: str = "",
) -> HTMLResponse:
    st = OrdemServicoStatus(status) if status else None
    tp = OrdemServicoTipo(tipo) if tipo else None
    result = await OrdemServicoService(session).list_items(
        PageParams(page=page, size=25), search=q or None, status=st, tipo=tp
    )
    lookups = await _os_lookups(session)
    return render(
        request,
        "manutencao/os_list.html",
        {
            "page_result": result,
            "q": q,
            "status": status,
            "tipo": tipo,
            "title": "Ordens de Serviço",
            **lookups,
        },
    )


@router.get("/manutencao/os/novo", response_class=HTMLResponse)
async def os_new_form(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.os.criar"))
    ],
    tipo: str = "preventiva",
) -> HTMLResponse:
    lookups = await _os_lookups(session)
    return render(
        request,
        "manutencao/os_form.html",
        {
            "os": None,
            "error": None,
            "title": "Nova OS",
            "action": "/manutencao/os/novo",
            "default_tipo": tipo,
            **lookups,
        },
    )


@router.post("/manutencao/os/novo", response_class=HTMLResponse)
async def os_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.os.criar"))
    ],
    veiculo_id: Annotated[str, Form()],
    tipo: Annotated[str, Form()],
    fornecedor_id: Annotated[str, Form()] = "",
    filial_id: Annotated[str, Form()] = "",
    km_entrada: Annotated[str, Form()] = "",
    data_previsao: Annotated[str, Form()] = "",
    garantia_dias: Annotated[str, Form()] = "",
    garantia_km: Annotated[str, Form()] = "",
    causa: Annotated[str, Form()] = "",
    responsavel_custo: Annotated[str, Form()] = "",
    observacoes: Annotated[str, Form()] = "",
) -> HTMLResponse:
    lookups = await _os_lookups(session)
    ctx = {
        "os": None,
        "error": None,
        "title": "Nova OS",
        "action": "/manutencao/os/novo",
        "default_tipo": tipo,
        **lookups,
    }
    try:
        data = OrdemServicoCreate(
            veiculo_id=uuid.UUID(veiculo_id),
            tipo=OrdemServicoTipo(tipo),
            origem=OrdemServicoOrigem.MANUAL,
            fornecedor_id=_uuid(fornecedor_id),
            filial_id=_uuid(filial_id),
            km_entrada=int(km_entrada) if km_entrada.strip() else None,
            data_previsao=_date(data_previsao),
            garantia_dias=int(garantia_dias) if garantia_dias.strip() else None,
            garantia_km=int(garantia_km) if garantia_km.strip() else None,
            causa=CorretivaCausa(causa) if causa else None,
            responsavel_custo=CorretivaResponsavel(responsavel_custo) if responsavel_custo else None,
            observacoes=observacoes or None,
        )
        item = await OrdemServicoService(session).create(current_user.tenant_id, data)
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _app_error_message(exc)
        return render(request, "manutencao/os_form.html", ctx, status_code=400)
    return RedirectResponse(f"/manutencao/os/{item.id}/editar", status_code=303)


@router.get("/manutencao/os/{os_id}/editar", response_class=HTMLResponse)
async def os_edit_form(
    request: Request,
    session: SessionDep,
    os_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.os.editar"))
    ],
) -> HTMLResponse:
    os_item = await OrdemServicoService(session).get(os_id)
    lookups = await _os_lookups(session)
    extras = await _os_extras(session, os_id)
    return render(
        request,
        "manutencao/os_form.html",
        {
            "os": os_item,
            "error": None,
            "title": f"OS {os_item.numero}",
            "action": f"/manutencao/os/{os_id}/editar",
            "default_tipo": os_item.tipo.value,
            **lookups,
            **extras,
        },
    )


@router.post("/manutencao/os/{os_id}/editar", response_class=HTMLResponse)
async def os_update(
    request: Request,
    session: SessionDep,
    os_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.os.editar"))
    ],
    fornecedor_id: Annotated[str, Form()] = "",
    filial_id: Annotated[str, Form()] = "",
    km_entrada: Annotated[str, Form()] = "",
    km_saida: Annotated[str, Form()] = "",
    data_previsao: Annotated[str, Form()] = "",
    garantia_dias: Annotated[str, Form()] = "",
    garantia_km: Annotated[str, Form()] = "",
    causa: Annotated[str, Form()] = "",
    responsavel_custo: Annotated[str, Form()] = "",
    observacoes: Annotated[str, Form()] = "",
) -> HTMLResponse:
    lookups = await _os_lookups(session)
    extras = await _os_extras(session, os_id)
    try:
        await OrdemServicoService(session).update(
            os_id,
            OrdemServicoUpdate(
                fornecedor_id=_uuid(fornecedor_id),
                filial_id=_uuid(filial_id),
                km_entrada=int(km_entrada) if km_entrada.strip() else None,
                km_saida=int(km_saida) if km_saida.strip() else None,
                data_previsao=_date(data_previsao),
                garantia_dias=int(garantia_dias) if garantia_dias.strip() else None,
                garantia_km=int(garantia_km) if garantia_km.strip() else None,
                causa=CorretivaCausa(causa) if causa else None,
                responsavel_custo=CorretivaResponsavel(responsavel_custo) if responsavel_custo else None,
                observacoes=observacoes or None,
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        os_item = await OrdemServicoService(session).get(os_id)
        return render(
            request,
            "manutencao/os_form.html",
            {
                "os": os_item,
                "error": _app_error_message(exc),
                "title": f"OS {os_item.numero}",
                "action": f"/manutencao/os/{os_id}/editar",
                "default_tipo": os_item.tipo.value,
                **lookups,
                **extras,
            },
            status_code=400,
        )
    return RedirectResponse(f"/manutencao/os/{os_id}/editar", status_code=303)


@router.post("/manutencao/os/{os_id}/itens", response_class=HTMLResponse)
async def os_add_item(
    session: SessionDep,
    os_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.os.editar"))
    ],
    tipo_item: Annotated[str, Form()],
    descricao: Annotated[str, Form()],
    peca_id: Annotated[str, Form()] = "",
    quantidade: Annotated[str, Form()] = "1",
    valor_unitario: Annotated[str, Form()] = "0",
    observacoes: Annotated[str, Form()] = "",
) -> RedirectResponse:
    await OrdemServicoService(session).add_item(
        current_user.tenant_id,
        os_id,
        OrdemServicoItemCreate(
            tipo_item=OrdemServicoItemTipo(tipo_item),
            descricao=descricao,
            peca_id=_uuid(peca_id),
            quantidade=_dec(quantidade),
            valor_unitario=_dec(valor_unitario),
            observacoes=observacoes or None,
        ),
    )
    return RedirectResponse(f"/manutencao/os/{os_id}/editar", status_code=303)


@router.post("/manutencao/os/{os_id}/itens/{item_id}/remover", response_class=HTMLResponse)
async def os_remove_item(
    session: SessionDep,
    os_id: uuid.UUID,
    item_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.os.editar"))
    ],
) -> RedirectResponse:
    await OrdemServicoService(session).remove_item(os_id, item_id)
    return RedirectResponse(f"/manutencao/os/{os_id}/editar", status_code=303)


@router.post("/manutencao/os/{os_id}/fotos", response_class=HTMLResponse)
async def os_add_foto(
    session: SessionDep,
    os_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.os.editar"))
    ],
    storage_key: Annotated[str, Form()],
    legenda: Annotated[str, Form()] = "",
    fase: Annotated[str, Form()] = "",
) -> RedirectResponse:
    await OrdemServicoService(session).add_foto(
        current_user.tenant_id,
        os_id,
        OrdemServicoFotoCreate(
            storage_key=storage_key,
            legenda=legenda or None,
            fase=fase or None,
        ),
    )
    return RedirectResponse(f"/manutencao/os/{os_id}/editar", status_code=303)


@router.post("/manutencao/os/{os_id}/fotos/{foto_id}/remover", response_class=HTMLResponse)
async def os_remove_foto(
    session: SessionDep,
    os_id: uuid.UUID,
    foto_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.os.editar"))
    ],
) -> RedirectResponse:
    await OrdemServicoService(session).remove_foto(os_id, foto_id)
    return RedirectResponse(f"/manutencao/os/{os_id}/editar", status_code=303)


@router.post("/manutencao/os/{os_id}/status", response_class=HTMLResponse)
async def os_change_status(
    session: SessionDep,
    os_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.os.editar"))
    ],
    novo_status: Annotated[str, Form()],
) -> RedirectResponse:
    await OrdemServicoService(session).change_status(
        os_id, OrdemServicoStatusChange(status=OrdemServicoStatus(novo_status))
    )
    return RedirectResponse(f"/manutencao/os/{os_id}/editar", status_code=303)


@router.post("/manutencao/os/{os_id}/concluir", response_class=HTMLResponse)
async def os_concluir(
    session: SessionDep,
    os_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.os.editar"))
    ],
    km_saida: Annotated[str, Form()] = "",
) -> RedirectResponse:
    await OrdemServicoService(session).concluir(
        os_id,
        OrdemServicoConcluir(km_saida=int(km_saida) if km_saida.strip() else None),
    )
    return RedirectResponse(f"/manutencao/os/{os_id}/editar", status_code=303)


@router.post("/manutencao/os/{os_id}/cancelar", response_class=HTMLResponse)
async def os_cancelar(
    session: SessionDep,
    os_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.os.editar"))
    ],
    motivo: Annotated[str, Form()] = "",
) -> RedirectResponse:
    await OrdemServicoService(session).cancelar(
        os_id, OrdemServicoCancelar(motivo=motivo or None)
    )
    return RedirectResponse(f"/manutencao/os/{os_id}/editar", status_code=303)


@router.post("/manutencao/os/{os_id}/aprovar", response_class=HTMLResponse)
async def os_aprovar(
    session: SessionDep,
    os_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.os.aprovar"))
    ],
) -> RedirectResponse:
    await OrdemServicoService(session).aprovar(
        os_id, OrdemServicoAprovar(aprovado_por_user_id=current_user.id)
    )
    return RedirectResponse(f"/manutencao/os/{os_id}/editar", status_code=303)


# ================================================================ Preventiva
async def _preventiva_lookups(session: AsyncSession) -> dict[str, Any]:
    veiculos = await VeiculoService(session).list_items(PageParams(page=1, size=300))
    fornecedores = await FornecedorService(session).list_items(PageParams(page=1, size=200))
    return {
        "veiculos": veiculos.items,
        "fornecedores": fornecedores.items,
        "veiculo_placas": {str(v.id): v.placa for v in veiculos.items},
    }


@router.get("/manutencao/preventiva", response_class=HTMLResponse)
async def preventiva_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser,
        Depends(require_web_permission("manutencao.preventiva.visualizar")),
    ],
    page: int = 1,
    q: str = "",
) -> HTMLResponse:
    svc = PlanoPreventivoService(session)
    result = await svc.list_items(PageParams(page=page, size=25), search=q or None)
    proximas = await svc.proximas_preventivas(PageParams(page=1, size=50))
    lookups = await _preventiva_lookups(session)
    return render(
        request,
        "manutencao/preventiva_list.html",
        {
            "page_result": result,
            "proximas": proximas,
            "q": q,
            "title": "Planos Preventivos",
            **lookups,
        },
    )


@router.get("/manutencao/preventiva/novo", response_class=HTMLResponse)
async def preventiva_new_form(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.preventiva.criar"))
    ],
) -> HTMLResponse:
    lookups = await _preventiva_lookups(session)
    return render(
        request,
        "manutencao/preventiva_form.html",
        {
            "plano": None,
            "checklist_text": "",
            "vinculos": [],
            "error": None,
            "title": "Novo Plano Preventivo",
            "action": "/manutencao/preventiva/novo",
            **lookups,
        },
    )


@router.post("/manutencao/preventiva/novo", response_class=HTMLResponse)
async def preventiva_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.preventiva.criar"))
    ],
    nome: Annotated[str, Form()],
    descricao: Annotated[str, Form()] = "",
    intervalo_km: Annotated[str, Form()] = "",
    intervalo_meses: Annotated[str, Form()] = "",
    fornecedor_sugerido_id: Annotated[str, Form()] = "",
    custo_estimado: Annotated[str, Form()] = "0",
    automatico: Annotated[str, Form()] = "",
    status: Annotated[str, Form()] = "active",
    checklist: Annotated[str, Form()] = "",
) -> HTMLResponse:
    lookups = await _preventiva_lookups(session)
    ctx = {
        "plano": None,
        "checklist_text": checklist,
        "vinculos": [],
        "error": None,
        "title": "Novo Plano Preventivo",
        "action": "/manutencao/preventiva/novo",
        **lookups,
    }
    try:
        item = await PlanoPreventivoService(session).create(
            current_user.tenant_id,
            PlanoPreventivoCreate(
                nome=nome,
                descricao=descricao or None,
                intervalo_km=int(intervalo_km) if intervalo_km.strip() else None,
                intervalo_meses=int(intervalo_meses) if intervalo_meses.strip() else None,
                fornecedor_sugerido_id=_uuid(fornecedor_sugerido_id),
                custo_estimado=_dec(custo_estimado),
                automatico=bool(automatico),
                status=CadastroStatus(status),
                checklist=_checklist_from_text(checklist),
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _app_error_message(exc)
        return render(request, "manutencao/preventiva_form.html", ctx, status_code=400)
    return RedirectResponse(f"/manutencao/preventiva/{item.id}/editar", status_code=303)


@router.get("/manutencao/preventiva/{plano_id}/editar", response_class=HTMLResponse)
async def preventiva_edit_form(
    request: Request,
    session: SessionDep,
    plano_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.preventiva.editar"))
    ],
) -> HTMLResponse:
    plano = await PlanoPreventivoService(session).get(plano_id)
    checklist_repo = PlanoChecklistRepository(session)
    checklist = list(
        (await session.execute(
            checklist_repo._base_query().where(
                checklist_repo.model.plano_id == plano_id
            ).order_by(checklist_repo.model.ordem)
        )).scalars().all()
    )
    vp_repo = VeiculoPlanoRepository(session)
    vinculos = list(
        (await session.execute(vp_repo.list_by_plano(plano_id))).scalars().all()
    )
    lookups = await _preventiva_lookups(session)
    return render(
        request,
        "manutencao/preventiva_form.html",
        {
            "plano": plano,
            "checklist_text": _checklist_to_text(checklist),
            "vinculos": vinculos,
            "error": None,
            "title": f"Plano — {plano.nome}",
            "action": f"/manutencao/preventiva/{plano_id}/editar",
            **lookups,
        },
    )


@router.post("/manutencao/preventiva/{plano_id}/editar", response_class=HTMLResponse)
async def preventiva_update(
    request: Request,
    session: SessionDep,
    plano_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.preventiva.editar"))
    ],
    nome: Annotated[str, Form()],
    descricao: Annotated[str, Form()] = "",
    intervalo_km: Annotated[str, Form()] = "",
    intervalo_meses: Annotated[str, Form()] = "",
    fornecedor_sugerido_id: Annotated[str, Form()] = "",
    custo_estimado: Annotated[str, Form()] = "0",
    automatico: Annotated[str, Form()] = "",
    status: Annotated[str, Form()] = "active",
    checklist: Annotated[str, Form()] = "",
) -> HTMLResponse:
    lookups = await _preventiva_lookups(session)
    vp_repo = VeiculoPlanoRepository(session)
    vinculos = list(
        (await session.execute(vp_repo.list_by_plano(plano_id))).scalars().all()
    )
    try:
        await PlanoPreventivoService(session).update(
            plano_id,
            PlanoPreventivoUpdate(
                nome=nome,
                descricao=descricao or None,
                intervalo_km=int(intervalo_km) if intervalo_km.strip() else None,
                intervalo_meses=int(intervalo_meses) if intervalo_meses.strip() else None,
                fornecedor_sugerido_id=_uuid(fornecedor_sugerido_id),
                custo_estimado=_dec(custo_estimado),
                automatico=bool(automatico),
                status=CadastroStatus(status),
                checklist=_checklist_from_text(checklist),
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        plano = await PlanoPreventivoService(session).get(plano_id)
        checklist_repo = PlanoChecklistRepository(session)
        checklist_items = list(
            (await session.execute(
                checklist_repo._base_query().where(
                    checklist_repo.model.plano_id == plano_id
                ).order_by(checklist_repo.model.ordem)
            )).scalars().all()
        )
        return render(
            request,
            "manutencao/preventiva_form.html",
            {
                "plano": plano,
                "checklist_text": checklist,
                "vinculos": vinculos,
                "error": _app_error_message(exc),
                "title": f"Plano — {plano.nome}",
                "action": f"/manutencao/preventiva/{plano_id}/editar",
                **lookups,
            },
            status_code=400,
        )
    return RedirectResponse(f"/manutencao/preventiva/{plano_id}/editar", status_code=303)


@router.post("/manutencao/preventiva/{plano_id}/vincular", response_class=HTMLResponse)
async def preventiva_vincular(
    session: SessionDep,
    plano_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.preventiva.editar"))
    ],
    veiculo_id: Annotated[str, Form()],
    km_ultima_execucao: Annotated[str, Form()] = "",
    data_ultima_execucao: Annotated[str, Form()] = "",
) -> RedirectResponse:
    await PlanoPreventivoService(session).link_veiculo(
        current_user.tenant_id,
        plano_id,
        VeiculoPlanoLink(
            veiculo_id=uuid.UUID(veiculo_id),
            km_ultima_execucao=int(km_ultima_execucao) if km_ultima_execucao.strip() else None,
            data_ultima_execucao=_date(data_ultima_execucao),
        ),
    )
    return RedirectResponse(f"/manutencao/preventiva/{plano_id}/editar", status_code=303)


@router.post(
    "/manutencao/preventiva/{plano_id}/vincular/{veiculo_id}/remover",
    response_class=HTMLResponse,
)
async def preventiva_desvincular(
    session: SessionDep,
    plano_id: uuid.UUID,
    veiculo_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.preventiva.editar"))
    ],
) -> RedirectResponse:
    await PlanoPreventivoService(session).unlink_veiculo(plano_id, veiculo_id)
    return RedirectResponse(f"/manutencao/preventiva/{plano_id}/editar", status_code=303)


@router.post("/manutencao/preventiva/gerar-os/{veiculo_plano_id}", response_class=HTMLResponse)
async def preventiva_gerar_os(
    session: SessionDep,
    veiculo_plano_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.preventiva.criar"))
    ],
) -> RedirectResponse:
    os_item = await PlanoPreventivoService(session).gerar_os_preventiva(
        current_user.tenant_id, veiculo_plano_id
    )
    return RedirectResponse(f"/manutencao/os/{os_item.id}/editar", status_code=303)


# ================================================================== Corretiva
@router.get("/manutencao/corretiva", response_class=HTMLResponse)
async def corretiva_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser,
        Depends(require_web_permission("manutencao.corretiva.visualizar")),
    ],
    page: int = 1,
    q: str = "",
    status: str = "",
) -> HTMLResponse:
    st = OrdemServicoStatus(status) if status else None
    result = await OrdemServicoService(session).list_corretivas(
        PageParams(page=page, size=25), search=q or None, status=st
    )
    lookups = await _os_lookups(session)
    return render(
        request,
        "manutencao/corretiva_list.html",
        {
            "page_result": result,
            "q": q,
            "status": status,
            "title": "Manutenção Corretiva",
            **lookups,
        },
    )


@router.get("/manutencao/corretiva/novo", response_class=HTMLResponse)
async def corretiva_new_form(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.corretiva.criar"))
    ],
) -> HTMLResponse:
    lookups = await _os_lookups(session)
    return render(
        request,
        "manutencao/os_form.html",
        {
            "os": None,
            "error": None,
            "title": "Nova Corretiva",
            "action": "/manutencao/corretiva/novo",
            "default_tipo": "corretiva",
            "corretiva_mode": True,
            **lookups,
        },
    )


@router.post("/manutencao/corretiva/novo", response_class=HTMLResponse)
async def corretiva_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.corretiva.criar"))
    ],
    veiculo_id: Annotated[str, Form()],
    fornecedor_id: Annotated[str, Form()] = "",
    filial_id: Annotated[str, Form()] = "",
    km_entrada: Annotated[str, Form()] = "",
    data_previsao: Annotated[str, Form()] = "",
    causa: Annotated[str, Form()] = "",
    responsavel_custo: Annotated[str, Form()] = "",
    observacoes: Annotated[str, Form()] = "",
) -> HTMLResponse:
    lookups = await _os_lookups(session)
    ctx = {
        "os": None,
        "error": None,
        "title": "Nova Corretiva",
        "action": "/manutencao/corretiva/novo",
        "default_tipo": "corretiva",
        "corretiva_mode": True,
        **lookups,
    }
    try:
        data = OrdemServicoCreate(
            veiculo_id=uuid.UUID(veiculo_id),
            tipo=OrdemServicoTipo.CORRETIVA,
            origem=OrdemServicoOrigem.MANUAL,
            fornecedor_id=_uuid(fornecedor_id),
            filial_id=_uuid(filial_id),
            km_entrada=int(km_entrada) if km_entrada.strip() else None,
            data_previsao=_date(data_previsao),
            causa=CorretivaCausa(causa) if causa else None,
            responsavel_custo=CorretivaResponsavel(responsavel_custo) if responsavel_custo else None,
            observacoes=observacoes or None,
        )
        item = await OrdemServicoService(session).create(current_user.tenant_id, data)
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _app_error_message(exc)
        return render(request, "manutencao/os_form.html", ctx, status_code=400)
    return RedirectResponse(f"/manutencao/os/{item.id}/editar", status_code=303)


# ======================================================================= Peças
@router.get("/manutencao/pecas", response_class=HTMLResponse)
async def pecas_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.peca.visualizar"))
    ],
    page: int = 1,
    q: str = "",
    tab: str = "pecas",
    filial_id: str = "",
) -> HTMLResponse:
    peca_svc = PecaService(session)
    estoque_svc = EstoqueService(session)
    pecas = await peca_svc.list_items(PageParams(page=page, size=25), search=q or None)
    todas_pecas = await peca_svc.list_items(PageParams(page=1, size=300), search=q or None)
    estoque = await estoque_svc.list_estoque(
        PageParams(page=1, size=50),
        filial_id=_uuid(filial_id),
        search=q or None,
    )
    alertas = await estoque_svc.list_alertas(PageParams(page=1, size=20))
    filiais = await FilialService(session).list_filiais(PageParams(page=1, size=100))
    peca_map = {str(p.id): p for p in pecas.items}
    return render(
        request,
        "manutencao/pecas_list.html",
        {
            "page_result": pecas,
            "todas_pecas": todas_pecas.items,
            "estoque": estoque,
            "alertas": alertas,
            "filiais": filiais.items,
            "peca_map": peca_map,
            "q": q,
            "tab": tab,
            "filial_id": filial_id,
            "title": "Peças e Estoque",
        },
    )


@router.get("/manutencao/pecas/novo", response_class=HTMLResponse)
async def peca_new_form(
    request: Request,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.peca.criar"))
    ],
) -> HTMLResponse:
    return render(
        request,
        "manutencao/peca_form.html",
        {"item": None, "error": None, "title": "Nova Peça", "action": "/manutencao/pecas/novo"},
    )


@router.post("/manutencao/pecas/novo", response_class=HTMLResponse)
async def peca_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.peca.criar"))
    ],
    codigo: Annotated[str, Form()],
    nome: Annotated[str, Form()],
    categoria_codigo: Annotated[str, Form()] = "",
    unidade: Annotated[str, Form()] = "UN",
    custo_medio: Annotated[str, Form()] = "0",
    status: Annotated[str, Form()] = "active",
) -> HTMLResponse:
    ctx = {"item": None, "error": None, "title": "Nova Peça", "action": "/manutencao/pecas/novo"}
    try:
        await PecaService(session).create(
            current_user.tenant_id,
            PecaCreate(
                codigo=codigo,
                nome=nome,
                categoria_codigo=categoria_codigo or None,
                unidade=unidade,
                custo_medio=_dec(custo_medio),
                status=CadastroStatus(status),
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _app_error_message(exc)
        return render(request, "manutencao/peca_form.html", ctx, status_code=400)
    return RedirectResponse("/manutencao/pecas", status_code=303)


@router.get("/manutencao/pecas/{item_id}/editar", response_class=HTMLResponse)
async def peca_edit_form(
    request: Request,
    session: SessionDep,
    item_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.peca.editar"))
    ],
) -> HTMLResponse:
    item = await PecaService(session).get(item_id)
    return render(
        request,
        "manutencao/peca_form.html",
        {
            "item": item,
            "error": None,
            "title": f"Peça — {item.codigo}",
            "action": f"/manutencao/pecas/{item_id}/editar",
        },
    )


@router.post("/manutencao/pecas/{item_id}/editar", response_class=HTMLResponse)
async def peca_update(
    request: Request,
    session: SessionDep,
    item_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.peca.editar"))
    ],
    codigo: Annotated[str, Form()],
    nome: Annotated[str, Form()],
    categoria_codigo: Annotated[str, Form()] = "",
    unidade: Annotated[str, Form()] = "UN",
    custo_medio: Annotated[str, Form()] = "0",
    status: Annotated[str, Form()] = "active",
) -> HTMLResponse:
    try:
        await PecaService(session).update(
            item_id,
            PecaUpdate(
                codigo=codigo,
                nome=nome,
                categoria_codigo=categoria_codigo or None,
                unidade=unidade,
                custo_medio=_dec(custo_medio),
                status=CadastroStatus(status),
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        item = await PecaService(session).get(item_id)
        return render(
            request,
            "manutencao/peca_form.html",
            {
                "item": item,
                "error": _app_error_message(exc),
                "title": f"Peça — {item.codigo}",
                "action": f"/manutencao/pecas/{item_id}/editar",
            },
            status_code=400,
        )
    return RedirectResponse("/manutencao/pecas", status_code=303)


@router.post("/manutencao/pecas/estoque/entrada", response_class=HTMLResponse)
async def estoque_entrada(
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.peca.editar"))
    ],
    peca_id: Annotated[str, Form()],
    filial_id: Annotated[str, Form()],
    quantidade: Annotated[str, Form()],
    custo_unitario: Annotated[str, Form()] = "0",
    observacoes: Annotated[str, Form()] = "",
) -> RedirectResponse:
    await EstoqueService(session).entrada(
        current_user.tenant_id,
        uuid.UUID(peca_id),
        EstoqueEntrada(
            filial_id=uuid.UUID(filial_id),
            quantidade=_dec(quantidade),
            custo_unitario=_dec(custo_unitario),
            observacoes=observacoes or None,
        ),
    )
    return RedirectResponse("/manutencao/pecas?tab=estoque", status_code=303)


@router.post("/manutencao/pecas/estoque/saida", response_class=HTMLResponse)
async def estoque_saida(
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.peca.editar"))
    ],
    peca_id: Annotated[str, Form()],
    filial_id: Annotated[str, Form()],
    quantidade: Annotated[str, Form()],
    observacoes: Annotated[str, Form()] = "",
) -> RedirectResponse:
    await EstoqueService(session).saida(
        current_user.tenant_id,
        uuid.UUID(peca_id),
        EstoqueSaida(
            filial_id=uuid.UUID(filial_id),
            quantidade=_dec(quantidade),
            observacoes=observacoes or None,
        ),
    )
    return RedirectResponse("/manutencao/pecas?tab=estoque", status_code=303)


@router.post("/manutencao/pecas/estoque/ajuste", response_class=HTMLResponse)
async def estoque_ajuste(
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.peca.editar"))
    ],
    peca_id: Annotated[str, Form()],
    filial_id: Annotated[str, Form()],
    quantidade: Annotated[str, Form()],
    observacoes: Annotated[str, Form()] = "",
) -> RedirectResponse:
    await EstoqueService(session).ajuste(
        current_user.tenant_id,
        uuid.UUID(peca_id),
        EstoqueAjuste(
            filial_id=uuid.UUID(filial_id),
            quantidade=_dec(quantidade),
            observacoes=observacoes or None,
        ),
    )
    return RedirectResponse("/manutencao/pecas?tab=estoque", status_code=303)


# ======================================================================== Pneus
@router.get("/manutencao/pneus", response_class=HTMLResponse)
async def pneus_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.pneu.visualizar"))
    ],
    page: int = 1,
    q: str = "",
    status: str = "",
) -> HTMLResponse:
    st = PneuStatus(status) if status else None
    result = await PneuService(session).list_items(
        PageParams(page=page, size=25), search=q or None, status=st
    )
    alertas = await PneuService(session).alertas_vida_util(PageParams(page=1, size=20))
    veiculos = await VeiculoService(session).list_items(PageParams(page=1, size=300))
    return render(
        request,
        "manutencao/pneus_list.html",
        {
            "page_result": result,
            "alertas": alertas,
            "veiculo_placas": {str(v.id): v.placa for v in veiculos.items},
            "q": q,
            "status": status,
            "title": "Pneus",
        },
    )


@router.get("/manutencao/pneus/novo", response_class=HTMLResponse)
async def pneu_new_form(
    request: Request,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.pneu.criar"))
    ],
) -> HTMLResponse:
    return render(
        request,
        "manutencao/pneu_form.html",
        {"pneu": None, "historico": [], "error": None, "title": "Novo Pneu", "action": "/manutencao/pneus/novo"},
    )


@router.post("/manutencao/pneus/novo", response_class=HTMLResponse)
async def pneu_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.pneu.criar"))
    ],
    numero_fogo: Annotated[str, Form()],
    marca: Annotated[str, Form()],
    medida: Annotated[str, Form()],
    modelo: Annotated[str, Form()] = "",
    vida_util_km: Annotated[str, Form()] = "",
    observacoes: Annotated[str, Form()] = "",
) -> HTMLResponse:
    ctx = {"pneu": None, "historico": [], "error": None, "title": "Novo Pneu", "action": "/manutencao/pneus/novo"}
    try:
        item = await PneuService(session).create(
            current_user.tenant_id,
            PneuCreate(
                numero_fogo=numero_fogo,
                marca=marca,
                modelo=modelo or None,
                medida=medida,
                vida_util_km=int(vida_util_km) if vida_util_km.strip() else None,
                observacoes=observacoes or None,
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _app_error_message(exc)
        return render(request, "manutencao/pneu_form.html", ctx, status_code=400)
    return RedirectResponse(f"/manutencao/pneus/{item.id}/editar", status_code=303)


@router.get("/manutencao/pneus/{pneu_id}/editar", response_class=HTMLResponse)
async def pneu_edit_form(
    request: Request,
    session: SessionDep,
    pneu_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.pneu.editar"))
    ],
) -> HTMLResponse:
    pneu = await PneuService(session).get(pneu_id)
    hist_repo = PneuHistoricoRepository(session)
    historico = list(
        (await session.execute(hist_repo.list_by_pneu(pneu_id))).scalars().all()
    )
    veiculos = await VeiculoService(session).list_items(PageParams(page=1, size=300))
    return render(
        request,
        "manutencao/pneu_form.html",
        {
            "pneu": pneu,
            "historico": historico,
            "veiculos": veiculos.items,
            "error": None,
            "title": f"Pneu {pneu.numero_fogo}",
            "action": f"/manutencao/pneus/{pneu_id}/editar",
        },
    )


@router.post("/manutencao/pneus/{pneu_id}/editar", response_class=HTMLResponse)
async def pneu_update(
    request: Request,
    session: SessionDep,
    pneu_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.pneu.editar"))
    ],
    marca: Annotated[str, Form()],
    medida: Annotated[str, Form()],
    modelo: Annotated[str, Form()] = "",
    vida_util_km: Annotated[str, Form()] = "",
    observacoes: Annotated[str, Form()] = "",
) -> HTMLResponse:
    hist_repo = PneuHistoricoRepository(session)
    historico = list(
        (await session.execute(hist_repo.list_by_pneu(pneu_id))).scalars().all()
    )
    veiculos = await VeiculoService(session).list_items(PageParams(page=1, size=300))
    try:
        await PneuService(session).update(
            pneu_id,
            PneuUpdate(
                marca=marca,
                modelo=modelo or None,
                medida=medida,
                vida_util_km=int(vida_util_km) if vida_util_km.strip() else None,
                observacoes=observacoes or None,
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        pneu = await PneuService(session).get(pneu_id)
        return render(
            request,
            "manutencao/pneu_form.html",
            {
                "pneu": pneu,
                "historico": historico,
                "veiculos": veiculos.items,
                "error": _app_error_message(exc),
                "title": f"Pneu {pneu.numero_fogo}",
                "action": f"/manutencao/pneus/{pneu_id}/editar",
            },
            status_code=400,
        )
    return RedirectResponse(f"/manutencao/pneus/{pneu_id}/editar", status_code=303)


@router.post("/manutencao/pneus/{pneu_id}/instalar", response_class=HTMLResponse)
async def pneu_instalar(
    session: SessionDep,
    pneu_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.pneu.editar"))
    ],
    veiculo_id: Annotated[str, Form()],
    posicao: Annotated[str, Form()],
    km: Annotated[str, Form()],
) -> RedirectResponse:
    await PneuService(session).instalar(
        current_user.tenant_id,
        pneu_id,
        PneuInstalar(
            veiculo_id=uuid.UUID(veiculo_id),
            posicao=PneuPosicao(posicao),
            km=int(km),
        ),
    )
    return RedirectResponse(f"/manutencao/pneus/{pneu_id}/editar", status_code=303)


@router.post("/manutencao/pneus/{pneu_id}/rodizio", response_class=HTMLResponse)
async def pneu_rodizio(
    session: SessionDep,
    pneu_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.pneu.editar"))
    ],
    posicao_destino: Annotated[str, Form()],
    km: Annotated[str, Form()] = "",
    observacoes: Annotated[str, Form()] = "",
) -> RedirectResponse:
    await PneuService(session).rodizio(
        current_user.tenant_id,
        pneu_id,
        PneuRodizio(
            posicao_destino=PneuPosicao(posicao_destino),
            km=int(km) if km.strip() else None,
            observacoes=observacoes or None,
        ),
    )
    return RedirectResponse(f"/manutencao/pneus/{pneu_id}/editar", status_code=303)


@router.post("/manutencao/pneus/{pneu_id}/inspecionar", response_class=HTMLResponse)
async def pneu_inspecionar(
    session: SessionDep,
    pneu_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.pneu.editar"))
    ],
    sulco_mm: Annotated[str, Form()],
    km: Annotated[str, Form()] = "",
    observacoes: Annotated[str, Form()] = "",
) -> RedirectResponse:
    await PneuService(session).inspecionar(
        current_user.tenant_id,
        pneu_id,
        PneuInspecionar(
            sulco_mm=_dec(sulco_mm),
            km=int(km) if km.strip() else None,
            observacoes=observacoes or None,
        ),
    )
    return RedirectResponse(f"/manutencao/pneus/{pneu_id}/editar", status_code=303)


@router.post("/manutencao/pneus/{pneu_id}/descartar", response_class=HTMLResponse)
async def pneu_descartar(
    session: SessionDep,
    pneu_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("manutencao.pneu.editar"))
    ],
    motivo: Annotated[str, Form()] = "",
    km: Annotated[str, Form()] = "",
) -> RedirectResponse:
    await PneuService(session).descartar(
        current_user.tenant_id,
        pneu_id,
        PneuDescartar(motivo=motivo or None, km=int(km) if km.strip() else None),
    )
    return RedirectResponse(f"/manutencao/pneus/{pneu_id}/editar", status_code=303)
