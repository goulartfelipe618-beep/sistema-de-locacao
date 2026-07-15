"""Rotas Web (HTML/Jinja2) do módulo Financeiro (§9)."""

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
from app.modules.cadastros.service_extra import FornecedorService
from app.modules.financeiro.schemas import (
    CaixaAbrirInput,
    CaixaFecharInput,
    CaixaLancamentoCreate,
    CartaoAutorizarInput,
    CartaoCapturarInput,
    ConsolidarInput,
    ContaBancariaCreate,
    ContaPagarCreate,
    ContaReceberCreate,
    FaturamentoConfigCreate,
    ManualMatchInput,
    OfxImportInput,
    PagarAprovarInput,
    PagarEfetivarInput,
    PixChaveCreate,
    PixCobrancaCreate,
    ReceberBaixaInput,
)
from app.modules.financeiro.service import (
    BancoService,
    CaixaService,
    CartaoService,
    ConciliacaoService,
    ContaPagarService,
    ContaReceberService,
    FaturamentoService,
    PixService,
)
from app.modules.identity.service import AuthenticatedUser
from app.modules.tenants.service import FilialService
from app.shared.enums import (
    BancoIntegracaoTipo,
    CaixaLancamentoTipo,
    CaixaSessaoStatus,
    CartaoTipo,
    ContaBancariaTipo,
    FaturamentoCiclo,
    FaturaStatus,
    FormaPagamento,
    PixChaveTipo,
    TituloStatus,
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
    fornecedores = await FornecedorService(session).list_items(PageParams(page=1, size=300))
    return {
        "filiais": filiais.items,
        "clientes": clientes.items,
        "fornecedores": fornecedores.items,
        "filial_nomes": {str(f.id): f.name for f in filiais.items},
        "cliente_nomes": {str(c.id): c.nome for c in clientes.items},
        "fornecedor_nomes": {str(f.id): f.nome for f in fornecedores.items},
        "formas_pagamento": [f.value for f in FormaPagamento],
    }


# ================================================================ Caixa
@router.get("/financeiro/caixa", response_class=HTMLResponse)
async def caixa_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.caixa.visualizar"))],
    page: int = 1,
    status: str = "",
) -> HTMLResponse:
    st = CaixaSessaoStatus(status) if status else None
    result = await CaixaService(session).list_sessoes(PageParams(page=page, size=25), status=st)
    lookups = await _lookups(session)
    return render(
        request,
        "financeiro/caixa_list.html",
        {"page_result": result, "title": "Caixa", "status": status, **lookups},
    )


@router.post("/financeiro/caixa/abrir", response_class=HTMLResponse)
async def caixa_abrir(
    request: Request,
    session: SessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.caixa.abrir"))],
    filial_id: Annotated[str, Form()],
    valor_abertura: Annotated[str, Form()] = "0",
    observacoes: Annotated[str, Form()] = "",
) -> HTMLResponse:
    try:
        sessao = await CaixaService(session).abrir(
            current_user.tenant_id,
            CaixaAbrirInput(
                filial_id=uuid.UUID(filial_id),
                valor_abertura=_dec(valor_abertura),
                observacoes=observacoes or None,
            ),
            operador_id=current_user.id,
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        result = await CaixaService(session).list_sessoes(PageParams(page=1, size=25))
        lookups = await _lookups(session)
        return render(
            request,
            "financeiro/caixa_list.html",
            {"page_result": result, "title": "Caixa", "status": "", "error": _msg(exc), **lookups},
            status_code=400,
        )
    return RedirectResponse(f"/financeiro/caixa/{sessao.id}", status_code=303)


@router.get("/financeiro/caixa/{sessao_id}", response_class=HTMLResponse)
async def caixa_detalhe(
    request: Request,
    session: SessionDep,
    sessao_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.caixa.visualizar"))],
) -> HTMLResponse:
    svc = CaixaService(session)
    sessao = await svc.get(sessao_id)
    lancamentos = await svc.list_lancamentos(sessao_id)
    saldo = await svc.calcular_saldo(sessao_id)
    lookups = await _lookups(session)
    return render(
        request,
        "financeiro/caixa_detalhe.html",
        {
            "sessao": sessao,
            "lancamentos": lancamentos,
            "saldo": saldo,
            "title": "Sessão de Caixa",
            "error": None,
            "lancamento_tipos": [t.value for t in CaixaLancamentoTipo],
            **lookups,
        },
    )


@router.post("/financeiro/caixa/{sessao_id}/lancamento", response_class=HTMLResponse)
async def caixa_lancamento(
    session: SessionDep,
    sessao_id: uuid.UUID,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.caixa.editar"))],
    tipo: Annotated[str, Form()],
    valor: Annotated[str, Form()],
    forma_pagamento: Annotated[str, Form()] = "dinheiro",
    categoria: Annotated[str, Form()] = "",
    descricao: Annotated[str, Form()] = "",
) -> RedirectResponse:
    await CaixaService(session).registrar_lancamento(
        sessao_id,
        CaixaLancamentoCreate(
            tipo=CaixaLancamentoTipo(tipo),
            valor=_dec(valor),
            forma_pagamento=FormaPagamento(forma_pagamento),
            categoria=categoria or None,
            descricao=descricao or None,
        ),
        created_by=current_user.id,
    )
    return RedirectResponse(f"/financeiro/caixa/{sessao_id}", status_code=303)


@router.post("/financeiro/caixa/{sessao_id}/fechar", response_class=HTMLResponse)
async def caixa_fechar(
    session: SessionDep,
    sessao_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.caixa.fechar"))],
    valor_fechamento_informado: Annotated[str, Form()],
    observacoes: Annotated[str, Form()] = "",
) -> RedirectResponse:
    await CaixaService(session).fechar(
        sessao_id,
        CaixaFecharInput(
            valor_fechamento_informado=_dec(valor_fechamento_informado),
            observacoes=observacoes or None,
        ),
    )
    return RedirectResponse(f"/financeiro/caixa/{sessao_id}", status_code=303)


# ================================================================ Contas a Receber
@router.get("/financeiro/receber", response_class=HTMLResponse)
async def receber_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.receber.visualizar"))],
    page: int = 1,
    status: str = "",
) -> HTMLResponse:
    st = TituloStatus(status) if status else None
    svc = ContaReceberService(session)
    result = await svc.list_items(PageParams(page=page, size=25), status=st)
    aging = await svc.aging()
    lookups = await _lookups(session)
    return render(
        request,
        "financeiro/receber_list.html",
        {"page_result": result, "aging": aging, "title": "Contas a Receber", "status": status, **lookups},
    )


@router.get("/financeiro/receber/novo", response_class=HTMLResponse)
async def receber_novo_form(
    request: Request,
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.receber.criar"))],
) -> HTMLResponse:
    lookups = await _lookups(session)
    return render(
        request,
        "financeiro/receber_form.html",
        {"title": "Novo Título a Receber", "error": None, **lookups},
    )


@router.post("/financeiro/receber/novo", response_class=HTMLResponse)
async def receber_novo_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.receber.criar"))],
    filial_id: Annotated[str, Form()],
    descricao: Annotated[str, Form()],
    valor_original: Annotated[str, Form()],
    vencimento: Annotated[str, Form()],
    cliente_id: Annotated[str, Form()] = "",
    forma_prevista: Annotated[str, Form()] = "",
    gera_pix: Annotated[str, Form()] = "",
    observacoes: Annotated[str, Form()] = "",
) -> HTMLResponse:
    lookups = await _lookups(session)
    ctx = {"title": "Novo Título a Receber", "error": None, **lookups}
    try:
        venc = _date(vencimento)
        if not venc:
            raise ValueError("Vencimento é obrigatório.")
        await ContaReceberService(session).create(
            current_user.tenant_id,
            ContaReceberCreate(
                cliente_id=_uuid(cliente_id),
                filial_id=uuid.UUID(filial_id),
                descricao=descricao,
                valor_original=_dec(valor_original),
                vencimento=venc,
                forma_prevista=FormaPagamento(forma_prevista) if forma_prevista else None,
                gera_pix=_bool(gera_pix),
                observacoes=observacoes or None,
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _msg(exc)
        return render(request, "financeiro/receber_form.html", ctx, status_code=400)
    return RedirectResponse("/financeiro/receber", status_code=303)


@router.get("/financeiro/receber/{titulo_id}", response_class=HTMLResponse)
async def receber_detalhe(
    request: Request,
    session: SessionDep,
    titulo_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.receber.visualizar"))],
) -> HTMLResponse:
    svc = ContaReceberService(session)
    titulo = await svc.get(titulo_id)
    baixas = await svc.list_baixas(titulo_id)
    caixa = await CaixaService(session).list_sessoes(
        PageParams(page=1, size=50), status=CaixaSessaoStatus.ABERTA
    )
    lookups = await _lookups(session)
    return render(
        request,
        "financeiro/receber_detalhe.html",
        {
            "titulo": titulo,
            "baixas": baixas,
            "sessoes_abertas": caixa.items,
            "title": f"Título {titulo.numero}",
            "error": None,
            **lookups,
        },
    )


@router.post("/financeiro/receber/{titulo_id}/baixar", response_class=HTMLResponse)
async def receber_baixar(
    session: SessionDep,
    titulo_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.receber.baixar"))],
    valor: Annotated[str, Form()],
    forma: Annotated[str, Form()] = "dinheiro",
    sessao_id: Annotated[str, Form()] = "",
    observacao: Annotated[str, Form()] = "",
) -> RedirectResponse:
    await ContaReceberService(session).baixar(
        titulo_id,
        ReceberBaixaInput(
            valor=_dec(valor),
            forma=FormaPagamento(forma),
            sessao_id=_uuid(sessao_id),
            observacao=observacao or None,
        ),
    )
    return RedirectResponse(f"/financeiro/receber/{titulo_id}", status_code=303)


@router.post("/financeiro/receber/{titulo_id}/estornar", response_class=HTMLResponse)
async def receber_estornar(
    session: SessionDep,
    titulo_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.receber.estornar"))],
) -> RedirectResponse:
    await ContaReceberService(session).estornar(titulo_id)
    return RedirectResponse(f"/financeiro/receber/{titulo_id}", status_code=303)


@router.post("/financeiro/receber/{titulo_id}/cancelar", response_class=HTMLResponse)
async def receber_cancelar(
    session: SessionDep,
    titulo_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.receber.editar"))],
) -> RedirectResponse:
    await ContaReceberService(session).cancelar(titulo_id)
    return RedirectResponse(f"/financeiro/receber/{titulo_id}", status_code=303)


@router.post("/financeiro/receber/{titulo_id}/pix", response_class=HTMLResponse)
async def receber_gerar_pix(
    session: SessionDep,
    titulo_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.pix.criar"))],
) -> RedirectResponse:
    await PixService(session).create_cobranca_from_titulo(
        PixCobrancaCreate(titulo_receber_id=titulo_id)
    )
    return RedirectResponse(f"/financeiro/receber/{titulo_id}", status_code=303)


# ================================================================ Contas a Pagar
@router.get("/financeiro/pagar", response_class=HTMLResponse)
async def pagar_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.pagar.visualizar"))],
    page: int = 1,
    status: str = "",
) -> HTMLResponse:
    st = TituloStatus(status) if status else None
    result = await ContaPagarService(session).list_items(PageParams(page=page, size=25), status=st)
    lookups = await _lookups(session)
    return render(
        request,
        "financeiro/pagar_list.html",
        {"page_result": result, "title": "Contas a Pagar", "status": status, **lookups},
    )


@router.get("/financeiro/pagar/novo", response_class=HTMLResponse)
async def pagar_novo_form(
    request: Request,
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.pagar.criar"))],
) -> HTMLResponse:
    lookups = await _lookups(session)
    return render(
        request,
        "financeiro/pagar_form.html",
        {"title": "Novo Título a Pagar", "error": None, **lookups},
    )


@router.post("/financeiro/pagar/novo", response_class=HTMLResponse)
async def pagar_novo_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.pagar.criar"))],
    filial_id: Annotated[str, Form()],
    descricao: Annotated[str, Form()],
    valor_original: Annotated[str, Form()],
    vencimento: Annotated[str, Form()],
    fornecedor_id: Annotated[str, Form()] = "",
    beneficiario_nome: Annotated[str, Form()] = "",
    forma_prevista: Annotated[str, Form()] = "",
    observacoes: Annotated[str, Form()] = "",
) -> HTMLResponse:
    lookups = await _lookups(session)
    ctx = {"title": "Novo Título a Pagar", "error": None, **lookups}
    try:
        venc = _date(vencimento)
        if not venc:
            raise ValueError("Vencimento é obrigatório.")
        await ContaPagarService(session).create(
            current_user.tenant_id,
            ContaPagarCreate(
                fornecedor_id=_uuid(fornecedor_id),
                beneficiario_nome=beneficiario_nome or None,
                filial_id=uuid.UUID(filial_id),
                descricao=descricao,
                valor_original=_dec(valor_original),
                vencimento=venc,
                forma_prevista=FormaPagamento(forma_prevista) if forma_prevista else None,
                observacoes=observacoes or None,
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _msg(exc)
        return render(request, "financeiro/pagar_form.html", ctx, status_code=400)
    return RedirectResponse("/financeiro/pagar", status_code=303)


@router.get("/financeiro/pagar/{titulo_id}", response_class=HTMLResponse)
async def pagar_detalhe(
    request: Request,
    session: SessionDep,
    titulo_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.pagar.visualizar"))],
) -> HTMLResponse:
    svc = ContaPagarService(session)
    titulo = await svc.get(titulo_id)
    baixas = await svc.list_baixas(titulo_id)
    contas = await BancoService(session).list_contas(PageParams(page=1, size=50))
    lookups = await _lookups(session)
    return render(
        request,
        "financeiro/pagar_detalhe.html",
        {
            "titulo": titulo,
            "baixas": baixas,
            "contas_bancarias": contas.items,
            "title": f"Título {titulo.numero}",
            "error": None,
            **lookups,
        },
    )


@router.post("/financeiro/pagar/{titulo_id}/aprovar", response_class=HTMLResponse)
async def pagar_aprovar(
    session: SessionDep,
    titulo_id: uuid.UUID,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.pagar.aprovar"))],
) -> RedirectResponse:
    await ContaPagarService(session).aprovar(
        titulo_id, PagarAprovarInput(aprovado_por=current_user.id)
    )
    return RedirectResponse(f"/financeiro/pagar/{titulo_id}", status_code=303)


@router.post("/financeiro/pagar/{titulo_id}/efetivar", response_class=HTMLResponse)
async def pagar_efetivar(
    session: SessionDep,
    titulo_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.pagar.efetivar"))],
    valor: Annotated[str, Form()],
    forma: Annotated[str, Form()] = "transferencia",
    conta_bancaria_id: Annotated[str, Form()] = "",
    observacao: Annotated[str, Form()] = "",
) -> RedirectResponse:
    await ContaPagarService(session).efetivar_pagamento(
        titulo_id,
        PagarEfetivarInput(
            valor=_dec(valor),
            forma=FormaPagamento(forma),
            conta_bancaria_id=_uuid(conta_bancaria_id),
            observacao=observacao or None,
        ),
    )
    return RedirectResponse(f"/financeiro/pagar/{titulo_id}", status_code=303)


@router.post("/financeiro/pagar/{titulo_id}/cancelar", response_class=HTMLResponse)
async def pagar_cancelar(
    session: SessionDep,
    titulo_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.pagar.editar"))],
) -> RedirectResponse:
    await ContaPagarService(session).cancelar(titulo_id)
    return RedirectResponse(f"/financeiro/pagar/{titulo_id}", status_code=303)


# ================================================================ PIX
@router.get("/financeiro/pix", response_class=HTMLResponse)
async def pix_view(
    request: Request,
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.pix.visualizar"))],
    page: int = 1,
) -> HTMLResponse:
    svc = PixService(session)
    chaves = await svc.list_chaves(PageParams(page=1, size=100))
    cobrancas = await svc.list_cobrancas(PageParams(page=page, size=25))
    lookups = await _lookups(session)
    return render(
        request,
        "financeiro/pix_list.html",
        {
            "chaves": chaves.items,
            "page_result": cobrancas,
            "title": "PIX",
            "pix_tipos": [t.value for t in PixChaveTipo],
            "error": None,
            **lookups,
        },
    )


@router.post("/financeiro/pix/chaves/novo", response_class=HTMLResponse)
async def pix_chave_criar(
    request: Request,
    session: SessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.pix.criar"))],
    filial_id: Annotated[str, Form()],
    tipo: Annotated[str, Form()],
    chave: Annotated[str, Form()],
    descricao: Annotated[str, Form()] = "",
) -> HTMLResponse:
    try:
        await PixService(session).create_chave(
            current_user.tenant_id,
            PixChaveCreate(
                filial_id=uuid.UUID(filial_id),
                tipo=PixChaveTipo(tipo),
                chave=chave,
                descricao=descricao or None,
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        svc = PixService(session)
        chaves = await svc.list_chaves(PageParams(page=1, size=100))
        cobrancas = await svc.list_cobrancas(PageParams(page=1, size=25))
        lookups = await _lookups(session)
        return render(
            request,
            "financeiro/pix_list.html",
            {
                "chaves": chaves.items,
                "page_result": cobrancas,
                "title": "PIX",
                "pix_tipos": [t.value for t in PixChaveTipo],
                "error": _msg(exc),
                **lookups,
            },
            status_code=400,
        )
    return RedirectResponse("/financeiro/pix", status_code=303)


@router.post("/financeiro/pix/cobrancas/{cobranca_id}/confirmar", response_class=HTMLResponse)
async def pix_confirmar(
    session: SessionDep,
    cobranca_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.pix.editar"))],
) -> RedirectResponse:
    await PixService(session).confirmar_pagamento(cobranca_id)
    return RedirectResponse("/financeiro/pix", status_code=303)


# ================================================================ Cartões
@router.get("/financeiro/cartoes", response_class=HTMLResponse)
async def cartoes_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.cartoes.visualizar"))],
    page: int = 1,
) -> HTMLResponse:
    result = await CartaoService(session).list_items(PageParams(page=page, size=25))
    return render(
        request,
        "financeiro/cartoes_list.html",
        {"page_result": result, "title": "Cartões"},
    )


@router.get("/financeiro/cartoes/novo", response_class=HTMLResponse)
async def cartao_novo_form(
    request: Request,
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.cartoes.criar"))],
) -> HTMLResponse:
    return render(
        request,
        "financeiro/cartao_form.html",
        {"title": "Nova Transação de Cartão", "error": None, "cartao_tipos": [t.value for t in CartaoTipo]},
    )


@router.post("/financeiro/cartoes/novo", response_class=HTMLResponse)
async def cartao_novo_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.cartoes.criar"))],
    tipo: Annotated[str, Form()],
    valor: Annotated[str, Form()],
    parcelas: Annotated[str, Form()] = "1",
    contrato_id: Annotated[str, Form()] = "",
    titulo_receber_id: Annotated[str, Form()] = "",
    taxa_adquirente: Annotated[str, Form()] = "0",
    observacoes: Annotated[str, Form()] = "",
) -> HTMLResponse:
    ctx = {"title": "Nova Transação de Cartão", "error": None, "cartao_tipos": [t.value for t in CartaoTipo]}
    try:
        await CartaoService(session).autorizar(
            current_user.tenant_id,
            CartaoAutorizarInput(
                tipo=CartaoTipo(tipo),
                valor=_dec(valor),
                parcelas=int(parcelas) if parcelas.strip() else 1,
                contrato_id=_uuid(contrato_id),
                titulo_receber_id=_uuid(titulo_receber_id),
                taxa_adquirente=_dec(taxa_adquirente),
                observacoes=observacoes or None,
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _msg(exc)
        return render(request, "financeiro/cartao_form.html", ctx, status_code=400)
    return RedirectResponse("/financeiro/cartoes", status_code=303)


@router.post("/financeiro/cartoes/{transacao_id}/capturar", response_class=HTMLResponse)
async def cartao_capturar(
    session: SessionDep,
    transacao_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.cartoes.editar"))],
    valor: Annotated[str, Form()] = "",
) -> RedirectResponse:
    await CartaoService(session).capturar(
        transacao_id,
        CartaoCapturarInput(valor=_dec(valor) if valor.strip() else None),
    )
    return RedirectResponse("/financeiro/cartoes", status_code=303)


@router.post("/financeiro/cartoes/{transacao_id}/cancelar", response_class=HTMLResponse)
async def cartao_cancelar(
    session: SessionDep,
    transacao_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.cartoes.editar"))],
) -> RedirectResponse:
    await CartaoService(session).cancelar(transacao_id)
    return RedirectResponse("/financeiro/cartoes", status_code=303)


@router.post("/financeiro/cartoes/{transacao_id}/estornar", response_class=HTMLResponse)
async def cartao_estornar(
    session: SessionDep,
    transacao_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.cartoes.editar"))],
) -> RedirectResponse:
    await CartaoService(session).estornar(transacao_id)
    return RedirectResponse("/financeiro/cartoes", status_code=303)


# ================================================================ Bancos
@router.get("/financeiro/bancos", response_class=HTMLResponse)
async def bancos_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.bancos.visualizar"))],
    page: int = 1,
) -> HTMLResponse:
    result = await BancoService(session).list_contas(PageParams(page=page, size=25))
    lookups = await _lookups(session)
    return render(
        request,
        "financeiro/bancos_list.html",
        {"page_result": result, "title": "Bancos", **lookups},
    )


@router.get("/financeiro/bancos/novo", response_class=HTMLResponse)
async def banco_novo_form(
    request: Request,
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.bancos.criar"))],
) -> HTMLResponse:
    lookups = await _lookups(session)
    return render(
        request,
        "financeiro/banco_form.html",
        {
            "title": "Nova Conta Bancária",
            "error": None,
            "conta_tipos": [t.value for t in ContaBancariaTipo],
            "integracao_tipos": [t.value for t in BancoIntegracaoTipo],
            **lookups,
        },
    )


@router.post("/financeiro/bancos/novo", response_class=HTMLResponse)
async def banco_novo_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.bancos.criar"))],
    banco_codigo: Annotated[str, Form()],
    banco_nome: Annotated[str, Form()],
    agencia: Annotated[str, Form()],
    conta: Annotated[str, Form()],
    tipo: Annotated[str, Form()] = "corrente",
    filial_id: Annotated[str, Form()] = "",
    saldo_atual: Annotated[str, Form()] = "0",
    integracao_tipo: Annotated[str, Form()] = "manual",
) -> HTMLResponse:
    lookups = await _lookups(session)
    ctx = {
        "title": "Nova Conta Bancária",
        "error": None,
        "conta_tipos": [t.value for t in ContaBancariaTipo],
        "integracao_tipos": [t.value for t in BancoIntegracaoTipo],
        **lookups,
    }
    try:
        await BancoService(session).create_conta(
            current_user.tenant_id,
            ContaBancariaCreate(
                banco_codigo=banco_codigo,
                banco_nome=banco_nome,
                agencia=agencia,
                conta=conta,
                tipo=ContaBancariaTipo(tipo),
                filial_id=_uuid(filial_id),
                saldo_atual=_dec(saldo_atual),
                integracao_tipo=BancoIntegracaoTipo(integracao_tipo),
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _msg(exc)
        return render(request, "financeiro/banco_form.html", ctx, status_code=400)
    return RedirectResponse("/financeiro/bancos", status_code=303)


@router.post("/financeiro/bancos/{conta_id}/toggle", response_class=HTMLResponse)
async def banco_toggle(
    session: SessionDep,
    conta_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.bancos.editar"))],
) -> RedirectResponse:
    await BancoService(session).toggle_ativa(conta_id)
    return RedirectResponse("/financeiro/bancos", status_code=303)


@router.get("/financeiro/bancos/{conta_id}/extrato", response_class=HTMLResponse)
async def banco_extrato(
    request: Request,
    session: SessionDep,
    conta_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.bancos.visualizar"))],
    page: int = 1,
) -> HTMLResponse:
    svc = BancoService(session)
    conta = await svc.get_conta(conta_id)
    result = await svc.list_extrato(PageParams(page=page, size=50), conta_id=conta_id)
    return render(
        request,
        "financeiro/banco_extrato.html",
        {"conta": conta, "page_result": result, "title": f"Extrato — {conta.banco_nome}"},
    )


# ================================================================ Conciliação
@router.get("/financeiro/conciliacao", response_class=HTMLResponse)
async def conciliacao_view(
    request: Request,
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.conciliacao.visualizar"))],
    page: int = 1,
) -> HTMLResponse:
    banco_svc = BancoService(session)
    contas = await banco_svc.list_contas(PageParams(page=1, size=100))
    divergencias = await ConciliacaoService(session).list_divergencias(PageParams(page=page, size=25))
    return render(
        request,
        "financeiro/conciliacao.html",
        {
            "contas": contas.items,
            "page_result": divergencias,
            "title": "Conciliação Bancária",
            "error": None,
        },
    )


@router.post("/financeiro/conciliacao/importar", response_class=HTMLResponse)
async def conciliacao_importar(
    request: Request,
    session: SessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.conciliacao.criar"))],
    conta_id: Annotated[str, Form()],
    conteudo: Annotated[str, Form()],
) -> HTMLResponse:
    try:
        await ConciliacaoService(session).import_ofx_lines(
            current_user.tenant_id,
            OfxImportInput(conta_id=uuid.UUID(conta_id), conteudo=conteudo),
        )
        await ConciliacaoService(session).auto_match(uuid.UUID(conta_id))
    except (AppError, ValueError) as exc:
        await session.rollback()
        contas = await BancoService(session).list_contas(PageParams(page=1, size=100))
        divergencias = await ConciliacaoService(session).list_divergencias(PageParams(page=1, size=25))
        return render(
            request,
            "financeiro/conciliacao.html",
            {
                "contas": contas.items,
                "page_result": divergencias,
                "title": "Conciliação Bancária",
                "error": _msg(exc),
            },
            status_code=400,
        )
    return RedirectResponse("/financeiro/conciliacao", status_code=303)


@router.post("/financeiro/conciliacao/{conta_id}/auto-match", response_class=HTMLResponse)
async def conciliacao_auto_match(
    session: SessionDep,
    conta_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.conciliacao.editar"))],
) -> RedirectResponse:
    await ConciliacaoService(session).auto_match(conta_id)
    return RedirectResponse("/financeiro/conciliacao", status_code=303)


@router.post("/financeiro/conciliacao/match", response_class=HTMLResponse)
async def conciliacao_match(
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.conciliacao.editar"))],
    extrato_id: Annotated[str, Form()],
    titulo_tipo: Annotated[str, Form()],
    titulo_id: Annotated[str, Form()],
) -> RedirectResponse:
    await ConciliacaoService(session).manual_match(
        ManualMatchInput(
            extrato_id=uuid.UUID(extrato_id),
            titulo_tipo=titulo_tipo,
            titulo_id=uuid.UUID(titulo_id),
        )
    )
    return RedirectResponse("/financeiro/conciliacao", status_code=303)


# ================================================================ Faturamento
@router.get("/financeiro/faturamento", response_class=HTMLResponse)
async def faturamento_view(
    request: Request,
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.faturamento.visualizar"))],
    page: int = 1,
    status: str = "",
) -> HTMLResponse:
    svc = FaturamentoService(session)
    st = FaturaStatus(status) if status else None
    faturas = await svc.list_faturas(PageParams(page=page, size=25), status=st)
    configs = await svc.list_configs(PageParams(page=1, size=100))
    lookups = await _lookups(session)
    return render(
        request,
        "financeiro/faturamento_list.html",
        {
            "page_result": faturas,
            "configs": configs.items,
            "title": "Faturamento",
            "status": status,
            "ciclos": [c.value for c in FaturamentoCiclo],
            "error": None,
            **lookups,
        },
    )


@router.post("/financeiro/faturamento/config/novo", response_class=HTMLResponse)
async def faturamento_config_criar(
    request: Request,
    session: SessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.faturamento.criar"))],
    cliente_id: Annotated[str, Form()],
    ciclo: Annotated[str, Form()] = "mensal",
    dia_fechamento: Annotated[str, Form()] = "1",
) -> HTMLResponse:
    try:
        await FaturamentoService(session).create_config(
            current_user.tenant_id,
            FaturamentoConfigCreate(
                cliente_id=uuid.UUID(cliente_id),
                ciclo=FaturamentoCiclo(ciclo),
                dia_fechamento=int(dia_fechamento) if dia_fechamento.strip() else 1,
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        svc = FaturamentoService(session)
        faturas = await svc.list_faturas(PageParams(page=1, size=25))
        configs = await svc.list_configs(PageParams(page=1, size=100))
        lookups = await _lookups(session)
        return render(
            request,
            "financeiro/faturamento_list.html",
            {
                "page_result": faturas,
                "configs": configs.items,
                "title": "Faturamento",
                "status": "",
                "ciclos": [c.value for c in FaturamentoCiclo],
                "error": _msg(exc),
                **lookups,
            },
            status_code=400,
        )
    return RedirectResponse("/financeiro/faturamento", status_code=303)


@router.post("/financeiro/faturamento/consolidar", response_class=HTMLResponse)
async def faturamento_consolidar(
    request: Request,
    session: SessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.faturamento.criar"))],
    cliente_id: Annotated[str, Form()],
    periodo_inicio: Annotated[str, Form()],
    periodo_fim: Annotated[str, Form()],
    vencimento: Annotated[str, Form()] = "",
) -> HTMLResponse:
    try:
        inicio = _date(periodo_inicio)
        fim = _date(periodo_fim)
        if not inicio or not fim:
            raise ValueError("Período de faturamento é obrigatório.")
        fatura = await FaturamentoService(session).consolidar(
            current_user.tenant_id,
            ConsolidarInput(
                cliente_id=uuid.UUID(cliente_id),
                periodo_inicio=inicio,
                periodo_fim=fim,
                vencimento=_date(vencimento),
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        svc = FaturamentoService(session)
        faturas = await svc.list_faturas(PageParams(page=1, size=25))
        configs = await svc.list_configs(PageParams(page=1, size=100))
        lookups = await _lookups(session)
        return render(
            request,
            "financeiro/faturamento_list.html",
            {
                "page_result": faturas,
                "configs": configs.items,
                "title": "Faturamento",
                "status": "",
                "ciclos": [c.value for c in FaturamentoCiclo],
                "error": _msg(exc),
                **lookups,
            },
            status_code=400,
        )
    return RedirectResponse(f"/financeiro/faturamento/{fatura.id}", status_code=303)


@router.get("/financeiro/faturamento/{fatura_id}", response_class=HTMLResponse)
async def faturamento_detalhe(
    request: Request,
    session: SessionDep,
    fatura_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.faturamento.visualizar"))],
) -> HTMLResponse:
    svc = FaturamentoService(session)
    fatura = await svc.get_fatura(fatura_id)
    titulos = await svc.list_titulos(fatura_id)
    lookups = await _lookups(session)
    return render(
        request,
        "financeiro/fatura_detalhe.html",
        {"fatura": fatura, "titulos": titulos, "title": f"Fatura {fatura.numero}", **lookups},
    )


@router.post("/financeiro/faturamento/{fatura_id}/emitir", response_class=HTMLResponse)
async def faturamento_emitir(
    session: SessionDep,
    fatura_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("financeiro.faturamento.editar"))],
) -> RedirectResponse:
    await FaturamentoService(session).emitir(fatura_id)
    return RedirectResponse(f"/financeiro/faturamento/{fatura_id}", status_code=303)
