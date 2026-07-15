"""Rotas Web (HTML/Jinja2) do módulo Tarifário."""

from __future__ import annotations

import uuid
from datetime import date, datetime
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
from app.modules.cadastros.service import ClienteService
from app.modules.cadastros.service_extra import FornecedorService, ParceiroService
from app.modules.frota.service import AcessoriosService, CategoriasService
from app.modules.identity.service import AuthenticatedUser
from app.modules.tarifario.schemas import (
    PoliticaCreate,
    PoliticaFaixaCreate,
    PoliticaUpdate,
    PricingQuoteInput,
    ProtecaoCreate,
    ProtecaoUpdate,
    TabelaCreate,
    TabelaItemCreate,
    TabelaItemUpdate,
    TabelaUpdate,
    TaxaCreate,
    TaxaUpdate,
    TemporadaCreate,
    TemporadaUpdate,
)
from app.modules.tarifario.service import (
    PoliticaCancelamentoService,
    PricingService,
    ProtecaoService,
    TabelaTarifaService,
    TaxaService,
    TemporadaService,
)
from app.modules.tenants.service import FilialService
from app.shared.enums import (
    CadastroStatus,
    PoliticaRetencaoTipo,
    TarifarioCanal,
    TaxaAplicacao,
    TaxaCalculoTipo,
    TemporadaAjusteTipo,
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


def _datetime(raw: str | None) -> datetime | None:
    if not raw or not raw.strip():
        return None
    value = raw.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    if "T" in value and len(value) == 16:
        value = f"{value}:00"
    return datetime.fromisoformat(value)


def _uuid(raw: str | None) -> uuid.UUID | None:
    if not raw or not raw.strip():
        return None
    return uuid.UUID(raw.strip())


def _app_error_message(exc: AppError | ValueError) -> str:
    return exc.message if isinstance(exc, AppError) else str(exc)


def _parse_uuid_list(raw_values: list[str]) -> list[uuid.UUID]:
    ids: list[uuid.UUID] = []
    for value in raw_values:
        if value and value.strip():
            ids.append(uuid.UUID(value.strip()))
    return ids


async def _ensure_tarifario_defaults(session: AsyncSession, tenant_id: uuid.UUID) -> None:
    await CategoriasService(session).ensure_defaults(tenant_id)
    await PricingService(session).ensure_defaults(tenant_id)


async def _tarifario_lookups(session: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Any]:
    await _ensure_tarifario_defaults(session, tenant_id)
    categorias = await CategoriasService(session).list_items(PageParams(page=1, size=200))
    filiais = await FilialService(session).list_filiais(PageParams(page=1, size=100))
    tabelas = await TabelaTarifaService(session).list_items(PageParams(page=1, size=200))
    clientes = await ClienteService(session).list_clientes(PageParams(page=1, size=200))
    parceiros = await ParceiroService(session).list_items(PageParams(page=1, size=200))
    fornecedores = await FornecedorService(session).list_items(PageParams(page=1, size=200))
    taxas = await TaxaService(session).list_items(PageParams(page=1, size=200))
    protecoes = await ProtecaoService(session).list_items(PageParams(page=1, size=200))
    politicas = await PoliticaCancelamentoService(session).list_items(PageParams(page=1, size=100))
    acessorios = await AcessoriosService(session).list_items(PageParams(page=1, size=200))
    return {
        "categorias": categorias.items,
        "filiais": filiais.items,
        "tabelas": tabelas.items,
        "clientes": clientes.items,
        "parceiros": parceiros.items,
        "fornecedores": fornecedores.items,
        "taxas_opcionais": taxas.items,
        "protecoes": protecoes.items,
        "politicas": politicas.items,
        "acessorios": acessorios.items,
        "categoria_nomes": {str(c.id): c.nome for c in categorias.items},
        "filial_nomes": {str(f.id): f.name for f in filiais.items},
        "tabela_nomes": {str(t.id): t.nome for t in tabelas.items},
    }


# ================================================================ Tabelas de Tarifas
@router.get("/tarifario/tabelas", response_class=HTMLResponse)
async def tabelas_list(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("tarifario.tabela.visualizar"))
    ],
    page: int = 1,
    q: str = "",
    canal: str = "",
) -> HTMLResponse:
    await _ensure_tarifario_defaults(session, current_user.tenant_id)
    cn = TarifarioCanal(canal) if canal else None
    result = await TabelaTarifaService(session).list_items(
        PageParams(page=page, size=25), search=q or None, canal=cn
    )
    lookups = await _tarifario_lookups(session, current_user.tenant_id)
    return render(
        request,
        "tarifario/tabelas_list.html",
        {
            "page_result": result,
            "q": q,
            "canal": canal,
            "title": "Tabelas de Tarifas",
            **lookups,
        },
    )


@router.get("/tarifario/tabelas/novo", response_class=HTMLResponse)
async def tabela_new_form(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("tarifario.tabela.criar"))
    ],
) -> HTMLResponse:
    lookups = await _tarifario_lookups(session, current_user.tenant_id)
    return render(
        request,
        "tarifario/tabela_form.html",
        {
            "tabela": None,
            "itens": [],
            "error": None,
            "title": "Nova Tabela de Tarifas",
            "action": "/tarifario/tabelas/novo",
            **lookups,
        },
    )


@router.post("/tarifario/tabelas/novo", response_class=HTMLResponse)
async def tabela_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("tarifario.tabela.criar"))
    ],
    nome: Annotated[str, Form()],
    vigencia_inicio: Annotated[str, Form()],
    vigencia_fim: Annotated[str, Form()] = "",
    canal: Annotated[str, Form()] = "todos",
    filial_id: Annotated[str, Form()] = "",
    parceiro_id: Annotated[str, Form()] = "",
    cliente_id: Annotated[str, Form()] = "",
    prioridade: Annotated[str, Form()] = "0",
    status: Annotated[str, Form()] = "active",
    observacoes: Annotated[str, Form()] = "",
) -> HTMLResponse:
    lookups = await _tarifario_lookups(session, current_user.tenant_id)
    ctx = {
        "tabela": None,
        "itens": [],
        "error": None,
        "title": "Nova Tabela de Tarifas",
        "action": "/tarifario/tabelas/novo",
        **lookups,
    }
    try:
        item = await TabelaTarifaService(session).create(
            current_user.tenant_id,
            TabelaCreate(
                nome=nome,
                vigencia_inicio=_date(vigencia_inicio) or date.today(),
                vigencia_fim=_date(vigencia_fim),
                canal=TarifarioCanal(canal),
                filial_id=_uuid(filial_id),
                parceiro_id=_uuid(parceiro_id),
                cliente_id=_uuid(cliente_id),
                prioridade=int(prioridade) if prioridade.strip() else 0,
                status=CadastroStatus(status),
                observacoes=observacoes or None,
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _app_error_message(exc)
        return render(request, "tarifario/tabela_form.html", ctx, status_code=400)
    return RedirectResponse(f"/tarifario/tabelas/{item.id}/editar", status_code=303)


@router.get("/tarifario/tabelas/{tabela_id}/editar", response_class=HTMLResponse)
async def tabela_edit_form(
    request: Request,
    session: SessionDep,
    tabela_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("tarifario.tabela.editar"))
    ],
) -> HTMLResponse:
    tabela = await TabelaTarifaService(session).get(tabela_id)
    itens = await TabelaTarifaService(session).list_itens(tabela_id)
    lookups = await _tarifario_lookups(session, current_user.tenant_id)
    return render(
        request,
        "tarifario/tabela_form.html",
        {
            "tabela": tabela,
            "itens": itens,
            "error": None,
            "title": f"Tabela — {tabela.nome}",
            "action": f"/tarifario/tabelas/{tabela_id}/editar",
            **lookups,
        },
    )


@router.post("/tarifario/tabelas/{tabela_id}/editar", response_class=HTMLResponse)
async def tabela_update(
    request: Request,
    session: SessionDep,
    tabela_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("tarifario.tabela.editar"))
    ],
    nome: Annotated[str, Form()],
    vigencia_inicio: Annotated[str, Form()],
    vigencia_fim: Annotated[str, Form()] = "",
    canal: Annotated[str, Form()] = "todos",
    filial_id: Annotated[str, Form()] = "",
    parceiro_id: Annotated[str, Form()] = "",
    cliente_id: Annotated[str, Form()] = "",
    prioridade: Annotated[str, Form()] = "0",
    status: Annotated[str, Form()] = "active",
    observacoes: Annotated[str, Form()] = "",
) -> HTMLResponse:
    lookups = await _tarifario_lookups(session, current_user.tenant_id)
    itens = await TabelaTarifaService(session).list_itens(tabela_id)
    try:
        await TabelaTarifaService(session).update(
            tabela_id,
            TabelaUpdate(
                nome=nome,
                vigencia_inicio=_date(vigencia_inicio),
                vigencia_fim=_date(vigencia_fim),
                canal=TarifarioCanal(canal),
                filial_id=_uuid(filial_id),
                parceiro_id=_uuid(parceiro_id),
                cliente_id=_uuid(cliente_id),
                prioridade=int(prioridade) if prioridade.strip() else 0,
                status=CadastroStatus(status),
                observacoes=observacoes or None,
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        tabela = await TabelaTarifaService(session).get(tabela_id)
        return render(
            request,
            "tarifario/tabela_form.html",
            {
                "tabela": tabela,
                "itens": itens,
                "error": _app_error_message(exc),
                "title": f"Tabela — {tabela.nome}",
                "action": f"/tarifario/tabelas/{tabela_id}/editar",
                **lookups,
            },
            status_code=400,
        )
    return RedirectResponse(f"/tarifario/tabelas/{tabela_id}/editar", status_code=303)


@router.post("/tarifario/tabelas/{tabela_id}/itens", response_class=HTMLResponse)
async def tabela_add_item(
    session: SessionDep,
    tabela_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("tarifario.tabela.editar"))
    ],
    categoria_id: Annotated[str, Form()],
    valor_1_3: Annotated[str, Form()] = "0",
    valor_4_7: Annotated[str, Form()] = "0",
    valor_8_15: Annotated[str, Form()] = "0",
    valor_16_30: Annotated[str, Form()] = "0",
    valor_mensal: Annotated[str, Form()] = "0",
    km_livre: Annotated[str, Form()] = "",
    km_incluido: Annotated[str, Form()] = "",
    valor_km_excedente: Annotated[str, Form()] = "",
) -> RedirectResponse:
    await TabelaTarifaService(session).add_item(
        current_user.tenant_id,
        tabela_id,
        TabelaItemCreate(
            categoria_id=uuid.UUID(categoria_id),
            valor_1_3=_dec(valor_1_3),
            valor_4_7=_dec(valor_4_7),
            valor_8_15=_dec(valor_8_15),
            valor_16_30=_dec(valor_16_30),
            valor_mensal=_dec(valor_mensal),
            km_livre=bool(km_livre),
            km_incluido=int(km_incluido) if km_incluido.strip() else None,
            valor_km_excedente=_dec(valor_km_excedente) if valor_km_excedente.strip() else None,
        ),
    )
    return RedirectResponse(f"/tarifario/tabelas/{tabela_id}/editar", status_code=303)


@router.post("/tarifario/tabelas/{tabela_id}/itens/{item_id}/editar", response_class=HTMLResponse)
async def tabela_update_item(
    session: SessionDep,
    tabela_id: uuid.UUID,
    item_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("tarifario.tabela.editar"))
    ],
    valor_1_3: Annotated[str, Form()] = "0",
    valor_4_7: Annotated[str, Form()] = "0",
    valor_8_15: Annotated[str, Form()] = "0",
    valor_16_30: Annotated[str, Form()] = "0",
    valor_mensal: Annotated[str, Form()] = "0",
    km_livre: Annotated[str, Form()] = "",
    km_incluido: Annotated[str, Form()] = "",
    valor_km_excedente: Annotated[str, Form()] = "",
) -> RedirectResponse:
    await TabelaTarifaService(session).update_item(
        tabela_id,
        item_id,
        TabelaItemUpdate(
            valor_1_3=_dec(valor_1_3),
            valor_4_7=_dec(valor_4_7),
            valor_8_15=_dec(valor_8_15),
            valor_16_30=_dec(valor_16_30),
            valor_mensal=_dec(valor_mensal),
            km_livre=bool(km_livre),
            km_incluido=int(km_incluido) if km_incluido.strip() else None,
            valor_km_excedente=_dec(valor_km_excedente) if valor_km_excedente.strip() else None,
        ),
    )
    return RedirectResponse(f"/tarifario/tabelas/{tabela_id}/editar", status_code=303)


@router.post("/tarifario/tabelas/{tabela_id}/itens/{item_id}/remover", response_class=HTMLResponse)
async def tabela_remove_item(
    session: SessionDep,
    tabela_id: uuid.UUID,
    item_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("tarifario.tabela.editar"))
    ],
) -> RedirectResponse:
    await TabelaTarifaService(session).remove_item(tabela_id, item_id)
    return RedirectResponse(f"/tarifario/tabelas/{tabela_id}/editar", status_code=303)


# =================================================================== Temporadas
@router.get("/tarifario/temporadas", response_class=HTMLResponse)
async def temporadas_list(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("tarifario.temporada.visualizar"))
    ],
    page: int = 1,
    q: str = "",
) -> HTMLResponse:
    result = await TemporadaService(session).list_items(
        PageParams(page=page, size=25), search=q or None
    )
    lookups = await _tarifario_lookups(session, current_user.tenant_id)
    return render(
        request,
        "tarifario/temporadas_list.html",
        {
            "page_result": result,
            "q": q,
            "title": "Temporadas",
            **lookups,
        },
    )


@router.get("/tarifario/temporadas/novo", response_class=HTMLResponse)
async def temporada_new_form(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("tarifario.temporada.criar"))
    ],
) -> HTMLResponse:
    lookups = await _tarifario_lookups(session, current_user.tenant_id)
    return render(
        request,
        "tarifario/temporada_form.html",
        {
            "temporada": None,
            "error": None,
            "title": "Nova Temporada",
            "action": "/tarifario/temporadas/novo",
            **lookups,
        },
    )


@router.post("/tarifario/temporadas/novo", response_class=HTMLResponse)
async def temporada_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("tarifario.temporada.criar"))
    ],
    nome: Annotated[str, Form()],
    data_inicio: Annotated[str, Form()],
    data_fim: Annotated[str, Form()],
    tipo_ajuste: Annotated[str, Form()],
    valor_ajuste: Annotated[str, Form()] = "0",
    tabela_alternativa_id: Annotated[str, Form()] = "",
    estadia_minima: Annotated[str, Form()] = "1",
    prioridade: Annotated[str, Form()] = "0",
    filial_id: Annotated[str, Form()] = "",
    categoria_id: Annotated[str, Form()] = "",
    status: Annotated[str, Form()] = "active",
) -> HTMLResponse:
    lookups = await _tarifario_lookups(session, current_user.tenant_id)
    ctx = {
        "temporada": None,
        "error": None,
        "title": "Nova Temporada",
        "action": "/tarifario/temporadas/novo",
        **lookups,
    }
    try:
        await TemporadaService(session).create(
            current_user.tenant_id,
            TemporadaCreate(
                nome=nome,
                data_inicio=_date(data_inicio) or date.today(),
                data_fim=_date(data_fim) or date.today(),
                tipo_ajuste=TemporadaAjusteTipo(tipo_ajuste),
                valor_ajuste=_dec(valor_ajuste),
                tabela_alternativa_id=_uuid(tabela_alternativa_id),
                estadia_minima=int(estadia_minima) if estadia_minima.strip() else 1,
                prioridade=int(prioridade) if prioridade.strip() else 0,
                filial_id=_uuid(filial_id),
                categoria_id=_uuid(categoria_id),
                status=CadastroStatus(status),
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _app_error_message(exc)
        return render(request, "tarifario/temporada_form.html", ctx, status_code=400)
    return RedirectResponse("/tarifario/temporadas", status_code=303)


@router.get("/tarifario/temporadas/{temporada_id}/editar", response_class=HTMLResponse)
async def temporada_edit_form(
    request: Request,
    session: SessionDep,
    temporada_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("tarifario.temporada.editar"))
    ],
) -> HTMLResponse:
    temporada = await TemporadaService(session).get(temporada_id)
    lookups = await _tarifario_lookups(session, current_user.tenant_id)
    return render(
        request,
        "tarifario/temporada_form.html",
        {
            "temporada": temporada,
            "error": None,
            "title": f"Temporada — {temporada.nome}",
            "action": f"/tarifario/temporadas/{temporada_id}/editar",
            **lookups,
        },
    )


@router.post("/tarifario/temporadas/{temporada_id}/editar", response_class=HTMLResponse)
async def temporada_update(
    request: Request,
    session: SessionDep,
    temporada_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("tarifario.temporada.editar"))
    ],
    nome: Annotated[str, Form()],
    data_inicio: Annotated[str, Form()],
    data_fim: Annotated[str, Form()],
    tipo_ajuste: Annotated[str, Form()],
    valor_ajuste: Annotated[str, Form()] = "0",
    tabela_alternativa_id: Annotated[str, Form()] = "",
    estadia_minima: Annotated[str, Form()] = "1",
    prioridade: Annotated[str, Form()] = "0",
    filial_id: Annotated[str, Form()] = "",
    categoria_id: Annotated[str, Form()] = "",
    status: Annotated[str, Form()] = "active",
) -> HTMLResponse:
    lookups = await _tarifario_lookups(session, current_user.tenant_id)
    try:
        await TemporadaService(session).update(
            temporada_id,
            TemporadaUpdate(
                nome=nome,
                data_inicio=_date(data_inicio),
                data_fim=_date(data_fim),
                tipo_ajuste=TemporadaAjusteTipo(tipo_ajuste),
                valor_ajuste=_dec(valor_ajuste),
                tabela_alternativa_id=_uuid(tabela_alternativa_id),
                estadia_minima=int(estadia_minima) if estadia_minima.strip() else None,
                prioridade=int(prioridade) if prioridade.strip() else None,
                filial_id=_uuid(filial_id),
                categoria_id=_uuid(categoria_id),
                status=CadastroStatus(status),
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        temporada = await TemporadaService(session).get(temporada_id)
        return render(
            request,
            "tarifario/temporada_form.html",
            {
                "temporada": temporada,
                "error": _app_error_message(exc),
                "title": f"Temporada — {temporada.nome}",
                "action": f"/tarifario/temporadas/{temporada_id}/editar",
                **lookups,
            },
            status_code=400,
        )
    return RedirectResponse(f"/tarifario/temporadas/{temporada_id}/editar", status_code=303)


# ========================================================================= Taxas
@router.get("/tarifario/taxas", response_class=HTMLResponse)
async def taxas_list(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("tarifario.taxa.visualizar"))
    ],
    page: int = 1,
    q: str = "",
) -> HTMLResponse:
    result = await TaxaService(session).list_items(
        PageParams(page=page, size=25), search=q or None
    )
    return render(
        request,
        "tarifario/taxas_list.html",
        {
            "page_result": result,
            "q": q,
            "title": "Taxas e Encargos",
        },
    )


@router.get("/tarifario/taxas/novo", response_class=HTMLResponse)
async def taxa_new_form(
    request: Request,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("tarifario.taxa.criar"))
    ],
) -> HTMLResponse:
    return render(
        request,
        "tarifario/taxa_form.html",
        {"taxa": None, "error": None, "title": "Nova Taxa", "action": "/tarifario/taxas/novo"},
    )


@router.post("/tarifario/taxas/novo", response_class=HTMLResponse)
async def taxa_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("tarifario.taxa.criar"))
    ],
    nome: Annotated[str, Form()],
    tipo_calculo: Annotated[str, Form()],
    descricao: Annotated[str, Form()] = "",
    valor: Annotated[str, Form()] = "0",
    aplicacao: Annotated[str, Form()] = "opcional",
    regra_codigo: Annotated[str, Form()] = "",
    tributavel: Annotated[str, Form()] = "",
    status: Annotated[str, Form()] = "active",
) -> HTMLResponse:
    ctx = {"taxa": None, "error": None, "title": "Nova Taxa", "action": "/tarifario/taxas/novo"}
    try:
        await TaxaService(session).create(
            current_user.tenant_id,
            TaxaCreate(
                nome=nome,
                descricao=descricao or None,
                tipo_calculo=TaxaCalculoTipo(tipo_calculo),
                valor=_dec(valor),
                aplicacao=TaxaAplicacao(aplicacao),
                regra_codigo=regra_codigo or None,
                tributavel=bool(tributavel),
                status=CadastroStatus(status),
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _app_error_message(exc)
        return render(request, "tarifario/taxa_form.html", ctx, status_code=400)
    return RedirectResponse("/tarifario/taxas", status_code=303)


@router.get("/tarifario/taxas/{taxa_id}/editar", response_class=HTMLResponse)
async def taxa_edit_form(
    request: Request,
    session: SessionDep,
    taxa_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("tarifario.taxa.editar"))
    ],
) -> HTMLResponse:
    taxa = await TaxaService(session).get(taxa_id)
    return render(
        request,
        "tarifario/taxa_form.html",
        {
            "taxa": taxa,
            "error": None,
            "title": f"Taxa — {taxa.nome}",
            "action": f"/tarifario/taxas/{taxa_id}/editar",
        },
    )


@router.post("/tarifario/taxas/{taxa_id}/editar", response_class=HTMLResponse)
async def taxa_update(
    request: Request,
    session: SessionDep,
    taxa_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("tarifario.taxa.editar"))
    ],
    nome: Annotated[str, Form()],
    tipo_calculo: Annotated[str, Form()],
    descricao: Annotated[str, Form()] = "",
    valor: Annotated[str, Form()] = "0",
    aplicacao: Annotated[str, Form()] = "opcional",
    regra_codigo: Annotated[str, Form()] = "",
    tributavel: Annotated[str, Form()] = "",
    status: Annotated[str, Form()] = "active",
) -> HTMLResponse:
    try:
        await TaxaService(session).update(
            taxa_id,
            TaxaUpdate(
                nome=nome,
                descricao=descricao or None,
                tipo_calculo=TaxaCalculoTipo(tipo_calculo),
                valor=_dec(valor),
                aplicacao=TaxaAplicacao(aplicacao),
                regra_codigo=regra_codigo or None,
                tributavel=bool(tributavel),
                status=CadastroStatus(status),
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        taxa = await TaxaService(session).get(taxa_id)
        return render(
            request,
            "tarifario/taxa_form.html",
            {
                "taxa": taxa,
                "error": _app_error_message(exc),
                "title": f"Taxa — {taxa.nome}",
                "action": f"/tarifario/taxas/{taxa_id}/editar",
            },
            status_code=400,
        )
    return RedirectResponse("/tarifario/taxas", status_code=303)


# ==================================================================== Proteções
@router.get("/tarifario/protecoes", response_class=HTMLResponse)
async def protecoes_list(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("tarifario.protecao.visualizar"))
    ],
    page: int = 1,
    q: str = "",
) -> HTMLResponse:
    result = await ProtecaoService(session).list_items(
        PageParams(page=page, size=25), search=q or None
    )
    lookups = await _tarifario_lookups(session, current_user.tenant_id)
    return render(
        request,
        "tarifario/protecoes_list.html",
        {
            "page_result": result,
            "q": q,
            "title": "Proteções",
            **lookups,
        },
    )


@router.get("/tarifario/protecoes/novo", response_class=HTMLResponse)
async def protecao_new_form(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("tarifario.protecao.criar"))
    ],
) -> HTMLResponse:
    lookups = await _tarifario_lookups(session, current_user.tenant_id)
    return render(
        request,
        "tarifario/protecao_form.html",
        {
            "protecao": None,
            "categorias_vinculadas": [],
            "error": None,
            "title": "Nova Proteção",
            "action": "/tarifario/protecoes/novo",
            **lookups,
        },
    )


@router.post("/tarifario/protecoes/novo", response_class=HTMLResponse)
async def protecao_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("tarifario.protecao.criar"))
    ],
    nome: Annotated[str, Form()],
    descricao: Annotated[str, Form()] = "",
    valor_diaria: Annotated[str, Form()] = "0",
    franquia: Annotated[str, Form()] = "0",
    fornecedor_id: Annotated[str, Form()] = "",
    exclusoes: Annotated[str, Form()] = "",
    obrigatoria: Annotated[str, Form()] = "",
    status: Annotated[str, Form()] = "active",
    categorias_obrigatorias: Annotated[list[str], Form()] = [],
) -> HTMLResponse:
    lookups = await _tarifario_lookups(session, current_user.tenant_id)
    ctx = {
        "protecao": None,
        "categorias_vinculadas": [],
        "error": None,
        "title": "Nova Proteção",
        "action": "/tarifario/protecoes/novo",
        **lookups,
    }
    try:
        item = await ProtecaoService(session).create(
            current_user.tenant_id,
            ProtecaoCreate(
                nome=nome,
                descricao=descricao or None,
                valor_diaria=_dec(valor_diaria),
                franquia=_dec(franquia),
                fornecedor_id=_uuid(fornecedor_id),
                exclusoes=exclusoes or None,
                obrigatoria=bool(obrigatoria),
                status=CadastroStatus(status),
                categorias_obrigatorias=_parse_uuid_list(categorias_obrigatorias),
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _app_error_message(exc)
        return render(request, "tarifario/protecao_form.html", ctx, status_code=400)
    return RedirectResponse(f"/tarifario/protecoes/{item.id}/editar", status_code=303)


@router.get("/tarifario/protecoes/{protecao_id}/editar", response_class=HTMLResponse)
async def protecao_edit_form(
    request: Request,
    session: SessionDep,
    protecao_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("tarifario.protecao.editar"))
    ],
) -> HTMLResponse:
    protecao = await ProtecaoService(session).get(protecao_id)
    categorias_vinculadas = await ProtecaoService(session).list_categorias(protecao_id)
    lookups = await _tarifario_lookups(session, current_user.tenant_id)
    return render(
        request,
        "tarifario/protecao_form.html",
        {
            "protecao": protecao,
            "categorias_vinculadas": categorias_vinculadas,
            "error": None,
            "title": f"Proteção — {protecao.nome}",
            "action": f"/tarifario/protecoes/{protecao_id}/editar",
            **lookups,
        },
    )


@router.post("/tarifario/protecoes/{protecao_id}/editar", response_class=HTMLResponse)
async def protecao_update(
    request: Request,
    session: SessionDep,
    protecao_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("tarifario.protecao.editar"))
    ],
    nome: Annotated[str, Form()],
    descricao: Annotated[str, Form()] = "",
    valor_diaria: Annotated[str, Form()] = "0",
    franquia: Annotated[str, Form()] = "0",
    fornecedor_id: Annotated[str, Form()] = "",
    exclusoes: Annotated[str, Form()] = "",
    obrigatoria: Annotated[str, Form()] = "",
    status: Annotated[str, Form()] = "active",
    categorias_obrigatorias: Annotated[list[str], Form()] = [],
) -> HTMLResponse:
    lookups = await _tarifario_lookups(session, current_user.tenant_id)
    categorias_vinculadas = await ProtecaoService(session).list_categorias(protecao_id)
    try:
        await ProtecaoService(session).update(
            protecao_id,
            ProtecaoUpdate(
                nome=nome,
                descricao=descricao or None,
                valor_diaria=_dec(valor_diaria),
                franquia=_dec(franquia),
                fornecedor_id=_uuid(fornecedor_id),
                exclusoes=exclusoes or None,
                obrigatoria=bool(obrigatoria),
                status=CadastroStatus(status),
                categorias_obrigatorias=_parse_uuid_list(categorias_obrigatorias),
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        protecao = await ProtecaoService(session).get(protecao_id)
        return render(
            request,
            "tarifario/protecao_form.html",
            {
                "protecao": protecao,
                "categorias_vinculadas": categorias_vinculadas,
                "error": _app_error_message(exc),
                "title": f"Proteção — {protecao.nome}",
                "action": f"/tarifario/protecoes/{protecao_id}/editar",
                **lookups,
            },
            status_code=400,
        )
    return RedirectResponse(f"/tarifario/protecoes/{protecao_id}/editar", status_code=303)


@router.post("/tarifario/protecoes/{protecao_id}/categorias", response_class=HTMLResponse)
async def protecao_link_categoria(
    session: SessionDep,
    protecao_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("tarifario.protecao.editar"))
    ],
    categoria_id: Annotated[str, Form()],
) -> RedirectResponse:
    await ProtecaoService(session).link_categoria(
        current_user.tenant_id, protecao_id, uuid.UUID(categoria_id)
    )
    return RedirectResponse(f"/tarifario/protecoes/{protecao_id}/editar", status_code=303)


# ========================================================= Políticas de Cancelamento
@router.get("/tarifario/cancelamento", response_class=HTMLResponse)
async def politicas_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("tarifario.politica.visualizar"))
    ],
    page: int = 1,
    q: str = "",
) -> HTMLResponse:
    result = await PoliticaCancelamentoService(session).list_items(
        PageParams(page=page, size=25), search=q or None
    )
    return render(
        request,
        "tarifario/politicas_list.html",
        {"page_result": result, "q": q, "title": "Políticas de Cancelamento"},
    )


@router.get("/tarifario/cancelamento/novo", response_class=HTMLResponse)
async def politica_new_form(
    request: Request,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("tarifario.politica.criar"))
    ],
) -> HTMLResponse:
    return render(
        request,
        "tarifario/politica_form.html",
        {
            "politica": None,
            "faixas": [],
            "error": None,
            "title": "Nova Política de Cancelamento",
            "action": "/tarifario/cancelamento/novo",
        },
    )


@router.post("/tarifario/cancelamento/novo", response_class=HTMLResponse)
async def politica_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("tarifario.politica.criar"))
    ],
    nome: Annotated[str, Form()],
    canal: Annotated[str, Form()] = "todos",
    status: Annotated[str, Form()] = "active",
    descricao: Annotated[str, Form()] = "",
) -> HTMLResponse:
    ctx = {
        "politica": None,
        "faixas": [],
        "error": None,
        "title": "Nova Política de Cancelamento",
        "action": "/tarifario/cancelamento/novo",
    }
    try:
        item = await PoliticaCancelamentoService(session).create(
            current_user.tenant_id,
            PoliticaCreate(
                nome=nome,
                canal=TarifarioCanal(canal),
                status=CadastroStatus(status),
                descricao=descricao or None,
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _app_error_message(exc)
        return render(request, "tarifario/politica_form.html", ctx, status_code=400)
    return RedirectResponse(f"/tarifario/cancelamento/{item.id}/editar", status_code=303)


@router.get("/tarifario/cancelamento/{politica_id}/editar", response_class=HTMLResponse)
async def politica_edit_form(
    request: Request,
    session: SessionDep,
    politica_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("tarifario.politica.editar"))
    ],
) -> HTMLResponse:
    politica = await PoliticaCancelamentoService(session).get(politica_id)
    faixas = await PoliticaCancelamentoService(session).list_faixas(politica_id)
    return render(
        request,
        "tarifario/politica_form.html",
        {
            "politica": politica,
            "faixas": faixas,
            "error": None,
            "title": f"Política — {politica.nome}",
            "action": f"/tarifario/cancelamento/{politica_id}/editar",
        },
    )


@router.post("/tarifario/cancelamento/{politica_id}/editar", response_class=HTMLResponse)
async def politica_update(
    request: Request,
    session: SessionDep,
    politica_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("tarifario.politica.editar"))
    ],
    nome: Annotated[str, Form()],
    canal: Annotated[str, Form()] = "todos",
    status: Annotated[str, Form()] = "active",
    descricao: Annotated[str, Form()] = "",
) -> HTMLResponse:
    faixas = await PoliticaCancelamentoService(session).list_faixas(politica_id)
    try:
        await PoliticaCancelamentoService(session).update(
            politica_id,
            PoliticaUpdate(
                nome=nome,
                canal=TarifarioCanal(canal),
                status=CadastroStatus(status),
                descricao=descricao or None,
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        politica = await PoliticaCancelamentoService(session).get(politica_id)
        return render(
            request,
            "tarifario/politica_form.html",
            {
                "politica": politica,
                "faixas": faixas,
                "error": _app_error_message(exc),
                "title": f"Política — {politica.nome}",
                "action": f"/tarifario/cancelamento/{politica_id}/editar",
            },
            status_code=400,
        )
    return RedirectResponse(f"/tarifario/cancelamento/{politica_id}/editar", status_code=303)


@router.post("/tarifario/cancelamento/{politica_id}/faixas", response_class=HTMLResponse)
async def politica_add_faixa(
    session: SessionDep,
    politica_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("tarifario.politica.editar"))
    ],
    tipo_retencao: Annotated[str, Form()],
    horas_antes_min: Annotated[str, Form()] = "0",
    horas_antes_max: Annotated[str, Form()] = "",
    valor_retencao: Annotated[str, Form()] = "0",
    ordem: Annotated[str, Form()] = "0",
) -> RedirectResponse:
    await PoliticaCancelamentoService(session).add_faixa(
        current_user.tenant_id,
        politica_id,
        PoliticaFaixaCreate(
            horas_antes_min=int(horas_antes_min) if horas_antes_min.strip() else 0,
            horas_antes_max=int(horas_antes_max) if horas_antes_max.strip() else None,
            tipo_retencao=PoliticaRetencaoTipo(tipo_retencao),
            valor_retencao=_dec(valor_retencao),
            ordem=int(ordem) if ordem.strip() else 0,
        ),
    )
    return RedirectResponse(f"/tarifario/cancelamento/{politica_id}/editar", status_code=303)


@router.post(
    "/tarifario/cancelamento/{politica_id}/faixas/{faixa_id}/remover",
    response_class=HTMLResponse,
)
async def politica_remove_faixa(
    session: SessionDep,
    politica_id: uuid.UUID,
    faixa_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("tarifario.politica.editar"))
    ],
) -> RedirectResponse:
    await PoliticaCancelamentoService(session).remove_faixa(politica_id, faixa_id)
    return RedirectResponse(f"/tarifario/cancelamento/{politica_id}/editar", status_code=303)


# ====================================================================== Simulador
@router.get("/tarifario/simular", response_class=HTMLResponse)
async def simular_form(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("tarifario.simular.visualizar"))
    ],
) -> HTMLResponse:
    lookups = await _tarifario_lookups(session, current_user.tenant_id)
    return render(
        request,
        "tarifario/simular.html",
        {
            "resultado": None,
            "error": None,
            "form": {},
            "title": "Simulador de Cotação",
            **lookups,
        },
    )


@router.post("/tarifario/simular", response_class=HTMLResponse)
async def simular_calcular(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("tarifario.simular.visualizar"))
    ],
    filial_id: Annotated[str, Form()],
    categoria_id: Annotated[str, Form()],
    retirada_em: Annotated[str, Form()],
    devolucao_em: Annotated[str, Form()],
    canal: Annotated[str, Form()] = "balcao",
    cliente_id: Annotated[str, Form()] = "",
    parceiro_id: Annotated[str, Form()] = "",
    protecao_ids: Annotated[list[str], Form()] = [],
    taxa_ids: Annotated[list[str], Form()] = [],
    one_way: Annotated[str, Form()] = "",
) -> HTMLResponse:
    lookups = await _tarifario_lookups(session, current_user.tenant_id)
    form = {
        "filial_id": filial_id,
        "categoria_id": categoria_id,
        "canal": canal,
        "retirada_em": retirada_em,
        "devolucao_em": devolucao_em,
        "cliente_id": cliente_id,
        "parceiro_id": parceiro_id,
        "protecao_ids": protecao_ids,
        "taxa_ids": taxa_ids,
        "one_way": bool(one_way),
    }
    ctx = {
        "resultado": None,
        "error": None,
        "form": form,
        "title": "Simulador de Cotação",
        **lookups,
    }
    try:
        resultado = await PricingService(session).calcular(
            PricingQuoteInput(
                tenant_id=current_user.tenant_id,
                filial_id=uuid.UUID(filial_id),
                categoria_id=uuid.UUID(categoria_id),
                canal=TarifarioCanal(canal),
                retirada_em=_datetime(retirada_em) or datetime.now(),
                devolucao_em=_datetime(devolucao_em) or datetime.now(),
                cliente_id=_uuid(cliente_id),
                parceiro_id=_uuid(parceiro_id),
                protecao_ids=_parse_uuid_list(protecao_ids),
                taxa_ids=_parse_uuid_list(taxa_ids),
                one_way=bool(one_way),
            )
        )
        ctx["resultado"] = resultado
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _app_error_message(exc)
        return render(request, "tarifario/simular.html", ctx, status_code=400)
    return render(request, "tarifario/simular.html", ctx)
