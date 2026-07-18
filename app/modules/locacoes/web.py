"""Rotas Web (HTML/Jinja2) do módulo Locações."""

from __future__ import annotations

import base64
import re
import uuid
from datetime import datetime
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
from app.core.storage import StorageService, storage_service
from app.core.templating import render
from app.modules.cadastros.service import ClienteService
from app.modules.cadastros.service_extra import MotoristaService, ParceiroService, FornecedorService
from app.modules.frota.service import AcessoriosService, CategoriasService, VeiculoService
from app.modules.identity.service import AuthenticatedUser
from app.modules.locacoes.models import LocContratoAditivo, LocContratoItem, LocContratoMotorista
from app.modules.locacoes.schemas import (
    AvariaCheckinInput,
    AvariaCreate,
    AvariaResponsabilidadeInput,
    AvariaUpdate,
    CheckoutConcluirInput,
    CheckinConcluirInput,
    ContratoCancelInput,
    ContratoCreate,
    MotoristaContratoInput,
    MultaCreate,
    MultaUpdate,
    ReabrirInput,
    RenovacaoInput,
    VistoriaFotoInput,
)
from app.modules.locacoes.service import (
    AvariaService,
    CheckinService,
    CheckoutService,
    ContratoService,
    EncerramentoService,
    MultaService,
    RenovacaoService,
)
from app.modules.reservas.schemas import MotoristaReservaInput
from app.modules.reservas.service import ReservaService
from app.modules.tarifario.schemas import AcessorioQuoteInput, PricingQuoteInput
from app.modules.tarifario.service import (
    PoliticaCancelamentoService,
    PricingService,
    ProtecaoService,
    TaxaService,
)
from app.modules.tenants.service import FilialService
from app.shared.enums import (
    AvariaOrigem,
    AvariaResponsabilidade,
    AvariaSeveridade,
    AvariaStatus,
    ContratoCondicaoPagamento,
    ContratoStatus,
    MultaStatus,
    ReservaOrigem,
    TarifarioCanal,
)

router = APIRouter()
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]

_FOTO_ANGULOS = [
    "frente",
    "traseira",
    "lateral_esquerda",
    "lateral_direita",
    "painel",
    "odometro",
]


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


def _checklist_from_text(raw: str) -> dict:
    items: dict[str, bool] = {}
    for line in raw.splitlines():
        text = line.strip()
        if text:
            items[text] = True
    return items


async def _ensure_defaults(session: AsyncSession, tenant_id: uuid.UUID) -> None:
    await CategoriasService(session).ensure_defaults(tenant_id)
    await PricingService(session).ensure_defaults(tenant_id)


async def _locacoes_lookups(session: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Any]:
    await _ensure_defaults(session, tenant_id)
    categorias = await CategoriasService(session).list_items(PageParams(page=1, size=200))
    filiais = await FilialService(session).list_filiais(PageParams(page=1, size=100))
    clientes = await ClienteService(session).list_clientes(PageParams(page=1, size=300))
    motoristas = await MotoristaService(session).list_items(PageParams(page=1, size=300))
    veiculos = await VeiculoService(session).list_items(PageParams(page=1, size=500))
    parceiros = await ParceiroService(session).list_items(PageParams(page=1, size=200))
    fornecedores = await FornecedorService(session).list_items(PageParams(page=1, size=200))
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
        "fornecedor_nomes": {str(f.id): f.nome for f in fornecedores.items},
    }


async def _contrato_extras(session: AsyncSession, contrato_id: uuid.UUID) -> dict[str, Any]:
    itens_stmt = select(LocContratoItem).where(
        LocContratoItem.contrato_id == contrato_id,
        LocContratoItem.deleted_at.is_(None),
    )
    mot_stmt = select(LocContratoMotorista).where(
        LocContratoMotorista.contrato_id == contrato_id,
        LocContratoMotorista.deleted_at.is_(None),
    )
    adit_stmt = (
        select(LocContratoAditivo)
        .where(
            LocContratoAditivo.contrato_id == contrato_id,
            LocContratoAditivo.deleted_at.is_(None),
        )
        .order_by(LocContratoAditivo.versao.desc())
    )
    itens = list((await session.execute(itens_stmt)).scalars().all())
    motoristas = list((await session.execute(mot_stmt)).scalars().all())
    aditivos = list((await session.execute(adit_stmt)).scalars().all())
    return {"itens": itens, "motoristas_vinc": motoristas, "aditivos": aditivos}


def _persist_assinatura_canvas(tenant_id: uuid.UUID, data_url: str) -> tuple[str, str] | None:
    """Grava assinatura PNG (canvas) no R2 ou inline compacto para dev."""
    raw = (data_url or "").strip()
    if not raw:
        return None
    match = re.match(r"data:image/png;base64,(.+)", raw, re.DOTALL)
    if not match:
        return None
    b64 = match.group(1).strip()
    try:
        png = base64.b64decode(b64)
    except (ValueError, TypeError):
        return None
    if storage_service.is_configured():
        key = StorageService.build_key(tenant_id, "locacoes", "assinatura", "assinatura.png")
        storage_service.upload_bytes(key, png, "image/png")
        return ("canvas", key)
    if len(b64) <= 480:
        return ("canvas", f"b64:{b64}")
    return None


def _parse_fotos_vistoria(foto_keys: dict[str, str]) -> list[VistoriaFotoInput]:
    fotos: list[VistoriaFotoInput] = []
    for idx, angulo in enumerate(_FOTO_ANGULOS):
        key = (foto_keys.get(angulo) or "").strip()
        if key:
            fotos.append(VistoriaFotoInput(storage_key=key, angulo=angulo, ordem=idx))
    return fotos


def _parse_avarias_checkin(
    localizacoes: list[str],
    severidades: list[str],
    laudos: list[str],
    valores: list[str],
) -> list[AvariaCheckinInput]:
    avarias: list[AvariaCheckinInput] = []
    for idx, loc in enumerate(localizacoes):
        loc = (loc or "").strip()
        if not loc:
            continue
        sev_raw = severidades[idx] if idx < len(severidades) else "leve"
        laudo = laudos[idx].strip() if idx < len(laudos) and laudos[idx] else None
        val_raw = valores[idx] if idx < len(valores) else ""
        valor = _dec(val_raw) if val_raw and val_raw.strip() else None
        avarias.append(
            AvariaCheckinInput(
                localizacao=loc,
                severidade=AvariaSeveridade(sev_raw),
                laudo=laudo,
                valor_reparo=valor,
            )
        )
    return avarias


def _contrato_status_badge(status: ContratoStatus) -> str:
    if status in {ContratoStatus.ATIVO, ContratoStatus.ENCERRADO}:
        return "badge-success"
    if status in {ContratoStatus.CANCELADO}:
        return "badge-danger"
    if status == ContratoStatus.ENCERRADO_PENDENCIA:
        return "badge-warning"
    return "badge-warning"


# ================================================================ Contratos
@router.get("/locacoes/contratos", response_class=HTMLResponse)
async def contratos_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("locacoes.contrato.visualizar"))
    ],
    page: int = 1,
    q: str = "",
    status: str = "",
) -> HTMLResponse:
    st = ContratoStatus(status) if status else None
    result = await ContratoService(session).list_items(
        PageParams(page=page, size=25), status=st, search=q or None
    )
    lookups = await _locacoes_lookups(session, _user.tenant_id)
    return render(
        request,
        "locacoes/contratos_list.html",
        {
            "page_result": result,
            "q": q,
            "status": status,
            "title": "Contratos",
            "status_badge": _contrato_status_badge,
            **lookups,
        },
    )


@router.get("/locacoes/contratos/novo", response_class=HTMLResponse)
async def contrato_novo_form(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("locacoes.contrato.criar"))
    ],
) -> HTMLResponse:
    lookups = await _locacoes_lookups(session, current_user.tenant_id)
    form = _form_to_dict(
        filial_retirada_id="",
        filial_devolucao_id="",
        retirada_prevista_em="",
        devolucao_prevista_em="",
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
        forma_pagamento="",
        condicao="avista",
        caucao="0",
        desconto="0",
        clausulas_combustivel="",
        observacoes="",
    )
    return render(
        request,
        "locacoes/contrato_form.html",
        {"title": "Novo Contrato", "error": None, "form": form, **lookups},
    )


@router.post("/locacoes/contratos/novo", response_class=HTMLResponse)
async def contrato_novo_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("locacoes.contrato.criar"))
    ],
    filial_retirada_id: Annotated[str, Form()],
    filial_devolucao_id: Annotated[str, Form()],
    categoria_id: Annotated[str, Form()],
    retirada_prevista_em: Annotated[str, Form()],
    devolucao_prevista_em: Annotated[str, Form()],
    cliente_id: Annotated[str, Form()],
    veiculo_id: Annotated[str, Form()],
    origem: Annotated[str, Form()] = "balcao",
    parceiro_id: Annotated[str, Form()] = "",
    motorista_ids: Annotated[list[str], Form()] = [],
    motorista_principal: Annotated[str, Form()] = "",
    protecao_ids: Annotated[list[str], Form()] = [],
    taxa_ids: Annotated[list[str], Form()] = [],
    acessorio_ids: Annotated[list[str], Form()] = [],
    acessorio_qtds: Annotated[list[str], Form()] = [],
    forma_pagamento: Annotated[str, Form()] = "",
    condicao: Annotated[str, Form()] = "avista",
    caucao: Annotated[str, Form()] = "0",
    desconto: Annotated[str, Form()] = "0",
    clausulas_combustivel: Annotated[str, Form()] = "",
    observacoes: Annotated[str, Form()] = "",
) -> HTMLResponse:
    lookups = await _locacoes_lookups(session, current_user.tenant_id)
    form = _form_to_dict(
        filial_retirada_id=filial_retirada_id,
        filial_devolucao_id=filial_devolucao_id,
        categoria_id=categoria_id,
        retirada_prevista_em=retirada_prevista_em,
        devolucao_prevista_em=devolucao_prevista_em,
        cliente_id=cliente_id,
        veiculo_id=veiculo_id,
        origem=origem,
        parceiro_id=parceiro_id,
        motorista_ids=motorista_ids,
        motorista_principal=motorista_principal,
        protecao_ids=protecao_ids,
        taxa_ids=taxa_ids,
        acessorio_ids=acessorio_ids,
        acessorio_qtds=acessorio_qtds,
        forma_pagamento=forma_pagamento,
        condicao=condicao,
        caucao=caucao,
        desconto=desconto,
        clausulas_combustivel=clausulas_combustivel,
        observacoes=observacoes,
    )
    ctx = {"title": "Novo Contrato", "error": None, "form": form, **lookups}
    inicio = _datetime(retirada_prevista_em)
    fim = _datetime(devolucao_prevista_em)
    try:
        if not inicio or not fim:
            raise ValueError("Datas de retirada e devolução são obrigatórias.")
        motoristas = [
            MotoristaContratoInput(
                motorista_id=m.motorista_id,
                principal=m.principal,
            )
            for m in _parse_motoristas(motorista_ids, motorista_principal)
        ]
        item = await ContratoService(session).create(
            current_user.tenant_id,
            ContratoCreate(
                cliente_id=uuid.UUID(cliente_id),
                veiculo_id=uuid.UUID(veiculo_id),
                categoria_id=uuid.UUID(categoria_id),
                filial_retirada_id=uuid.UUID(filial_retirada_id),
                filial_devolucao_id=uuid.UUID(filial_devolucao_id),
                retirada_prevista_em=inicio,
                devolucao_prevista_em=fim,
                origem=ReservaOrigem(origem),
                parceiro_id=_uuid(parceiro_id),
                forma_pagamento=forma_pagamento or None,
                condicao=ContratoCondicaoPagamento(condicao),
                caucao=_dec(caucao),
                protecao_ids=_parse_uuid_list(protecao_ids),
                taxa_ids=_parse_uuid_list(taxa_ids),
                acessorio_ids=_parse_acessorios(acessorio_ids, acessorio_qtds),
                motoristas=motoristas,
                desconto=_dec(desconto),
                clausulas_combustivel=clausulas_combustivel or None,
                observacoes=observacoes or None,
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _app_error_message(exc)
        return render(request, "locacoes/contrato_form.html", ctx, status_code=400)
    return RedirectResponse(f"/locacoes/contratos/{item.id}", status_code=303)


@router.post("/locacoes/contratos/de-reserva/{reserva_id}", response_class=HTMLResponse)
async def contrato_de_reserva(
    session: SessionDep,
    reserva_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("locacoes.contrato.criar"))
    ],
) -> RedirectResponse:
    contrato = await ReservaService(session).create_contrato(reserva_id)
    return RedirectResponse(f"/locacoes/contratos/{contrato.id}", status_code=303)


@router.get("/locacoes/contratos/{contrato_id}", response_class=HTMLResponse)
async def contrato_detalhe(
    request: Request,
    session: SessionDep,
    contrato_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("locacoes.contrato.visualizar"))
    ],
) -> HTMLResponse:
    contrato = await ContratoService(session).get(contrato_id)
    cliente = await ClienteService(session).get(contrato.cliente_id)
    lookups = await _locacoes_lookups(session, _user.tenant_id)
    extras = await _contrato_extras(session, contrato_id)
    return render(
        request,
        "locacoes/contrato_detalhe.html",
        {
            "contrato": contrato,
            "cliente": cliente,
            "title": f"Contrato {contrato.numero}",
            "error": None,
            "status_badge": _contrato_status_badge(contrato.status),
            **extras,
            **lookups,
        },
    )


@router.post("/locacoes/contratos/{contrato_id}/cancelar", response_class=HTMLResponse)
async def contrato_cancelar(
    session: SessionDep,
    contrato_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("locacoes.contrato.cancelar"))
    ],
    motivo: Annotated[str, Form()],
) -> RedirectResponse:
    await ContratoService(session).cancelar(
        contrato_id, ContratoCancelInput(motivo=motivo)
    )
    return RedirectResponse(f"/locacoes/contratos/{contrato_id}", status_code=303)


# ================================================================ Check-out
@router.get("/locacoes/checkout", response_class=HTMLResponse)
async def checkout_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("locacoes.checkout.visualizar"))
    ],
    page: int = 1,
) -> HTMLResponse:
    result = await ContratoService(session).list_items(
        PageParams(page=page, size=25),
        statuses={ContratoStatus.AGUARDANDO_CHECKOUT, ContratoStatus.RASCUNHO},
    )
    lookups = await _locacoes_lookups(session, _user.tenant_id)
    return render(
        request,
        "locacoes/checkout_list.html",
        {
            "page_result": result,
            "title": "Check-out",
            "status_badge": _contrato_status_badge,
            **lookups,
        },
    )


@router.get("/locacoes/checkout/{contrato_id}", response_class=HTMLResponse)
async def checkout_form(
    request: Request,
    session: SessionDep,
    contrato_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("locacoes.checkout.visualizar"))
    ],
) -> HTMLResponse:
    contrato = await ContratoService(session).get(contrato_id)
    if contrato.status == ContratoStatus.RASCUNHO:
        if (
            current_user.is_superuser
            or "locacoes.checkout.editar" in current_user.permissions
        ):
            contrato = await CheckoutService(session).iniciar(contrato_id)
    lookups = await _locacoes_lookups(session, current_user.tenant_id)
    veiculo = await VeiculoService(session).get(contrato.veiculo_id)
    return render(
        request,
        "locacoes/checkout_form.html",
        {
            "contrato": contrato,
            "veiculo": veiculo,
            "title": f"Check-out — {contrato.numero}",
            "error": None,
            "foto_angulos": _FOTO_ANGULOS,
            **lookups,
        },
    )


@router.post("/locacoes/checkout/{contrato_id}/concluir", response_class=HTMLResponse)
async def checkout_concluir(
    request: Request,
    session: SessionDep,
    contrato_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("locacoes.checkout.criar"))
    ],
    km: Annotated[str, Form()],
    combustivel_nivel: Annotated[str, Form()],
    checklist: Annotated[str, Form()] = "",
    caucao_confirmada: Annotated[str, Form()] = "",
    allow_force: Annotated[str, Form()] = "",
    observacoes: Annotated[str, Form()] = "",
    foto_frente: Annotated[str, Form()] = "",
    foto_traseira: Annotated[str, Form()] = "",
    foto_lateral_esquerda: Annotated[str, Form()] = "",
    foto_lateral_direita: Annotated[str, Form()] = "",
    foto_painel: Annotated[str, Form()] = "",
    foto_odometro: Annotated[str, Form()] = "",
    assinatura_data: Annotated[str, Form()] = "",
) -> HTMLResponse:
    contrato = await ContratoService(session).get(contrato_id)
    lookups = await _locacoes_lookups(session, current_user.tenant_id)
    veiculo = await VeiculoService(session).get(contrato.veiculo_id)
    foto_map = {
        "frente": foto_frente,
        "traseira": foto_traseira,
        "lateral_esquerda": foto_lateral_esquerda,
        "lateral_direita": foto_lateral_direita,
        "painel": foto_painel,
        "odometro": foto_odometro,
    }
    ctx = {
        "contrato": contrato,
        "veiculo": veiculo,
        "title": f"Check-out — {contrato.numero}",
        "error": None,
        "foto_angulos": _FOTO_ANGULOS,
        **lookups,
    }
    try:
        assinatura = _persist_assinatura_canvas(current_user.tenant_id, assinatura_data)
        await CheckoutService(session).concluir(
            contrato_id,
            CheckoutConcluirInput(
                km=int(km),
                combustivel_nivel=int(combustivel_nivel),
                checklist_json=_checklist_from_text(checklist),
                fotos=_parse_fotos_vistoria(foto_map),
                caucao_confirmada=caucao_confirmada in ("on", "true", "1"),
                allow_force=allow_force in ("on", "true", "1"),
                realizado_por_user_id=current_user.id,
                observacoes=observacoes or None,
                assinatura_tipo=assinatura[0] if assinatura else None,
                assinatura_key=assinatura[1] if assinatura else None,
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _app_error_message(exc)
        return render(request, "locacoes/checkout_form.html", ctx, status_code=400)
    return RedirectResponse(f"/locacoes/contratos/{contrato_id}", status_code=303)


# ================================================================ Check-in
@router.get("/locacoes/checkin", response_class=HTMLResponse)
async def checkin_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("locacoes.checkin.visualizar"))
    ],
    page: int = 1,
) -> HTMLResponse:
    result = await ContratoService(session).list_items(
        PageParams(page=page, size=25),
        statuses={ContratoStatus.ATIVO, ContratoStatus.AGUARDANDO_CHECKIN},
    )
    lookups = await _locacoes_lookups(session, _user.tenant_id)
    return render(
        request,
        "locacoes/checkin_list.html",
        {
            "page_result": result,
            "title": "Check-in",
            "status_badge": _contrato_status_badge,
            **lookups,
        },
    )


@router.get("/locacoes/checkin/{contrato_id}", response_class=HTMLResponse)
async def checkin_form(
    request: Request,
    session: SessionDep,
    contrato_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("locacoes.checkin.visualizar"))
    ],
) -> HTMLResponse:
    contrato = await ContratoService(session).get(contrato_id)
    lookups = await _locacoes_lookups(session, current_user.tenant_id)
    veiculo = await VeiculoService(session).get(contrato.veiculo_id)
    return render(
        request,
        "locacoes/checkin_form.html",
        {
            "contrato": contrato,
            "veiculo": veiculo,
            "title": f"Check-in — {contrato.numero}",
            "error": None,
            "foto_angulos": _FOTO_ANGULOS,
            **lookups,
        },
    )


@router.post("/locacoes/checkin/{contrato_id}/concluir", response_class=HTMLResponse)
async def checkin_concluir(
    request: Request,
    session: SessionDep,
    contrato_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("locacoes.checkin.criar"))
    ],
    km_entrada: Annotated[str, Form()],
    combustivel_entrada: Annotated[str, Form()],
    checklist: Annotated[str, Form()] = "",
    atraso_horas: Annotated[str, Form()] = "0",
    caucao_devolvida: Annotated[str, Form()] = "0",
    caucao_retida: Annotated[str, Form()] = "0",
    valor_km_excedente: Annotated[str, Form()] = "0",
    pendencia_financeira: Annotated[str, Form()] = "",
    observacoes: Annotated[str, Form()] = "",
    avaria_localizacao: Annotated[str, Form()] = "",
    avaria_severidade: Annotated[str, Form()] = "leve",
    avaria_laudo: Annotated[str, Form()] = "",
    avaria_valor: Annotated[str, Form()] = "",
    foto_frente: Annotated[str, Form()] = "",
    foto_traseira: Annotated[str, Form()] = "",
    foto_lateral_esquerda: Annotated[str, Form()] = "",
    foto_lateral_direita: Annotated[str, Form()] = "",
    foto_painel: Annotated[str, Form()] = "",
    foto_odometro: Annotated[str, Form()] = "",
) -> HTMLResponse:
    contrato = await ContratoService(session).get(contrato_id)
    lookups = await _locacoes_lookups(session, current_user.tenant_id)
    veiculo = await VeiculoService(session).get(contrato.veiculo_id)
    foto_map = {
        "frente": foto_frente,
        "traseira": foto_traseira,
        "lateral_esquerda": foto_lateral_esquerda,
        "lateral_direita": foto_lateral_direita,
        "painel": foto_painel,
        "odometro": foto_odometro,
    }
    ctx = {
        "contrato": contrato,
        "veiculo": veiculo,
        "title": f"Check-in — {contrato.numero}",
        "error": None,
        "foto_angulos": _FOTO_ANGULOS,
        **lookups,
    }
    try:
        await CheckinService(session).concluir(
            contrato_id,
            CheckinConcluirInput(
                km_entrada=int(km_entrada),
                combustivel_entrada=int(combustivel_entrada),
                checklist_json=_checklist_from_text(checklist),
                fotos=_parse_fotos_vistoria(foto_map),
                horas_atraso=_dec(atraso_horas),
                valor_km_excedente=_dec(valor_km_excedente),
                caucao_devolvida=_dec(caucao_devolvida),
                caucao_retida=_dec(caucao_retida),
                pendencia_financeira=pendencia_financeira in ("on", "true", "1"),
                avarias=_parse_avarias_checkin(
                    [avaria_localizacao],
                    [avaria_severidade],
                    [avaria_laudo],
                    [avaria_valor],
                ),
                realizado_por_user_id=current_user.id,
                observacoes=observacoes or None,
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _app_error_message(exc)
        return render(request, "locacoes/checkin_form.html", ctx, status_code=400)
    return RedirectResponse(f"/locacoes/contratos/{contrato_id}", status_code=303)


# ================================================================ Renovações
@router.get("/locacoes/renovacoes", response_class=HTMLResponse)
async def renovacoes_view(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("locacoes.renovacao.visualizar"))
    ],
    page: int = 1,
    contrato_id: str = "",
    nova_devolucao: str = "",
) -> HTMLResponse:
    result = await ContratoService(session).list_items(
        PageParams(page=page, size=25),
        status=ContratoStatus.ATIVO,
    )
    lookups = await _locacoes_lookups(session, current_user.tenant_id)
    preview = None
    preview_error = None
    contrato_uuid = _uuid(contrato_id)
    nova_dt = _datetime(nova_devolucao)
    if contrato_uuid and nova_dt:
        try:
            contrato = await ContratoService(session).get(contrato_uuid)
            quote = await PricingService(session).calcular(
                PricingQuoteInput(
                    tenant_id=current_user.tenant_id,
                    filial_id=contrato.filial_retirada_id,
                    categoria_id=contrato.categoria_id,
                    canal=TarifarioCanal.BALCAO,
                    retirada_em=contrato.devolucao_prevista_em,
                    devolucao_em=nova_dt,
                    veiculo_id=contrato.veiculo_id,
                    cliente_id=contrato.cliente_id,
                )
            )
            preview = {
                "dias_extra": quote.dias,
                "valor_aditivo": quote.total,
                "nova_devolucao": nova_dt,
            }
        except (AppError, ValueError) as exc:
            preview_error = _app_error_message(exc)
    return render(
        request,
        "locacoes/renovacoes.html",
        {
            "page_result": result,
            "title": "Renovações",
            "contrato_id": contrato_id,
            "nova_devolucao": nova_devolucao,
            "preview": preview,
            "preview_error": preview_error,
            **lookups,
        },
    )


@router.post("/locacoes/renovacoes", response_class=HTMLResponse)
async def renovacoes_renovar(
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("locacoes.renovacao.criar"))
    ],
    contrato_id: Annotated[str, Form()],
    nova_devolucao: Annotated[str, Form()],
    motivo: Annotated[str, Form()] = "",
) -> RedirectResponse:
    nova_dt = _datetime(nova_devolucao)
    if not nova_dt:
        raise ValueError("Nova data de devolução é obrigatória.")
    await RenovacaoService(session).renovar(
        uuid.UUID(contrato_id),
        RenovacaoInput(nova_devolucao=nova_dt, motivo=motivo or None),
    )
    return RedirectResponse(
        f"/locacoes/contratos/{contrato_id}",
        status_code=303,
    )


# ================================================================ Encerramentos
@router.get("/locacoes/encerramentos", response_class=HTMLResponse)
async def encerramentos_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser,
        Depends(require_web_permission("locacoes.encerramento.visualizar")),
    ],
    page: int = 1,
    status: str = "",
    q: str = "",
) -> HTMLResponse:
    st = ContratoStatus(status) if status else None
    if st:
        result = await ContratoService(session).list_items(
            PageParams(page=page, size=25),
            status=st,
            search=q or None,
        )
    else:
        result = await EncerramentoService(session).list_encerrados(
            PageParams(page=page, size=25),
            search=q or None,
        )
    lookups = await _locacoes_lookups(session, _user.tenant_id)
    return render(
        request,
        "locacoes/encerramentos.html",
        {
            "page_result": result,
            "title": "Encerramentos",
            "status": status,
            "q": q,
            "status_badge": _contrato_status_badge,
            **lookups,
        },
    )


@router.post("/locacoes/encerramentos/{contrato_id}/reabrir", response_class=HTMLResponse)
async def encerramento_reabrir(
    session: SessionDep,
    contrato_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser,
        Depends(require_web_permission("locacoes.encerramento.reabrir")),
    ],
    motivo: Annotated[str, Form()],
) -> RedirectResponse:
    await EncerramentoService(session).reabrir(
        contrato_id, ReabrirInput(motivo=motivo)
    )
    return RedirectResponse(f"/locacoes/contratos/{contrato_id}", status_code=303)


# ================================================================ Multas
@router.get("/locacoes/multas", response_class=HTMLResponse)
async def multas_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("locacoes.multa.visualizar"))
    ],
    page: int = 1,
    status: str = "",
) -> HTMLResponse:
    st = MultaStatus(status) if status else None
    result = await MultaService(session).list_items(
        PageParams(page=page, size=25), status=st
    )
    lookups = await _locacoes_lookups(session, _user.tenant_id)
    return render(
        request,
        "locacoes/multas_list.html",
        {
            "page_result": result,
            "title": "Multas e Infrações",
            "status": status,
            **lookups,
        },
    )


@router.get("/locacoes/multas/novo", response_class=HTMLResponse)
async def multa_novo_form(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("locacoes.multa.criar"))
    ],
) -> HTMLResponse:
    lookups = await _locacoes_lookups(session, current_user.tenant_id)
    return render(
        request,
        "locacoes/multa_form.html",
        {
            "title": "Nova Multa",
            "error": None,
            "item": None,
            "action": "/locacoes/multas/novo",
            **lookups,
        },
    )


@router.post("/locacoes/multas/novo", response_class=HTMLResponse)
async def multa_novo_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("locacoes.multa.criar"))
    ],
    veiculo_id: Annotated[str, Form()],
    ocorrido_em: Annotated[str, Form()],
    orgao: Annotated[str, Form()],
    codigo_infracao: Annotated[str, Form()],
    valor: Annotated[str, Form()],
    pontuacao: Annotated[str, Form()] = "0",
    ait: Annotated[str, Form()] = "",
    taxa_admin: Annotated[str, Form()] = "0",
    observacoes: Annotated[str, Form()] = "",
) -> HTMLResponse:
    lookups = await _locacoes_lookups(session, current_user.tenant_id)
    ctx = {
        "title": "Nova Multa",
        "error": None,
        "item": None,
        "action": "/locacoes/multas/novo",
        **lookups,
    }
    try:
        ocorrido = _datetime(ocorrido_em)
        if not ocorrido:
            raise ValueError("Data/hora da ocorrência é obrigatória.")
        await MultaService(session).create(
            current_user.tenant_id,
            MultaCreate(
                veiculo_id=uuid.UUID(veiculo_id),
                ocorrido_em=ocorrido,
                orgao=orgao,
                codigo_infracao=codigo_infracao,
                valor=_dec(valor),
                pontuacao=int(pontuacao) if pontuacao.strip() else 0,
                ait=ait or None,
                taxa_admin=_dec(taxa_admin),
                observacoes=observacoes or None,
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _app_error_message(exc)
        return render(request, "locacoes/multa_form.html", ctx, status_code=400)
    return RedirectResponse("/locacoes/multas", status_code=303)


@router.get("/locacoes/multas/{multa_id}/editar", response_class=HTMLResponse)
async def multa_editar_form(
    request: Request,
    session: SessionDep,
    multa_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("locacoes.multa.editar"))
    ],
) -> HTMLResponse:
    item = await MultaService(session).get(multa_id)
    lookups = await _locacoes_lookups(session, _user.tenant_id)
    return render(
        request,
        "locacoes/multa_form.html",
        {
            "title": f"Editar Multa",
            "error": None,
            "item": item,
            "action": f"/locacoes/multas/{multa_id}/editar",
            **lookups,
        },
    )


@router.post("/locacoes/multas/{multa_id}/editar", response_class=HTMLResponse)
async def multa_editar_save(
    request: Request,
    session: SessionDep,
    multa_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("locacoes.multa.editar"))
    ],
    orgao: Annotated[str, Form()] = "",
    codigo_infracao: Annotated[str, Form()] = "",
    valor: Annotated[str, Form()] = "",
    pontuacao: Annotated[str, Form()] = "",
    ait: Annotated[str, Form()] = "",
    taxa_admin: Annotated[str, Form()] = "",
    observacoes: Annotated[str, Form()] = "",
) -> HTMLResponse:
    item = await MultaService(session).get(multa_id)
    lookups = await _locacoes_lookups(session, _user.tenant_id)
    ctx = {
        "title": "Editar Multa",
        "error": None,
        "item": item,
        "action": f"/locacoes/multas/{multa_id}/editar",
        **lookups,
    }
    try:
        payload: dict[str, Any] = {}
        if orgao.strip():
            payload["orgao"] = orgao
        if codigo_infracao.strip():
            payload["codigo_infracao"] = codigo_infracao
        if valor.strip():
            payload["valor"] = _dec(valor)
        if pontuacao.strip():
            payload["pontuacao"] = int(pontuacao)
        if ait.strip():
            payload["ait"] = ait
        if taxa_admin.strip():
            payload["taxa_admin"] = _dec(taxa_admin)
        if observacoes.strip():
            payload["observacoes"] = observacoes
        await MultaService(session).update(multa_id, MultaUpdate(**payload))
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _app_error_message(exc)
        return render(request, "locacoes/multa_form.html", ctx, status_code=400)
    return RedirectResponse("/locacoes/multas", status_code=303)


@router.post("/locacoes/multas/{multa_id}/excluir", response_class=HTMLResponse)
async def multa_excluir(
    session: SessionDep,
    multa_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("locacoes.multa.excluir"))
    ],
) -> RedirectResponse:
    await MultaService(session).delete(multa_id)
    return RedirectResponse("/locacoes/multas", status_code=303)


@router.post("/locacoes/multas/{multa_id}/vincular", response_class=HTMLResponse)
async def multa_vincular(
    session: SessionDep,
    multa_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("locacoes.multa.editar"))
    ],
) -> RedirectResponse:
    await MultaService(session).vincular_auto(multa_id)
    return RedirectResponse("/locacoes/multas", status_code=303)


@router.post("/locacoes/multas/{multa_id}/notificado", response_class=HTMLResponse)
async def multa_notificado(
    session: SessionDep,
    multa_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("locacoes.multa.editar"))
    ],
) -> RedirectResponse:
    await MultaService(session).marcar_notificado(multa_id)
    return RedirectResponse("/locacoes/multas", status_code=303)


@router.post("/locacoes/multas/{multa_id}/paga", response_class=HTMLResponse)
async def multa_paga(
    session: SessionDep,
    multa_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("locacoes.multa.editar"))
    ],
) -> RedirectResponse:
    await MultaService(session).marcar_paga(multa_id)
    return RedirectResponse("/locacoes/multas", status_code=303)


# ================================================================ Avarias
@router.get("/locacoes/avarias", response_class=HTMLResponse)
async def avarias_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("locacoes.avaria.visualizar"))
    ],
    page: int = 1,
    status: str = "",
) -> HTMLResponse:
    st = AvariaStatus(status) if status else None
    result = await AvariaService(session).list_items(
        PageParams(page=page, size=25), status=st
    )
    lookups = await _locacoes_lookups(session, _user.tenant_id)
    return render(
        request,
        "locacoes/avarias_list.html",
        {
            "page_result": result,
            "title": "Avarias",
            "status": status,
            **lookups,
        },
    )


@router.get("/locacoes/avarias/novo", response_class=HTMLResponse)
async def avaria_novo_form(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("locacoes.avaria.criar"))
    ],
) -> HTMLResponse:
    lookups = await _locacoes_lookups(session, current_user.tenant_id)
    return render(
        request,
        "locacoes/avaria_form.html",
        {
            "title": "Nova Avaria",
            "error": None,
            "item": None,
            "action": "/locacoes/avarias/novo",
            **lookups,
        },
    )


@router.post("/locacoes/avarias/novo", response_class=HTMLResponse)
async def avaria_novo_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("locacoes.avaria.criar"))
    ],
    veiculo_id: Annotated[str, Form()],
    origem: Annotated[str, Form()],
    localizacao: Annotated[str, Form()],
    severidade: Annotated[str, Form()],
    contrato_id: Annotated[str, Form()] = "",
    laudo: Annotated[str, Form()] = "",
    valor_reparo: Annotated[str, Form()] = "",
    observacoes: Annotated[str, Form()] = "",
    fotos: Annotated[str, Form()] = "",
) -> HTMLResponse:
    lookups = await _locacoes_lookups(session, current_user.tenant_id)
    ctx = {
        "title": "Nova Avaria",
        "error": None,
        "item": None,
        "action": "/locacoes/avarias/novo",
        **lookups,
    }
    try:
        foto_keys = [k.strip() for k in fotos.splitlines() if k.strip()]
        await AvariaService(session).create(
            current_user.tenant_id,
            AvariaCreate(
                veiculo_id=uuid.UUID(veiculo_id),
                origem=AvariaOrigem(origem),
                localizacao=localizacao,
                severidade=AvariaSeveridade(severidade),
                contrato_id=_uuid(contrato_id),
                laudo=laudo or None,
                valor_reparo=_dec(valor_reparo) if valor_reparo.strip() else None,
                fotos=foto_keys,
                observacoes=observacoes or None,
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _app_error_message(exc)
        return render(request, "locacoes/avaria_form.html", ctx, status_code=400)
    return RedirectResponse("/locacoes/avarias", status_code=303)


@router.get("/locacoes/avarias/{avaria_id}/editar", response_class=HTMLResponse)
async def avaria_editar_form(
    request: Request,
    session: SessionDep,
    avaria_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("locacoes.avaria.editar"))
    ],
) -> HTMLResponse:
    item = await AvariaService(session).get(avaria_id)
    lookups = await _locacoes_lookups(session, _user.tenant_id)
    return render(
        request,
        "locacoes/avaria_form.html",
        {
            "title": "Editar Avaria",
            "error": None,
            "item": item,
            "action": f"/locacoes/avarias/{avaria_id}/editar",
            **lookups,
        },
    )


@router.post("/locacoes/avarias/{avaria_id}/editar", response_class=HTMLResponse)
async def avaria_editar_save(
    request: Request,
    session: SessionDep,
    avaria_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("locacoes.avaria.editar"))
    ],
    localizacao: Annotated[str, Form()] = "",
    severidade: Annotated[str, Form()] = "",
    laudo: Annotated[str, Form()] = "",
    valor_reparo: Annotated[str, Form()] = "",
    observacoes: Annotated[str, Form()] = "",
) -> HTMLResponse:
    item = await AvariaService(session).get(avaria_id)
    lookups = await _locacoes_lookups(session, _user.tenant_id)
    ctx = {
        "title": "Editar Avaria",
        "error": None,
        "item": item,
        "action": f"/locacoes/avarias/{avaria_id}/editar",
        **lookups,
    }
    try:
        payload: dict[str, Any] = {}
        if localizacao.strip():
            payload["localizacao"] = localizacao
        if severidade.strip():
            payload["severidade"] = AvariaSeveridade(severidade)
        if laudo.strip():
            payload["laudo"] = laudo
        if valor_reparo.strip():
            payload["valor_reparo"] = _dec(valor_reparo)
        if observacoes.strip():
            payload["observacoes"] = observacoes
        await AvariaService(session).update(avaria_id, AvariaUpdate(**payload))
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _app_error_message(exc)
        return render(request, "locacoes/avaria_form.html", ctx, status_code=400)
    return RedirectResponse("/locacoes/avarias", status_code=303)


@router.post("/locacoes/avarias/{avaria_id}/responsabilidade", response_class=HTMLResponse)
async def avaria_responsabilidade(
    session: SessionDep,
    avaria_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("locacoes.avaria.editar"))
    ],
    responsabilidade: Annotated[str, Form()],
) -> RedirectResponse:
    await AvariaService(session).definir_responsabilidade(
        avaria_id,
        AvariaResponsabilidadeInput(
            responsabilidade=AvariaResponsabilidade(responsabilidade)
        ),
    )
    return RedirectResponse("/locacoes/avarias", status_code=303)


@router.post("/locacoes/avarias/{avaria_id}/gerar-os", response_class=HTMLResponse)
async def avaria_gerar_os(
    session: SessionDep,
    avaria_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("locacoes.avaria.editar"))
    ],
) -> RedirectResponse:
    await AvariaService(session).gerar_os(avaria_id)
    return RedirectResponse("/locacoes/avarias", status_code=303)


@router.post("/locacoes/avarias/{avaria_id}/encerrar", response_class=HTMLResponse)
async def avaria_encerrar(
    session: SessionDep,
    avaria_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("locacoes.avaria.editar"))
    ],
) -> RedirectResponse:
    await AvariaService(session).encerrar(avaria_id)
    return RedirectResponse("/locacoes/avarias", status_code=303)
