"""API REST do módulo Financeiro (§9)."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import ApiSessionDep, require_api_permission
from app.core.pagination import PageParams
from app.modules.financeiro.schemas import (
    AgingBucket,
    CaixaAbrirInput,
    CaixaFecharInput,
    CaixaLancamentoCreate,
    CaixaSessaoRead,
    CartaoAutorizarInput,
    CartaoCapturarInput,
    CartaoRead,
    ConsolidarInput,
    ContaBancariaCreate,
    ContaBancariaRead,
    ContaPagarCreate,
    ContaPagarRead,
    ContaReceberCreate,
    ContaReceberRead,
    ExtratoLinhaRead,
    FaturamentoConfigCreate,
    FaturamentoConfigRead,
    FaturaRead,
    ManualMatchInput,
    OfxImportInput,
    PagarAprovarInput,
    PagarEfetivarInput,
    PixChaveCreate,
    PixChaveRead,
    PixCobrancaCreate,
    PixCobrancaRead,
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
from app.shared.enums import (
    CaixaSessaoStatus,
    CartaoTransacaoStatus,
    ConciliacaoStatus,
    ContaPagarOrigem,
    ContaReceberOrigem,
    FaturaStatus,
    PixCobrancaStatus,
    TituloStatus,
)

router = APIRouter(prefix="/financeiro", tags=["Financeiro"])


def _page_dict(result: Any, read_cls: type) -> dict:
    return {
        "items": [read_cls.model_validate(i) for i in result.items],
        "total": result.total,
        "page": result.page,
        "size": result.size,
        "pages": result.pages,
    }


# ------------------------------------------------------------------ Caixa
@router.get("/caixa", response_model=dict)
async def api_list_caixa(
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.caixa.visualizar"))],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    status_: CaixaSessaoStatus | None = Query(None, alias="status"),
) -> dict:
    result = await CaixaService(session).list_sessoes(PageParams(page=page, size=size), status=status_)
    return _page_dict(result, CaixaSessaoRead)


@router.post("/caixa/abrir", response_model=CaixaSessaoRead, status_code=status.HTTP_201_CREATED)
async def api_abrir_caixa(
    payload: CaixaAbrirInput,
    session: ApiSessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.caixa.abrir"))],
) -> CaixaSessaoRead:
    item = await CaixaService(session).abrir(current_user.tenant_id, payload, operador_id=current_user.id)
    return CaixaSessaoRead.model_validate(item)


@router.post("/caixa/{sessao_id}/lancamento", response_model=dict, status_code=status.HTTP_201_CREATED)
async def api_caixa_lancamento(
    sessao_id: uuid.UUID,
    payload: CaixaLancamentoCreate,
    session: ApiSessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.caixa.editar"))],
) -> dict:
    lanc = await CaixaService(session).registrar_lancamento(sessao_id, payload, created_by=current_user.id)
    return {"id": str(lanc.id), "sessao_id": str(lanc.sessao_id), "valor": str(lanc.valor)}


@router.post("/caixa/{sessao_id}/fechar", response_model=CaixaSessaoRead)
async def api_fechar_caixa(
    sessao_id: uuid.UUID,
    payload: CaixaFecharInput,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.caixa.fechar"))],
) -> CaixaSessaoRead:
    return CaixaSessaoRead.model_validate(await CaixaService(session).fechar(sessao_id, payload))


# ------------------------------------------------------------------ Contas a Receber
@router.get("/receber", response_model=dict)
async def api_list_receber(
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.receber.visualizar"))],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    status_: TituloStatus | None = Query(None, alias="status"),
    cliente_id: uuid.UUID | None = None,
    origem: ContaReceberOrigem | None = None,
) -> dict:
    result = await ContaReceberService(session).list_items(
        PageParams(page=page, size=size), status=status_, cliente_id=cliente_id, origem=origem
    )
    return _page_dict(result, ContaReceberRead)


@router.post("/receber", response_model=ContaReceberRead, status_code=status.HTTP_201_CREATED)
async def api_create_receber(
    payload: ContaReceberCreate,
    session: ApiSessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.receber.criar"))],
) -> ContaReceberRead:
    return ContaReceberRead.model_validate(
        await ContaReceberService(session).create(current_user.tenant_id, payload)
    )


@router.get("/receber/aging", response_model=list[AgingBucket])
async def api_receber_aging(
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.receber.visualizar"))],
) -> list[AgingBucket]:
    return [AgingBucket(**b) for b in await ContaReceberService(session).aging()]


@router.get("/receber/{titulo_id}", response_model=ContaReceberRead)
async def api_get_receber(
    titulo_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.receber.visualizar"))],
) -> ContaReceberRead:
    return ContaReceberRead.model_validate(await ContaReceberService(session).get(titulo_id))


@router.post("/receber/{titulo_id}/baixar", response_model=ContaReceberRead)
async def api_baixar_receber(
    titulo_id: uuid.UUID,
    payload: ReceberBaixaInput,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.receber.baixar"))],
) -> ContaReceberRead:
    return ContaReceberRead.model_validate(await ContaReceberService(session).baixar(titulo_id, payload))


@router.post("/receber/{titulo_id}/estornar", response_model=ContaReceberRead)
async def api_estornar_receber(
    titulo_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.receber.estornar"))],
) -> ContaReceberRead:
    return ContaReceberRead.model_validate(await ContaReceberService(session).estornar(titulo_id))


@router.post("/receber/{titulo_id}/cancelar", response_model=ContaReceberRead)
async def api_cancelar_receber(
    titulo_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.receber.editar"))],
) -> ContaReceberRead:
    return ContaReceberRead.model_validate(await ContaReceberService(session).cancelar(titulo_id))


# ------------------------------------------------------------------ Contas a Pagar
@router.get("/pagar", response_model=dict)
async def api_list_pagar(
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.pagar.visualizar"))],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    status_: TituloStatus | None = Query(None, alias="status"),
    fornecedor_id: uuid.UUID | None = None,
    origem: ContaPagarOrigem | None = None,
) -> dict:
    result = await ContaPagarService(session).list_items(
        PageParams(page=page, size=size), status=status_, fornecedor_id=fornecedor_id, origem=origem
    )
    return _page_dict(result, ContaPagarRead)


@router.post("/pagar", response_model=ContaPagarRead, status_code=status.HTTP_201_CREATED)
async def api_create_pagar(
    payload: ContaPagarCreate,
    session: ApiSessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.pagar.criar"))],
) -> ContaPagarRead:
    return ContaPagarRead.model_validate(
        await ContaPagarService(session).create(current_user.tenant_id, payload)
    )


@router.get("/pagar/{titulo_id}", response_model=ContaPagarRead)
async def api_get_pagar(
    titulo_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.pagar.visualizar"))],
) -> ContaPagarRead:
    return ContaPagarRead.model_validate(await ContaPagarService(session).get(titulo_id))


@router.post("/pagar/{titulo_id}/aprovar", response_model=ContaPagarRead)
async def api_aprovar_pagar(
    titulo_id: uuid.UUID,
    session: ApiSessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.pagar.aprovar"))],
    payload: PagarAprovarInput | None = None,
) -> ContaPagarRead:
    data = payload or PagarAprovarInput()
    if data.aprovado_por is None:
        data = data.model_copy(update={"aprovado_por": current_user.id})
    return ContaPagarRead.model_validate(await ContaPagarService(session).aprovar(titulo_id, data))


@router.post("/pagar/{titulo_id}/efetivar", response_model=ContaPagarRead)
async def api_efetivar_pagar(
    titulo_id: uuid.UUID,
    payload: PagarEfetivarInput,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.pagar.efetivar"))],
) -> ContaPagarRead:
    return ContaPagarRead.model_validate(
        await ContaPagarService(session).efetivar_pagamento(titulo_id, payload)
    )


# ------------------------------------------------------------------ PIX
@router.get("/pix/chaves", response_model=dict)
async def api_list_pix_chaves(
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.pix.visualizar"))],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
) -> dict:
    return _page_dict(await PixService(session).list_chaves(PageParams(page=page, size=size)), PixChaveRead)


@router.post("/pix/chaves", response_model=PixChaveRead, status_code=status.HTTP_201_CREATED)
async def api_create_pix_chave(
    payload: PixChaveCreate,
    session: ApiSessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.pix.criar"))],
) -> PixChaveRead:
    return PixChaveRead.model_validate(await PixService(session).create_chave(current_user.tenant_id, payload))


@router.get("/pix/cobrancas", response_model=dict)
async def api_list_pix_cobrancas(
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.pix.visualizar"))],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    status_: PixCobrancaStatus | None = Query(None, alias="status"),
) -> dict:
    result = await PixService(session).list_cobrancas(PageParams(page=page, size=size), status=status_)
    return _page_dict(result, PixCobrancaRead)


@router.post("/pix/cobrancas", response_model=PixCobrancaRead, status_code=status.HTTP_201_CREATED)
async def api_create_pix_cobranca(
    payload: PixCobrancaCreate,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.pix.criar"))],
) -> PixCobrancaRead:
    return PixCobrancaRead.model_validate(await PixService(session).create_cobranca_from_titulo(payload))


@router.post("/pix/cobrancas/{cobranca_id}/confirmar", response_model=PixCobrancaRead)
async def api_confirmar_pix(
    cobranca_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.pix.editar"))],
) -> PixCobrancaRead:
    return PixCobrancaRead.model_validate(await PixService(session).confirmar_pagamento(cobranca_id))


# ------------------------------------------------------------------ Cartões
@router.get("/cartoes", response_model=dict)
async def api_list_cartoes(
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.cartoes.visualizar"))],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    status_: CartaoTransacaoStatus | None = Query(None, alias="status"),
) -> dict:
    result = await CartaoService(session).list_items(PageParams(page=page, size=size), status=status_)
    return _page_dict(result, CartaoRead)


@router.post("/cartoes/autorizar", response_model=CartaoRead, status_code=status.HTTP_201_CREATED)
async def api_autorizar_cartao(
    payload: CartaoAutorizarInput,
    session: ApiSessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.cartoes.criar"))],
) -> CartaoRead:
    return CartaoRead.model_validate(await CartaoService(session).autorizar(current_user.tenant_id, payload))


@router.post("/cartoes/{transacao_id}/capturar", response_model=CartaoRead)
async def api_capturar_cartao(
    transacao_id: uuid.UUID,
    payload: CartaoCapturarInput,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.cartoes.editar"))],
) -> CartaoRead:
    return CartaoRead.model_validate(await CartaoService(session).capturar(transacao_id, payload))


@router.post("/cartoes/{transacao_id}/cancelar", response_model=CartaoRead)
async def api_cancelar_cartao(
    transacao_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.cartoes.editar"))],
) -> CartaoRead:
    return CartaoRead.model_validate(await CartaoService(session).cancelar(transacao_id))


@router.post("/cartoes/{transacao_id}/estornar", response_model=CartaoRead)
async def api_estornar_cartao(
    transacao_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.cartoes.editar"))],
) -> CartaoRead:
    return CartaoRead.model_validate(await CartaoService(session).estornar(transacao_id))


# ------------------------------------------------------------------ Bancos
@router.get("/bancos", response_model=dict)
async def api_list_bancos(
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.bancos.visualizar"))],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
) -> dict:
    return _page_dict(await BancoService(session).list_contas(PageParams(page=page, size=size)), ContaBancariaRead)


@router.post("/bancos", response_model=ContaBancariaRead, status_code=status.HTTP_201_CREATED)
async def api_create_banco(
    payload: ContaBancariaCreate,
    session: ApiSessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.bancos.criar"))],
) -> ContaBancariaRead:
    return ContaBancariaRead.model_validate(await BancoService(session).create_conta(current_user.tenant_id, payload))


@router.get("/bancos/{conta_id}/extrato", response_model=dict)
async def api_banco_extrato(
    conta_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.bancos.visualizar"))],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    status_: ConciliacaoStatus | None = Query(None, alias="status"),
) -> dict:
    result = await BancoService(session).list_extrato(
        PageParams(page=page, size=size), conta_id=conta_id, status=status_
    )
    return _page_dict(result, ExtratoLinhaRead)


# ------------------------------------------------------------------ Conciliação
@router.post("/conciliacao/importar", response_model=dict)
async def api_conciliacao_importar(
    payload: OfxImportInput,
    session: ApiSessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.conciliacao.criar"))],
) -> dict:
    criadas = await ConciliacaoService(session).import_ofx_lines(current_user.tenant_id, payload)
    return {"linhas_importadas": criadas}


@router.post("/conciliacao/{conta_id}/auto-match", response_model=dict)
async def api_conciliacao_auto_match(
    conta_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.conciliacao.editar"))],
) -> dict:
    conciliadas = await ConciliacaoService(session).auto_match(conta_id)
    return {"conciliadas": conciliadas}


@router.post("/conciliacao/match", response_model=ExtratoLinhaRead)
async def api_conciliacao_match(
    payload: ManualMatchInput,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.conciliacao.editar"))],
) -> ExtratoLinhaRead:
    return ExtratoLinhaRead.model_validate(await ConciliacaoService(session).manual_match(payload))


@router.get("/conciliacao/divergencias", response_model=dict)
async def api_conciliacao_divergencias(
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.conciliacao.visualizar"))],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
) -> dict:
    result = await ConciliacaoService(session).list_divergencias(PageParams(page=page, size=size))
    return _page_dict(result, ExtratoLinhaRead)


# ------------------------------------------------------------------ Faturamento
@router.get("/faturamento/configs", response_model=dict)
async def api_list_faturamento_configs(
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.faturamento.visualizar"))],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
) -> dict:
    return _page_dict(
        await FaturamentoService(session).list_configs(PageParams(page=page, size=size)),
        FaturamentoConfigRead,
    )


@router.post("/faturamento/configs", response_model=FaturamentoConfigRead, status_code=status.HTTP_201_CREATED)
async def api_create_faturamento_config(
    payload: FaturamentoConfigCreate,
    session: ApiSessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.faturamento.criar"))],
) -> FaturamentoConfigRead:
    return FaturamentoConfigRead.model_validate(
        await FaturamentoService(session).create_config(current_user.tenant_id, payload)
    )


@router.get("/faturamento/faturas", response_model=dict)
async def api_list_faturas(
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.faturamento.visualizar"))],
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    status_: FaturaStatus | None = Query(None, alias="status"),
) -> dict:
    result = await FaturamentoService(session).list_faturas(PageParams(page=page, size=size), status=status_)
    return _page_dict(result, FaturaRead)


@router.post("/faturamento/consolidar", response_model=FaturaRead, status_code=status.HTTP_201_CREATED)
async def api_consolidar_fatura(
    payload: ConsolidarInput,
    session: ApiSessionDep,
    current_user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.faturamento.criar"))],
) -> FaturaRead:
    return FaturaRead.model_validate(await FaturamentoService(session).consolidar(current_user.tenant_id, payload))


@router.post("/faturamento/faturas/{fatura_id}/emitir", response_model=FaturaRead)
async def api_emitir_fatura(
    fatura_id: uuid.UUID,
    session: ApiSessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_api_permission("financeiro.faturamento.editar"))],
) -> FaturaRead:
    return FaturaRead.model_validate(await FaturamentoService(session).emitir(fatura_id))
