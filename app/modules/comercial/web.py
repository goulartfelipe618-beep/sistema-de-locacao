"""Rotas Web (HTML/Jinja2) do módulo Comercial / CRM (§7)."""

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
from app.modules.cadastros.service import ClienteService
from app.modules.cadastros.service_extra import VendedorService
from app.modules.comercial.schemas import (
    CampanhaCreate,
    CupomCreate,
    FidelidadeRegraInput,
    FidelidadeTierInput,
    InteracaoCreate,
    OportunidadeCreate,
    PropostaCreate,
    PropostaItemInput,
)
from app.modules.comercial.service import (
    KANBAN_ESTAGIOS,
    CampanhaService,
    CupomService,
    FidelidadeService,
    FunilService,
    PropostaService,
)
from app.modules.frota.service import CategoriasService
from app.modules.identity.service import AuthenticatedUser
from app.modules.tenants.service import FilialService
from app.shared.enums import (
    CrmCampanhaCanal,
    CrmCampanhaPublico,
    CrmCampanhaStatus,
    CrmCupomStatus,
    CrmCupomTipo,
    CrmEstagio,
    CrmInteracaoTipo,
    CrmOrigemLead,
    CrmPropostaStatus,
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


def _int(raw: str | None, default: int = 0) -> int:
    value = (raw or "").strip()
    return int(value) if value else default


def _bool(raw: str | None) -> bool:
    return (raw or "").strip().lower() in ("on", "true", "1", "sim")


def _msg(exc: AppError | ValueError) -> str:
    return exc.message if isinstance(exc, AppError) else str(exc)


async def _lookups(session: AsyncSession) -> dict[str, Any]:
    clientes = await ClienteService(session).list_clientes(PageParams(page=1, size=300))
    vendedores = await VendedorService(session).list_items(PageParams(page=1, size=200))
    filiais = await FilialService(session).list_filiais(PageParams(page=1, size=100))
    categorias = await CategoriasService(session).list_items(PageParams(page=1, size=200))
    return {
        "clientes": clientes.items,
        "vendedores": vendedores.items,
        "filiais": filiais.items,
        "categorias": categorias.items,
        "cliente_nomes": {str(c.id): c.nome for c in clientes.items},
        "vendedor_nomes": {str(v.id): v.nome for v in vendedores.items},
        "categoria_nomes": {str(c.id): c.nome for c in categorias.items},
    }


# ================================================================ Funil
@router.get("/comercial/funil", response_class=HTMLResponse)
async def funil_kanban(
    request: Request,
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("comercial.funil.visualizar"))],
) -> HTMLResponse:
    board = await FunilService(session).kanban()
    lookups = await _lookups(session)
    return render(
        request,
        "comercial/funil_kanban.html",
        {
            "title": "Funil de Vendas",
            "board": board,
            "estagios": list(KANBAN_ESTAGIOS),
            "origens_lead": [o.value for o in CrmOrigemLead],
            "error": None,
            **lookups,
        },
    )


@router.post("/comercial/funil/novo", response_class=HTMLResponse)
async def funil_novo(
    request: Request,
    session: SessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_permission("comercial.funil.criar"))],
    titulo: Annotated[str, Form()],
    origem_lead: Annotated[str, Form()] = "outro",
    cliente_id: Annotated[str, Form()] = "",
    vendedor_id: Annotated[str, Form()] = "",
    valor_estimado: Annotated[str, Form()] = "0",
    data_prevista_fechamento: Annotated[str, Form()] = "",
    observacoes: Annotated[str, Form()] = "",
) -> HTMLResponse:
    try:
        await FunilService(session).create(
            current_user.tenant_id,
            OportunidadeCreate(
                titulo=titulo,
                origem_lead=CrmOrigemLead(origem_lead),
                cliente_id=_uuid(cliente_id),
                vendedor_id=_uuid(vendedor_id),
                valor_estimado=_dec(valor_estimado),
                data_prevista_fechamento=_date(data_prevista_fechamento),
                observacoes=observacoes or None,
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        board = await FunilService(session).kanban()
        lookups = await _lookups(session)
        return render(
            request,
            "comercial/funil_kanban.html",
            {
                "title": "Funil de Vendas",
                "board": board,
                "estagios": list(KANBAN_ESTAGIOS),
                "origens_lead": [o.value for o in CrmOrigemLead],
                "error": _msg(exc),
                **lookups,
            },
            status_code=400,
        )
    return RedirectResponse("/comercial/funil", status_code=303)


@router.post("/comercial/funil/{oportunidade_id}/mover", response_class=HTMLResponse)
async def funil_mover(
    session: SessionDep,
    oportunidade_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("comercial.funil.editar"))],
    estagio: Annotated[str, Form()],
) -> RedirectResponse:
    await FunilService(session).move_estagio(oportunidade_id, CrmEstagio(estagio))
    return RedirectResponse("/comercial/funil", status_code=303)


@router.get("/comercial/funil/{oportunidade_id}", response_class=HTMLResponse)
async def funil_detalhe(
    request: Request,
    session: SessionDep,
    oportunidade_id: uuid.UUID,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_permission("comercial.funil.visualizar"))],
) -> HTMLResponse:
    svc = FunilService(session)
    opp = await svc.get(oportunidade_id)
    from app.modules.notificacoes.service import NotificationService

    notif_svc = NotificationService(session)
    await notif_svc.marcar_lidas_por_referencia(
        current_user.id,
        referencia_tipo="crm_oportunidade",
        referencia_id=oportunidade_id,
    )
    request.state.notificacoes_nao_lidas = await notif_svc.count_nao_lidas(current_user.id)
    interacoes = await svc.list_interacoes(oportunidade_id)
    lookups = await _lookups(session)
    return render(
        request,
        "comercial/funil_detalhe.html",
        {
            "title": f"Oportunidade {opp.numero}",
            "opp": opp,
            "interacoes": interacoes,
            "estagios": list(KANBAN_ESTAGIOS),
            "interacao_tipos": [t.value for t in CrmInteracaoTipo],
            "error": None,
            **lookups,
        },
    )


@router.post("/comercial/funil/{oportunidade_id}/interacao", response_class=HTMLResponse)
async def funil_interacao(
    session: SessionDep,
    oportunidade_id: uuid.UUID,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_permission("comercial.funil.criar"))],
    tipo: Annotated[str, Form()] = "nota",
    descricao: Annotated[str, Form()] = "",
) -> RedirectResponse:
    await FunilService(session).add_interacao(
        oportunidade_id,
        InteracaoCreate(tipo=CrmInteracaoTipo(tipo), descricao=descricao or "-"),
        user_id=current_user.id,
    )
    return RedirectResponse(f"/comercial/funil/{oportunidade_id}", status_code=303)


@router.post("/comercial/funil/{oportunidade_id}/perdido", response_class=HTMLResponse)
async def funil_perdido(
    session: SessionDep,
    oportunidade_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("comercial.funil.editar"))],
    motivo_perda: Annotated[str, Form()] = "Não informado",
) -> RedirectResponse:
    await FunilService(session).marcar_perdido(oportunidade_id, motivo_perda or "Não informado")
    return RedirectResponse(f"/comercial/funil/{oportunidade_id}", status_code=303)


@router.post("/comercial/funil/{oportunidade_id}/ganho", response_class=HTMLResponse)
async def funil_ganho(
    session: SessionDep,
    oportunidade_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("comercial.funil.editar"))],
) -> RedirectResponse:
    await FunilService(session).marcar_ganho(oportunidade_id)
    return RedirectResponse(f"/comercial/funil/{oportunidade_id}", status_code=303)


# ================================================================ Propostas
@router.get("/comercial/propostas", response_class=HTMLResponse)
async def propostas_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("comercial.proposta.visualizar"))],
    page: int = 1,
    status: str = "",
) -> HTMLResponse:
    st = CrmPropostaStatus(status) if status else None
    result = await PropostaService(session).list_items(PageParams(page=page, size=25), status=st)
    lookups = await _lookups(session)
    return render(
        request,
        "comercial/propostas_list.html",
        {"title": "Propostas", "page_result": result, "status": status, **lookups},
    )


@router.get("/comercial/propostas/nova", response_class=HTMLResponse)
async def proposta_nova_form(
    request: Request,
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("comercial.proposta.criar"))],
) -> HTMLResponse:
    lookups = await _lookups(session)
    return render(
        request,
        "comercial/proposta_form.html",
        {"title": "Nova Proposta", "error": None, **lookups},
    )


@router.post("/comercial/propostas/nova", response_class=HTMLResponse)
async def proposta_nova_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_permission("comercial.proposta.criar"))],
    cliente_id: Annotated[str, Form()] = "",
    vendedor_id: Annotated[str, Form()] = "",
    filial_id: Annotated[str, Form()] = "",
    validade_em: Annotated[str, Form()] = "",
    condicoes_comerciais: Annotated[str, Form()] = "",
    observacoes: Annotated[str, Form()] = "",
    item_descricao: Annotated[list[str] | None, Form()] = None,
    item_categoria_id: Annotated[list[str] | None, Form()] = None,
    item_quantidade: Annotated[list[str] | None, Form()] = None,
    item_dias: Annotated[list[str] | None, Form()] = None,
    item_valor_unitario: Annotated[list[str] | None, Form()] = None,
) -> HTMLResponse:
    lookups = await _lookups(session)
    ctx = {"title": "Nova Proposta", "error": None, **lookups}
    item_descricao = item_descricao or []
    item_categoria_id = item_categoria_id or []
    item_quantidade = item_quantidade or []
    item_dias = item_dias or []
    item_valor_unitario = item_valor_unitario or []
    try:
        itens: list[PropostaItemInput] = []
        for idx, desc in enumerate(item_descricao):
            if not desc or not desc.strip():
                continue
            itens.append(
                PropostaItemInput(
                    descricao=desc.strip(),
                    categoria_id=_uuid(item_categoria_id[idx]) if idx < len(item_categoria_id) else None,
                    quantidade=_dec(item_quantidade[idx] if idx < len(item_quantidade) else "1", "1"),
                    dias=_int(item_dias[idx] if idx < len(item_dias) else "1", 1),
                    valor_unitario=_dec(
                        item_valor_unitario[idx] if idx < len(item_valor_unitario) else "0"
                    ),
                )
            )
        proposta = await PropostaService(session).create(
            current_user.tenant_id,
            PropostaCreate(
                cliente_id=_uuid(cliente_id),
                vendedor_id=_uuid(vendedor_id),
                filial_id=_uuid(filial_id),
                validade_em=_date(validade_em),
                condicoes_comerciais=condicoes_comerciais or None,
                observacoes=observacoes or None,
                itens=itens,
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _msg(exc)
        return render(request, "comercial/proposta_form.html", ctx, status_code=400)
    return RedirectResponse(f"/comercial/propostas/{proposta.id}", status_code=303)


@router.get("/comercial/propostas/{proposta_id}", response_class=HTMLResponse)
async def proposta_detalhe(
    request: Request,
    session: SessionDep,
    proposta_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("comercial.proposta.visualizar"))],
) -> HTMLResponse:
    svc = PropostaService(session)
    proposta = await svc.get(proposta_id)
    itens = await svc.list_proposta_itens(proposta_id)
    lookups = await _lookups(session)
    return render(
        request,
        "comercial/proposta_detalhe.html",
        {
            "title": f"Proposta {proposta.numero} v{proposta.versao}",
            "proposta": proposta,
            "itens": itens,
            "error": None,
            **lookups,
        },
    )


@router.post("/comercial/propostas/{proposta_id}/{acao}", response_class=HTMLResponse)
async def proposta_acao(
    session: SessionDep,
    proposta_id: uuid.UUID,
    acao: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_permission("comercial.proposta.editar"))],
) -> RedirectResponse:
    svc = PropostaService(session)
    if acao == "enviar":
        await svc.enviar(proposta_id)
    elif acao == "aceitar":
        await svc.aceitar(proposta_id)
    elif acao == "recusar":
        await svc.recusar(proposta_id)
    elif acao == "visualizar":
        await svc.marcar_visualizada(proposta_id)
    elif acao == "revisao":
        nova = await svc.criar_revisao(proposta_id)
        return RedirectResponse(f"/comercial/propostas/{nova.id}", status_code=303)
    return RedirectResponse(f"/comercial/propostas/{proposta_id}", status_code=303)


@router.post("/comercial/propostas/{proposta_id}/excluir/confirmar", response_class=HTMLResponse)
async def proposta_excluir(
    session: SessionDep,
    proposta_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("comercial.proposta.excluir"))],
) -> RedirectResponse:
    await PropostaService(session).delete(proposta_id)
    return RedirectResponse("/comercial/propostas", status_code=303)


# ================================================================ Campanhas
@router.get("/comercial/campanhas", response_class=HTMLResponse)
async def campanhas_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("comercial.campanha.visualizar"))],
    page: int = 1,
    status: str = "",
) -> HTMLResponse:
    st = CrmCampanhaStatus(status) if status else None
    result = await CampanhaService(session).list_items(PageParams(page=page, size=25), status=st)
    return render(
        request,
        "comercial/campanhas_list.html",
        {"title": "Campanhas", "page_result": result, "status": status},
    )


@router.get("/comercial/campanhas/nova", response_class=HTMLResponse)
async def campanha_nova_form(
    request: Request,
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("comercial.campanha.criar"))],
) -> HTMLResponse:
    return render(
        request,
        "comercial/campanha_form.html",
        {
            "title": "Nova Campanha",
            "error": None,
            "canais": [c.value for c in CrmCampanhaCanal],
            "publicos": [p.value for p in CrmCampanhaPublico],
        },
    )


@router.post("/comercial/campanhas/nova", response_class=HTMLResponse)
async def campanha_nova_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_permission("comercial.campanha.criar"))],
    nome: Annotated[str, Form()],
    canal: Annotated[str, Form()] = "email",
    publico_alvo: Annotated[str, Form()] = "todos",
    categoria_cliente: Annotated[str, Form()] = "",
    dias_inativo: Annotated[str, Form()] = "90",
    desconto_percentual: Annotated[str, Form()] = "",
    inicio_em: Annotated[str, Form()] = "",
    fim_em: Annotated[str, Form()] = "",
    mensagem_assunto: Annotated[str, Form()] = "",
    mensagem_corpo: Annotated[str, Form()] = "",
) -> HTMLResponse:
    ctx = {
        "title": "Nova Campanha",
        "error": None,
        "canais": [c.value for c in CrmCampanhaCanal],
        "publicos": [p.value for p in CrmCampanhaPublico],
    }
    try:
        await CampanhaService(session).create(
            current_user.tenant_id,
            CampanhaCreate(
                nome=nome,
                canal=CrmCampanhaCanal(canal),
                publico_alvo=CrmCampanhaPublico(publico_alvo),
                categoria_cliente=categoria_cliente or None,
                dias_inativo=_int(dias_inativo, 90),
                desconto_percentual=_dec(desconto_percentual) if desconto_percentual.strip() else None,
                inicio_em=_date(inicio_em),
                fim_em=_date(fim_em),
                mensagem_assunto=mensagem_assunto or None,
                mensagem_corpo=mensagem_corpo or None,
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _msg(exc)
        return render(request, "comercial/campanha_form.html", ctx, status_code=400)
    return RedirectResponse("/comercial/campanhas", status_code=303)


@router.get("/comercial/campanhas/{campanha_id}", response_class=HTMLResponse)
async def campanha_detalhe(
    request: Request,
    session: SessionDep,
    campanha_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("comercial.campanha.visualizar"))],
) -> HTMLResponse:
    campanha = await CampanhaService(session).get(campanha_id)
    return render(
        request,
        "comercial/campanha_detalhe.html",
        {"title": f"Campanha {campanha.codigo}", "campanha": campanha, "error": None},
    )


@router.post("/comercial/campanhas/{campanha_id}/{acao}", response_class=HTMLResponse)
async def campanha_acao(
    session: SessionDep,
    campanha_id: uuid.UUID,
    acao: str,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("comercial.campanha.editar"))],
) -> RedirectResponse:
    svc = CampanhaService(session)
    if acao == "ativar":
        await svc.ativar(campanha_id)
    elif acao == "pausar":
        await svc.pausar(campanha_id)
    elif acao == "encerrar":
        await svc.encerrar(campanha_id)
    elif acao == "disparar":
        await svc.disparar(campanha_id)
    return RedirectResponse(f"/comercial/campanhas/{campanha_id}", status_code=303)


# ================================================================ Cupons
@router.get("/comercial/cupons", response_class=HTMLResponse)
async def cupons_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("comercial.cupom.visualizar"))],
    page: int = 1,
    status: str = "",
) -> HTMLResponse:
    st = CrmCupomStatus(status) if status else None
    result = await CupomService(session).list_items(PageParams(page=page, size=25), status=st)
    lookups = await _lookups(session)
    return render(
        request,
        "comercial/cupons_list.html",
        {
            "title": "Cupons",
            "page_result": result,
            "status": status,
            "cupom_tipos": [t.value for t in CrmCupomTipo],
            **lookups,
        },
    )


@router.get("/comercial/cupons/novo", response_class=HTMLResponse)
async def cupom_novo_form(
    request: Request,
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("comercial.cupom.criar"))],
) -> HTMLResponse:
    lookups = await _lookups(session)
    return render(
        request,
        "comercial/cupom_form.html",
        {"title": "Novo Cupom", "error": None, "cupom_tipos": [t.value for t in CrmCupomTipo], **lookups},
    )


@router.post("/comercial/cupons/novo", response_class=HTMLResponse)
async def cupom_novo_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_permission("comercial.cupom.criar"))],
    codigo: Annotated[str, Form()],
    tipo: Annotated[str, Form()] = "percentual",
    valor: Annotated[str, Form()] = "0",
    categoria_id: Annotated[str, Form()] = "",
    valor_minimo: Annotated[str, Form()] = "0",
    primeira_locacao_apenas: Annotated[str, Form()] = "",
    inicio_em: Annotated[str, Form()] = "",
    fim_em: Annotated[str, Form()] = "",
    limite_uso_total: Annotated[str, Form()] = "",
    limite_uso_cliente: Annotated[str, Form()] = "",
    descricao: Annotated[str, Form()] = "",
) -> HTMLResponse:
    lookups = await _lookups(session)
    ctx = {"title": "Novo Cupom", "error": None, "cupom_tipos": [t.value for t in CrmCupomTipo], **lookups}
    try:
        await CupomService(session).create(
            current_user.tenant_id,
            CupomCreate(
                codigo=codigo,
                tipo=CrmCupomTipo(tipo),
                valor=_dec(valor),
                categoria_id=_uuid(categoria_id),
                valor_minimo=_dec(valor_minimo),
                primeira_locacao_apenas=_bool(primeira_locacao_apenas),
                inicio_em=_date(inicio_em),
                fim_em=_date(fim_em),
                limite_uso_total=_int(limite_uso_total) or None,
                limite_uso_cliente=_int(limite_uso_cliente) or None,
                descricao=descricao or None,
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _msg(exc)
        return render(request, "comercial/cupom_form.html", ctx, status_code=400)
    return RedirectResponse("/comercial/cupons", status_code=303)


@router.post("/comercial/cupons/{cupom_id}/excluir", response_class=HTMLResponse)
async def cupom_excluir(
    session: SessionDep,
    cupom_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("comercial.cupom.excluir"))],
) -> RedirectResponse:
    await CupomService(session).delete(cupom_id)
    return RedirectResponse("/comercial/cupons", status_code=303)


# ================================================================ Fidelidade
@router.get("/comercial/fidelidade", response_class=HTMLResponse)
async def fidelidade_view(
    request: Request,
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("comercial.fidelidade.visualizar"))],
    page: int = 1,
) -> HTMLResponse:
    svc = FidelidadeService(session)
    regra = await svc.get_regra()
    tiers = await svc.list_tiers()
    contas = await svc.list_contas(PageParams(page=page, size=25))
    lookups = await _lookups(session)
    return render(
        request,
        "comercial/fidelidade.html",
        {
            "title": "Fidelidade",
            "regra": regra,
            "tiers": tiers,
            "page_result": contas,
            "error": None,
            **lookups,
        },
    )


@router.post("/comercial/fidelidade/regra", response_class=HTMLResponse)
async def fidelidade_regra_salvar(
    session: SessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_permission("comercial.fidelidade.editar"))],
    nome: Annotated[str, Form()] = "Programa de Fidelidade",
    pontos_por_real: Annotated[str, Form()] = "1",
    pontos_por_diaria: Annotated[str, Form()] = "0",
    valor_por_ponto: Annotated[str, Form()] = "0.10",
    validade_meses: Annotated[str, Form()] = "12",
    ativo: Annotated[str, Form()] = "on",
) -> RedirectResponse:
    await FidelidadeService(session).salvar_regra(
        current_user.tenant_id,
        FidelidadeRegraInput(
            nome=nome or "Programa de Fidelidade",
            pontos_por_real=_dec(pontos_por_real, "1"),
            pontos_por_diaria=_dec(pontos_por_diaria, "0"),
            valor_por_ponto=_dec(valor_por_ponto, "0.10"),
            validade_meses=_int(validade_meses, 12),
            ativo=_bool(ativo),
        ),
    )
    return RedirectResponse("/comercial/fidelidade", status_code=303)


@router.post("/comercial/fidelidade/tiers/novo", response_class=HTMLResponse)
async def fidelidade_tier_novo(
    session: SessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_permission("comercial.fidelidade.criar"))],
    nome: Annotated[str, Form()],
    pontos_minimos: Annotated[str, Form()] = "0",
    beneficio_descricao: Annotated[str, Form()] = "",
    ordem: Annotated[str, Form()] = "0",
) -> RedirectResponse:
    await FidelidadeService(session).add_tier(
        current_user.tenant_id,
        FidelidadeTierInput(
            nome=nome,
            pontos_minimos=_int(pontos_minimos, 0),
            beneficio_descricao=beneficio_descricao or None,
            ordem=_int(ordem, 0),
        ),
    )
    return RedirectResponse("/comercial/fidelidade", status_code=303)


@router.post("/comercial/fidelidade/resgatar", response_class=HTMLResponse)
async def fidelidade_resgatar(
    request: Request,
    session: SessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_permission("comercial.fidelidade.editar"))],
    cliente_id: Annotated[str, Form()],
    pontos: Annotated[str, Form()],
) -> HTMLResponse:
    try:
        await FidelidadeService(session).resgatar(
            current_user.tenant_id,
            cliente_id=uuid.UUID(cliente_id),
            pontos=_int(pontos, 0),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        svc = FidelidadeService(session)
        regra = await svc.get_regra()
        tiers = await svc.list_tiers()
        contas = await svc.list_contas(PageParams(page=1, size=25))
        lookups = await _lookups(session)
        return render(
            request,
            "comercial/fidelidade.html",
            {
                "title": "Fidelidade",
                "regra": regra,
                "tiers": tiers,
                "page_result": contas,
                "error": _msg(exc),
                **lookups,
            },
            status_code=400,
        )
    return RedirectResponse("/comercial/fidelidade", status_code=303)


@router.get("/comercial/fidelidade/contas/{conta_id}", response_class=HTMLResponse)
async def fidelidade_extrato(
    request: Request,
    session: SessionDep,
    conta_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("comercial.fidelidade.visualizar"))],
) -> HTMLResponse:
    svc = FidelidadeService(session)
    conta = await svc.conta_repo.get(conta_id)
    if conta is None:
        return RedirectResponse("/comercial/fidelidade", status_code=303)
    movimentos = await svc.extrato(conta_id)
    lookups = await _lookups(session)
    return render(
        request,
        "comercial/fidelidade_extrato.html",
        {
            "title": "Extrato de Pontos",
            "conta": conta,
            "movimentos": movimentos,
            **lookups,
        },
    )
