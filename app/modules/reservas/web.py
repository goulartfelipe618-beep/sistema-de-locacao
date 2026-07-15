"""Rotas Web (HTML/Jinja2) do módulo Reservas."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_web_permission
from app.core.exceptions import AppError
from app.core.pagination import PageParams
from app.core.templating import render
from app.modules.cadastros.service import ClienteService
from app.modules.cadastros.service_extra import MotoristaService, ParceiroService
from app.modules.frota.service import AcessoriosService, CategoriasService, VeiculoService
from app.modules.identity.service import AuthenticatedUser
from app.modules.reservas.models import ResReservaItem, ResReservaMotorista
from app.modules.reservas.schemas import (
    CotacaoConverterInput,
    CotacaoCreate,
    MotoristaReservaInput,
    ReservaCancelInput,
    ReservaCreate,
)
from app.modules.reservas.service import (
    CalendarioService,
    CotacaoService,
    DisponibilidadeService,
    ReservaItemRepository,
    ReservaMotoristaRepository,
    ReservaService,
)
from app.modules.tarifario.schemas import AcessorioQuoteInput, PricingQuoteInput
from app.modules.tarifario.service import (
    PoliticaCancelamentoService,
    PricingService,
    ProtecaoService,
    TaxaService,
)
from app.modules.tenants.service import FilialService
from app.shared.enums import CotacaoStatus, ReservaOrigem, ReservaStatus, TarifarioCanal

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


def _parse_motoristas(
    motorista_ids: list[str], principal_id: str | None
) -> list[MotoristaReservaInput]:
    ids = _parse_uuid_list(motorista_ids)
    if not ids:
        return []
    principal = _uuid(principal_id)
    return [
        MotoristaReservaInput(
            motorista_id=mid,
            principal=principal == mid if principal else idx == 0,
        )
        for idx, mid in enumerate(ids)
    ]


def _parse_acessorios(
    acessorio_ids: list[str], acessorio_qtds: list[str]
) -> list[AcessorioQuoteInput]:
    items: list[AcessorioQuoteInput] = []
    for idx, raw_id in enumerate(acessorio_ids):
        if not raw_id or not raw_id.strip():
            continue
        qtd_raw = acessorio_qtds[idx] if idx < len(acessorio_qtds) else "1"
        qtd = int(qtd_raw.strip()) if qtd_raw and qtd_raw.strip() else 1
        items.append(AcessorioQuoteInput(id=uuid.UUID(raw_id.strip()), qtd=max(1, qtd)))
    return items


def _form_to_dict(**kwargs: Any) -> dict[str, Any]:
    return {k: v for k, v in kwargs.items()}


async def _ensure_defaults(session: AsyncSession, tenant_id: uuid.UUID) -> None:
    await CategoriasService(session).ensure_defaults(tenant_id)
    await PricingService(session).ensure_defaults(tenant_id)


async def _reservas_lookups(session: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Any]:
    await _ensure_defaults(session, tenant_id)
    categorias = await CategoriasService(session).list_items(PageParams(page=1, size=200))
    filiais = await FilialService(session).list_filiais(PageParams(page=1, size=100))
    clientes = await ClienteService(session).list_clientes(PageParams(page=1, size=300))
    motoristas = await MotoristaService(session).list_items(PageParams(page=1, size=300))
    veiculos = await VeiculoService(session).list_items(PageParams(page=1, size=500))
    parceiros = await ParceiroService(session).list_items(PageParams(page=1, size=200))
    taxas = await TaxaService(session).list_items(PageParams(page=1, size=200))
    protecoes = await ProtecaoService(session).list_items(PageParams(page=1, size=200))
    politicas = await PoliticaCancelamentoService(session).list_items(PageParams(page=1, size=100))
    acessorios = await AcessoriosService(session).list_items(PageParams(page=1, size=200))
    return {
        "categorias": categorias.items,
        "filiais": filiais.items,
        "clientes": clientes.items,
        "motoristas": motoristas.items,
        "veiculos": veiculos.items,
        "parceiros": parceiros.items,
        "taxas_opcionais": taxas.items,
        "protecoes": protecoes.items,
        "politicas": politicas.items,
        "acessorios": acessorios.items,
        "categoria_nomes": {str(c.id): c.nome for c in categorias.items},
        "filial_nomes": {str(f.id): f.name for f in filiais.items},
        "cliente_nomes": {str(c.id): c.nome for c in clientes.items},
        "motorista_nomes": {str(m.id): m.nome for m in motoristas.items},
        "veiculo_placas": {str(v.id): v.placa for v in veiculos.items},
        "parceiro_nomes": {str(p.id): p.nome for p in parceiros.items},
    }


async def _reserva_extras(session: AsyncSession, reserva_id: uuid.UUID) -> dict[str, Any]:
    item_repo = ReservaItemRepository(session)
    mot_repo = ReservaMotoristaRepository(session)
    itens_stmt = select(ResReservaItem).where(
        ResReservaItem.reserva_id == reserva_id,
        ResReservaItem.deleted_at.is_(None),
    )
    mot_stmt = select(ResReservaMotorista).where(
        ResReservaMotorista.reserva_id == reserva_id,
        ResReservaMotorista.deleted_at.is_(None),
    )
    itens = list((await session.execute(itens_stmt)).scalars().all())
    motoristas = list((await session.execute(mot_stmt)).scalars().all())
    return {"itens": itens, "motoristas_vinc": motoristas}


def _build_pricing_input(
    tenant_id: uuid.UUID,
    *,
    filial_retirada_id: uuid.UUID,
    filial_devolucao_id: uuid.UUID,
    categoria_id: uuid.UUID,
    retirada_em: datetime,
    devolucao_em: datetime,
    origem: ReservaOrigem,
    cliente_id: uuid.UUID | None,
    veiculo_id: uuid.UUID | None,
    parceiro_id: uuid.UUID | None,
    protecao_ids: list[uuid.UUID],
    taxa_ids: list[uuid.UUID],
    acessorio_ids: list[AcessorioQuoteInput],
) -> PricingQuoteInput:
    canal_map = {
        ReservaOrigem.BALCAO: TarifarioCanal.BALCAO,
        ReservaOrigem.WEBSITE: TarifarioCanal.SITE,
        ReservaOrigem.APP: TarifarioCanal.APP,
        ReservaOrigem.PARCEIRO: TarifarioCanal.PARCEIRO,
        ReservaOrigem.TELEFONE: TarifarioCanal.TELEFONE,
    }
    return PricingQuoteInput(
        tenant_id=tenant_id,
        filial_id=filial_retirada_id,
        categoria_id=categoria_id,
        canal=canal_map.get(origem, TarifarioCanal.BALCAO),
        retirada_em=retirada_em,
        devolucao_em=devolucao_em,
        veiculo_id=veiculo_id,
        cliente_id=cliente_id,
        parceiro_id=parceiro_id,
        protecao_ids=protecao_ids,
        taxa_ids=taxa_ids,
        acessorio_ids=acessorio_ids,
        one_way=filial_retirada_id != filial_devolucao_id,
    )


# ================================================================ Nova Reserva
@router.get("/reservas/nova", response_class=HTMLResponse)
async def reserva_nova_form(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("reservas.reserva.criar"))
    ],
    filial_retirada_id: str = "",
    filial_devolucao_id: str = "",
    retirada_em: str = "",
    devolucao_em: str = "",
    consultar: str = "",
) -> HTMLResponse:
    lookups = await _reservas_lookups(session, current_user.tenant_id)
    disponibilidade = None
    filial_uuid = _uuid(filial_retirada_id)
    inicio = _datetime(retirada_em)
    fim = _datetime(devolucao_em)
    if consultar and filial_uuid and inicio and fim:
        disponibilidade = await DisponibilidadeService(session).consultar(
            filial_uuid, inicio, fim
        )
    form = _form_to_dict(
        filial_retirada_id=filial_retirada_id,
        filial_devolucao_id=filial_devolucao_id or filial_retirada_id,
        retirada_em=retirada_em,
        devolucao_em=devolucao_em,
        categoria_id="",
        veiculo_id="",
        cliente_id="",
        origem="balcao",
        parceiro_id="",
        motorista_ids=[],
        motorista_principal="",
        protecao_ids=[],
        taxa_ids=[],
        acessorio_ids=[],
        acessorio_qtds=[],
        forma_pagamento_prevista="",
        politica_cancelamento_id="",
        observacoes="",
        desconto="0",
        endereco_entrega="",
    )
    return render(
        request,
        "reservas/nova.html",
        {
            "title": "Nova Reserva",
            "error": None,
            "form": form,
            "disponibilidade": disponibilidade,
            "resultado": None,
            **lookups,
        },
    )


@router.post("/reservas/nova/preco", response_class=HTMLResponse)
async def reserva_nova_preco(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("reservas.reserva.criar"))
    ],
    filial_retirada_id: Annotated[str, Form()],
    filial_devolucao_id: Annotated[str, Form()],
    categoria_id: Annotated[str, Form()],
    retirada_em: Annotated[str, Form()],
    devolucao_em: Annotated[str, Form()],
    origem: Annotated[str, Form()] = "balcao",
    cliente_id: Annotated[str, Form()] = "",
    veiculo_id: Annotated[str, Form()] = "",
    parceiro_id: Annotated[str, Form()] = "",
    protecao_ids: Annotated[list[str], Form()] = [],
    taxa_ids: Annotated[list[str], Form()] = [],
    acessorio_ids: Annotated[list[str], Form()] = [],
    acessorio_qtds: Annotated[list[str], Form()] = [],
    desconto: Annotated[str, Form()] = "0",
) -> HTMLResponse:
    try:
        resultado = await PricingService(session).calcular(
            _build_pricing_input(
                current_user.tenant_id,
                filial_retirada_id=uuid.UUID(filial_retirada_id),
                filial_devolucao_id=uuid.UUID(filial_devolucao_id),
                categoria_id=uuid.UUID(categoria_id),
                retirada_em=_datetime(retirada_em) or datetime.now(tz=UTC),
                devolucao_em=_datetime(devolucao_em) or datetime.now(tz=UTC),
                origem=ReservaOrigem(origem),
                cliente_id=_uuid(cliente_id),
                veiculo_id=_uuid(veiculo_id),
                parceiro_id=_uuid(parceiro_id),
                protecao_ids=_parse_uuid_list(protecao_ids),
                taxa_ids=_parse_uuid_list(taxa_ids),
                acessorio_ids=_parse_acessorios(acessorio_ids, acessorio_qtds),
            )
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        return render(
            request,
            "reservas/_preco_partial.html",
            {"resultado": None, "error": _app_error_message(exc)},
            status_code=400,
        )
    return render(request, "reservas/_preco_partial.html", {"resultado": resultado, "error": None})


@router.post("/reservas/nova", response_class=HTMLResponse)
async def reserva_nova_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("reservas.reserva.criar"))
    ],
    filial_retirada_id: Annotated[str, Form()],
    filial_devolucao_id: Annotated[str, Form()],
    categoria_id: Annotated[str, Form()],
    retirada_em: Annotated[str, Form()],
    devolucao_em: Annotated[str, Form()],
    cliente_id: Annotated[str, Form()],
    origem: Annotated[str, Form()] = "balcao",
    veiculo_id: Annotated[str, Form()] = "",
    endereco_entrega: Annotated[str, Form()] = "",
    parceiro_id: Annotated[str, Form()] = "",
    motorista_ids: Annotated[list[str], Form()] = [],
    motorista_principal: Annotated[str, Form()] = "",
    protecao_ids: Annotated[list[str], Form()] = [],
    taxa_ids: Annotated[list[str], Form()] = [],
    acessorio_ids: Annotated[list[str], Form()] = [],
    acessorio_qtds: Annotated[list[str], Form()] = [],
    forma_pagamento_prevista: Annotated[str, Form()] = "",
    politica_cancelamento_id: Annotated[str, Form()] = "",
    observacoes: Annotated[str, Form()] = "",
    desconto: Annotated[str, Form()] = "0",
) -> HTMLResponse:
    lookups = await _reservas_lookups(session, current_user.tenant_id)
    form = _form_to_dict(
        filial_retirada_id=filial_retirada_id,
        filial_devolucao_id=filial_devolucao_id,
        categoria_id=categoria_id,
        retirada_em=retirada_em,
        devolucao_em=devolucao_em,
        cliente_id=cliente_id,
        origem=origem,
        veiculo_id=veiculo_id,
        endereco_entrega=endereco_entrega,
        parceiro_id=parceiro_id,
        motorista_ids=motorista_ids,
        motorista_principal=motorista_principal,
        protecao_ids=protecao_ids,
        taxa_ids=taxa_ids,
        acessorio_ids=acessorio_ids,
        acessorio_qtds=acessorio_qtds,
        forma_pagamento_prevista=forma_pagamento_prevista,
        politica_cancelamento_id=politica_cancelamento_id,
        observacoes=observacoes,
        desconto=desconto,
    )
    ctx = {
        "title": "Nova Reserva",
        "error": None,
        "form": form,
        "disponibilidade": None,
        "resultado": None,
        **lookups,
    }
    inicio = _datetime(retirada_em)
    fim = _datetime(devolucao_em)
    try:
        if not inicio or not fim:
            raise ValueError("Datas de retirada e devolução são obrigatórias.")
        item = await ReservaService(session).create(
            current_user.tenant_id,
            ReservaCreate(
                cliente_id=uuid.UUID(cliente_id),
                categoria_id=uuid.UUID(categoria_id),
                filial_retirada_id=uuid.UUID(filial_retirada_id),
                filial_devolucao_id=uuid.UUID(filial_devolucao_id),
                retirada_em=inicio,
                devolucao_em=fim,
                origem=ReservaOrigem(origem),
                veiculo_id=_uuid(veiculo_id),
                endereco_entrega=endereco_entrega or None,
                parceiro_id=_uuid(parceiro_id),
                politica_cancelamento_id=_uuid(politica_cancelamento_id),
                forma_pagamento_prevista=forma_pagamento_prevista or None,
                protecao_ids=_parse_uuid_list(protecao_ids),
                taxa_ids=_parse_uuid_list(taxa_ids),
                acessorio_ids=_parse_acessorios(acessorio_ids, acessorio_qtds),
                motoristas=_parse_motoristas(motorista_ids, motorista_principal),
                observacoes=observacoes or None,
                desconto=_dec(desconto),
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        filial_uuid = _uuid(filial_retirada_id)
        if filial_uuid and inicio and fim:
            try:
                ctx["disponibilidade"] = await DisponibilidadeService(session).consultar(
                    filial_uuid, inicio, fim
                )
            except (AppError, ValueError):
                pass
        ctx["error"] = _app_error_message(exc)
        return render(request, "reservas/nova.html", ctx, status_code=400)
    return RedirectResponse(f"/reservas/{item.id}", status_code=303)


# ================================================================ Listagem
@router.get("/reservas", response_class=HTMLResponse)
async def reservas_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("reservas.reserva.visualizar"))
    ],
    page: int = 1,
    q: str = "",
    status: str = "",
) -> HTMLResponse:
    st = ReservaStatus(status) if status else None
    result = await ReservaService(session).list_items(
        PageParams(page=page, size=25), status=st, search=q or None
    )
    lookups = await _reservas_lookups(session, _user.tenant_id)
    return render(
        request,
        "reservas/list.html",
        {
            "page_result": result,
            "q": q,
            "status": status,
            "title": "Reservas",
            **lookups,
        },
    )


# ================================================================ Calendário
@router.get("/reservas/calendario", response_class=HTMLResponse)
async def calendario_view(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("reservas.calendario.visualizar"))
    ],
    filial_id: str = "",
    inicio: str = "",
    fim: str = "",
) -> HTMLResponse:
    lookups = await _reservas_lookups(session, current_user.tenant_id)
    now = datetime.now(tz=UTC)
    inicio_dt = _datetime(inicio) or now.replace(hour=0, minute=0, second=0, microsecond=0)
    fim_dt = _datetime(fim) or (inicio_dt + timedelta(days=7))
    eventos = []
    if filial_id:
        eventos = await CalendarioService(session).list_events(
            inicio_dt,
            fim_dt,
            filial_id=_uuid(filial_id),
        )
    return render(
        request,
        "reservas/calendario.html",
        {
            "title": "Calendário de Reservas",
            "eventos": eventos,
            "filial_id": filial_id,
            "inicio": inicio_dt.strftime("%Y-%m-%dT%H:%M"),
            "fim": fim_dt.strftime("%Y-%m-%dT%H:%M"),
            "error": None,
            **lookups,
        },
    )


@router.post("/reservas/calendario/realocar", response_class=HTMLResponse)
async def calendario_realocar(
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("reservas.reserva.editar"))
    ],
    reserva_id: Annotated[str, Form()],
    novo_veiculo_id: Annotated[str, Form()],
    filial_id: Annotated[str, Form()] = "",
    inicio: Annotated[str, Form()] = "",
    fim: Annotated[str, Form()] = "",
) -> RedirectResponse:
    await CalendarioService(session).realocar(
        uuid.UUID(reserva_id), uuid.UUID(novo_veiculo_id)
    )
    qs = ""
    if filial_id:
        qs = f"?filial_id={filial_id}&inicio={inicio}&fim={fim}"
    return RedirectResponse(f"/reservas/calendario{qs}", status_code=303)


# ================================================================ Disponibilidade
@router.get("/reservas/disponibilidade", response_class=HTMLResponse)
async def disponibilidade_view(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("reservas.disponibilidade.visualizar"))
    ],
    filial_id: str = "",
    categoria_id: str = "",
    inicio: str = "",
    fim: str = "",
) -> HTMLResponse:
    lookups = await _reservas_lookups(session, current_user.tenant_id)
    resultado = None
    error = None
    filial_uuid = _uuid(filial_id)
    inicio_dt = _datetime(inicio)
    fim_dt = _datetime(fim)
    if filial_uuid and inicio_dt and fim_dt:
        try:
            resultado = await DisponibilidadeService(session).consultar(
                filial_uuid,
                inicio_dt,
                fim_dt,
                categoria_id=_uuid(categoria_id),
            )
        except (AppError, ValueError) as exc:
            error = _app_error_message(exc)
    return render(
        request,
        "reservas/disponibilidade.html",
        {
            "title": "Disponibilidade",
            "resultado": resultado,
            "error": error,
            "filial_id": filial_id,
            "categoria_id": categoria_id,
            "inicio": inicio,
            "fim": fim,
            **lookups,
        },
    )


# ================================================================ Cotações
@router.get("/reservas/cotacoes", response_class=HTMLResponse)
async def cotacoes_list(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("reservas.cotacao.visualizar"))
    ],
    page: int = 1,
    q: str = "",
    status: str = "",
) -> HTMLResponse:
    st = CotacaoStatus(status) if status else None
    result = await CotacaoService(session).list_items(
        PageParams(page=page, size=25), status=st, search=q or None
    )
    lookups = await _reservas_lookups(session, current_user.tenant_id)
    return render(
        request,
        "reservas/cotacoes_list.html",
        {
            "page_result": result,
            "q": q,
            "status": status,
            "title": "Cotações",
            **lookups,
        },
    )


@router.get("/reservas/cotacoes/novo", response_class=HTMLResponse)
async def cotacao_novo_form(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("reservas.cotacao.criar"))
    ],
) -> HTMLResponse:
    lookups = await _reservas_lookups(session, current_user.tenant_id)
    return render(
        request,
        "reservas/cotacao_form.html",
        {
            "title": "Nova Cotação",
            "error": None,
            "resultado": None,
            "form": {},
            "cotacao": None,
            **lookups,
        },
    )


@router.post("/reservas/cotacoes/novo", response_class=HTMLResponse)
async def cotacao_novo_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("reservas.cotacao.criar"))
    ],
    filial_retirada_id: Annotated[str, Form()],
    filial_devolucao_id: Annotated[str, Form()],
    categoria_id: Annotated[str, Form()],
    retirada_em: Annotated[str, Form()],
    devolucao_em: Annotated[str, Form()],
    canal: Annotated[str, Form()] = "balcao",
    origem: Annotated[str, Form()] = "balcao",
    cliente_id: Annotated[str, Form()] = "",
    veiculo_id: Annotated[str, Form()] = "",
    parceiro_id: Annotated[str, Form()] = "",
    protecao_ids: Annotated[list[str], Form()] = [],
    taxa_ids: Annotated[list[str], Form()] = [],
    acessorio_ids: Annotated[list[str], Form()] = [],
    acessorio_qtds: Annotated[list[str], Form()] = [],
    observacoes: Annotated[str, Form()] = "",
    validade_horas: Annotated[str, Form()] = "24",
    acao: Annotated[str, Form()] = "salvar",
) -> HTMLResponse:
    lookups = await _reservas_lookups(session, current_user.tenant_id)
    form = _form_to_dict(
        filial_retirada_id=filial_retirada_id,
        filial_devolucao_id=filial_devolucao_id,
        categoria_id=categoria_id,
        retirada_em=retirada_em,
        devolucao_em=devolucao_em,
        canal=canal,
        origem=origem,
        cliente_id=cliente_id,
        veiculo_id=veiculo_id,
        parceiro_id=parceiro_id,
        protecao_ids=protecao_ids,
        taxa_ids=taxa_ids,
        acessorio_ids=acessorio_ids,
        acessorio_qtds=acessorio_qtds,
        observacoes=observacoes,
        validade_horas=validade_horas,
    )
    ctx = {
        "title": "Nova Cotação",
        "error": None,
        "resultado": None,
        "form": form,
        "cotacao": None,
        **lookups,
    }
    try:
        inicio = _datetime(retirada_em)
        fim = _datetime(devolucao_em)
        if not inicio or not fim:
            raise ValueError("Datas de retirada e devolução são obrigatórias.")
        data = CotacaoCreate(
            filial_retirada_id=uuid.UUID(filial_retirada_id),
            filial_devolucao_id=uuid.UUID(filial_devolucao_id),
            categoria_id=uuid.UUID(categoria_id),
            retirada_em=inicio,
            devolucao_em=fim,
            origem=ReservaOrigem(origem),
            canal=TarifarioCanal(canal),
            cliente_id=_uuid(cliente_id),
            veiculo_id=_uuid(veiculo_id),
            parceiro_id=_uuid(parceiro_id),
            protecao_ids=_parse_uuid_list(protecao_ids),
            taxa_ids=_parse_uuid_list(taxa_ids),
            acessorio_ids=_parse_acessorios(acessorio_ids, acessorio_qtds),
            observacoes=observacoes or None,
            validade_horas=int(validade_horas) if validade_horas.strip() else 24,
        )
        if acao == "simular":
            ctx["resultado"] = await PricingService(session).calcular(
                PricingQuoteInput(
                    tenant_id=current_user.tenant_id,
                    filial_id=data.filial_retirada_id,
                    categoria_id=data.categoria_id,
                    canal=data.canal,
                    retirada_em=data.retirada_em,
                    devolucao_em=data.devolucao_em,
                    veiculo_id=data.veiculo_id,
                    cliente_id=data.cliente_id,
                    parceiro_id=data.parceiro_id,
                    protecao_ids=data.protecao_ids,
                    taxa_ids=data.taxa_ids,
                    acessorio_ids=data.acessorio_ids,
                    one_way=data.filial_retirada_id != data.filial_devolucao_id,
                )
            )
            return render(request, "reservas/cotacao_form.html", ctx)
        item = await CotacaoService(session).create(current_user.tenant_id, data)
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _app_error_message(exc)
        return render(request, "reservas/cotacao_form.html", ctx, status_code=400)
    return RedirectResponse("/reservas/cotacoes", status_code=303)


@router.post("/reservas/cotacoes/{cotacao_id}/converter", response_class=HTMLResponse)
async def cotacao_converter(
    session: SessionDep,
    cotacao_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("reservas.cotacao.editar"))
    ],
    cliente_id: Annotated[str, Form()],
    motorista_ids: Annotated[list[str], Form()] = [],
    motorista_principal: Annotated[str, Form()] = "",
    forma_pagamento_prevista: Annotated[str, Form()] = "",
    politica_cancelamento_id: Annotated[str, Form()] = "",
    observacoes: Annotated[str, Form()] = "",
) -> RedirectResponse:
    reserva = await CotacaoService(session).converter_em_reserva(
        cotacao_id,
        CotacaoConverterInput(
            cliente_id=uuid.UUID(cliente_id),
            motoristas=_parse_motoristas(motorista_ids, motorista_principal),
            forma_pagamento_prevista=forma_pagamento_prevista or None,
            politica_cancelamento_id=_uuid(politica_cancelamento_id),
            observacoes=observacoes or None,
        ),
    )
    return RedirectResponse(f"/reservas/{reserva.id}", status_code=303)


# ================================================================ Detalhe / Ações
@router.get("/reservas/{reserva_id}", response_class=HTMLResponse)
async def reserva_detalhe(
    request: Request,
    session: SessionDep,
    reserva_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("reservas.reserva.visualizar"))
    ],
) -> HTMLResponse:
    reserva = await ReservaService(session).get(reserva_id)
    lookups = await _reservas_lookups(session, _user.tenant_id)
    extras = await _reserva_extras(session, reserva_id)
    return render(
        request,
        "reservas/detalhe.html",
        {
            "reserva": reserva,
            "title": f"Reserva {reserva.numero}",
            "error": None,
            **extras,
            **lookups,
        },
    )


@router.post("/reservas/{reserva_id}/confirmar", response_class=HTMLResponse)
async def reserva_confirmar(
    session: SessionDep,
    reserva_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("reservas.reserva.editar"))
    ],
) -> RedirectResponse:
    await ReservaService(session).confirmar(reserva_id)
    return RedirectResponse(f"/reservas/{reserva_id}", status_code=303)


@router.post("/reservas/{reserva_id}/aprovar", response_class=HTMLResponse)
async def reserva_aprovar(
    session: SessionDep,
    reserva_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("reservas.reserva.aprovar"))
    ],
) -> RedirectResponse:
    await ReservaService(session).aprovar_bloqueado(reserva_id)
    return RedirectResponse(f"/reservas/{reserva_id}", status_code=303)


@router.post("/reservas/{reserva_id}/cancelar", response_class=HTMLResponse)
async def reserva_cancelar(
    session: SessionDep,
    reserva_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("reservas.reserva.cancelar"))
    ],
    motivo: Annotated[str, Form()],
) -> RedirectResponse:
    await ReservaService(session).cancelar(
        reserva_id, ReservaCancelInput(motivo=motivo)
    )
    return RedirectResponse(f"/reservas/{reserva_id}", status_code=303)


@router.post("/reservas/{reserva_id}/no-show", response_class=HTMLResponse)
async def reserva_no_show(
    session: SessionDep,
    reserva_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("reservas.reserva.editar"))
    ],
) -> RedirectResponse:
    await ReservaService(session).marcar_no_show(reserva_id)
    return RedirectResponse(f"/reservas/{reserva_id}", status_code=303)
