"""Rotas Web — módulo Intermediação."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_web_permission, require_web_user
from app.core.exceptions import AppError
from app.core.templating import render
from app.modules.cadastros.service_extra import FornecedorService
from app.modules.frota.service import CategoriasService, VeiculoService
from app.modules.identity.service import AuthenticatedUser
from app.modules.intermediacao.schemas import (
    ContratoFornecedorCreate,
    ContratoFornecedorUpdate,
    ContratoPrecoCreate,
    IndisponibilidadeTerceiroCreate,
    IntermediacaoConfigUpdate,
)
from app.modules.intermediacao.service import IntermediacaoService
from app.modules.tenants.service import FilialService
from app.core.pagination import PageParams
from app.shared.enums import (
    ContratoFornecedorStatus,
    IndisponibilidadeTerceiroMotivo,
    ModeloNegocioTerceiro,
    ModoOperacaoLocadora,
    TipoCalculoRepasse,
)

router = APIRouter()
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


def _msg(exc: AppError | ValueError) -> str:
    return exc.message if isinstance(exc, AppError) else str(exc)


@router.get("/intermediacao/config", response_class=HTMLResponse)
async def config_view(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("intermediacao.config.visualizar"))
    ],
) -> HTMLResponse:
    cfg = await IntermediacaoService(session).get_config(current_user.tenant_id)
    return render(
        request,
        "intermediacao/config.html",
        {"title": "Intermediação — Configurações", "config": cfg},
    )


@router.post("/intermediacao/config")
async def config_save(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("intermediacao.config.editar"))
    ],
    modo_operacao: Annotated[str, Form()],
    exige_contrato_fornecedor: Annotated[bool, Form()] = False,
    aprovar_reserva_automaticamente: Annotated[bool, Form()] = False,
    publicar_terceiros_site: Annotated[bool, Form()] = False,
    priorizar_frota_propria: Annotated[bool, Form()] = False,
    margem_minima_percentual: Annotated[str, Form()] = "10",
    buffer_disponibilidade_horas: Annotated[int, Form()] = 4,
    observacoes: Annotated[str, Form()] = "",
) -> RedirectResponse:
    try:
        await IntermediacaoService(session).update_config(
            current_user.tenant_id,
            IntermediacaoConfigUpdate(
                modo_operacao=ModoOperacaoLocadora(modo_operacao),
                exige_contrato_fornecedor=exige_contrato_fornecedor,
                aprovar_reserva_automaticamente=aprovar_reserva_automaticamente,
                publicar_terceiros_site=publicar_terceiros_site,
                priorizar_frota_propria=priorizar_frota_propria,
                margem_minima_percentual=Decimal(margem_minima_percentual.replace(",", ".")),
                buffer_disponibilidade_horas=buffer_disponibilidade_horas,
                observacoes=observacoes or None,
            ),
        )
        request.session["_flash"] = {"type": "success", "message": "Configurações salvas."}
    except (AppError, ValueError) as exc:
        await session.rollback()
        request.session["_flash"] = {"type": "danger", "message": _msg(exc)}
    return RedirectResponse(url="/intermediacao/config", status_code=303)


@router.get("/intermediacao/contratos-fornecedor", response_class=HTMLResponse)
async def contratos_list(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("intermediacao.contrato.visualizar"))
    ],
) -> HTMLResponse:
    svc = IntermediacaoService(session)
    contratos = await svc.list_contratos_fornecedor(current_user.tenant_id)
    fornecedores = {f.id: f for f in await svc.list_locadoras_parceiras(current_user.tenant_id)}
    return render(
        request,
        "intermediacao/contratos_list.html",
        {
            "title": "Contratos com Locadoras Parceiras",
            "contratos": contratos,
            "fornecedores": fornecedores,
        },
    )


@router.get("/intermediacao/contratos-fornecedor/novo", response_class=HTMLResponse)
async def contrato_new(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("intermediacao.contrato.criar"))
    ],
) -> HTMLResponse:
    fornecedores = await IntermediacaoService(session).list_locadoras_parceiras(
        current_user.tenant_id
    )
    return render(
        request,
        "intermediacao/contrato_form.html",
        {
            "title": "Novo Contrato de Intermediação",
            "contrato": None,
            "precos": [],
            "fornecedores": fornecedores,
            "categorias": (await CategoriasService(session).list_items(PageParams(page=1, size=200))).items,
            "filiais": (await FilialService(session).list_filiais(PageParams(page=1, size=100))).items,
            "error": None,
            "action": "/intermediacao/contratos-fornecedor/novo",
        },
    )


@router.post("/intermediacao/contratos-fornecedor/novo")
async def contrato_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("intermediacao.contrato.criar"))
    ],
    fornecedor_id: Annotated[str, Form()],
    numero: Annotated[str, Form()],
    titulo: Annotated[str, Form()],
    modelo_negocio: Annotated[str, Form()],
    tipo_calculo: Annotated[str, Form()],
    vigencia_inicio: Annotated[str, Form()],
    vigencia_fim: Annotated[str, Form()] = "",
    percentual_repasse: Annotated[str, Form()] = "",
    percentual_comissao: Annotated[str, Form()] = "",
    valor_diaria_repasse: Annotated[str, Form()] = "",
    prazo_pagamento_dias: Annotated[int, Form()] = 30,
    clausulas: Annotated[str, Form()] = "",
) -> RedirectResponse:
    try:
        data = ContratoFornecedorCreate(
            fornecedor_id=uuid.UUID(fornecedor_id),
            numero=numero,
            titulo=titulo,
            modelo_negocio=ModeloNegocioTerceiro(modelo_negocio),
            tipo_calculo=TipoCalculoRepasse(tipo_calculo),
            vigencia_inicio=date.fromisoformat(vigencia_inicio),
            vigencia_fim=date.fromisoformat(vigencia_fim) if vigencia_fim else None,
            percentual_repasse=Decimal(percentual_repasse.replace(",", ".")) if percentual_repasse else None,
            percentual_comissao=Decimal(percentual_comissao.replace(",", ".")) if percentual_comissao else None,
            valor_diaria_repasse=Decimal(valor_diaria_repasse.replace(",", ".")) if valor_diaria_repasse else None,
            prazo_pagamento_dias=prazo_pagamento_dias,
            clausulas=clausulas or None,
        )
        c = await IntermediacaoService(session).create_contrato_fornecedor(
            current_user.tenant_id, data
        )
        c.status = ContratoFornecedorStatus.ATIVO
        request.session["_flash"] = {"type": "success", "message": "Contrato criado."}
        return RedirectResponse(
            url=f"/intermediacao/contratos-fornecedor/{c.id}/editar", status_code=303
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        request.session["_flash"] = {"type": "danger", "message": _msg(exc)}
        return RedirectResponse(url="/intermediacao/contratos-fornecedor/novo", status_code=303)


@router.get("/intermediacao/contratos-fornecedor/{contrato_id}/editar", response_class=HTMLResponse)
async def contrato_edit(
    contrato_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("intermediacao.contrato.editar"))
    ],
) -> HTMLResponse:
    svc = IntermediacaoService(session)
    contrato = await svc.get_contrato_fornecedor(contrato_id)
    precos = await svc.list_precos_contrato(contrato_id)
    fornecedores = await svc.list_locadoras_parceiras(current_user.tenant_id)
    return render(
        request,
        "intermediacao/contrato_form.html",
        {
            "title": f"Contrato {contrato.numero}",
            "contrato": contrato,
            "precos": precos,
            "fornecedores": fornecedores,
            "categorias": (await CategoriasService(session).list_items(PageParams(page=1, size=200))).items,
            "filiais": (await FilialService(session).list_filiais(PageParams(page=1, size=100))).items,
            "error": None,
            "action": f"/intermediacao/contratos-fornecedor/{contrato_id}/editar",
        },
    )


@router.post("/intermediacao/contratos-fornecedor/{contrato_id}/precos")
async def contrato_add_preco(
    contrato_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("intermediacao.contrato.editar"))
    ],
    vigencia_inicio: Annotated[str, Form()],
    valor_cliente_diaria: Annotated[str, Form()],
    valor_repasse_diaria: Annotated[str, Form()],
    categoria_id: Annotated[str, Form()] = "",
    filial_id: Annotated[str, Form()] = "",
    vigencia_fim: Annotated[str, Form()] = "",
    dias_minimos: Annotated[int, Form()] = 1,
    percentual_comissao: Annotated[str, Form()] = "",
) -> RedirectResponse:
    try:
        await IntermediacaoService(session).add_preco_contrato(
            current_user.tenant_id,
            contrato_id,
            ContratoPrecoCreate(
                categoria_id=uuid.UUID(categoria_id) if categoria_id else None,
                filial_id=uuid.UUID(filial_id) if filial_id else None,
                vigencia_inicio=date.fromisoformat(vigencia_inicio),
                vigencia_fim=date.fromisoformat(vigencia_fim) if vigencia_fim else None,
                dias_minimos=dias_minimos,
                valor_cliente_diaria=Decimal(valor_cliente_diaria.replace(",", ".")),
                valor_repasse_diaria=Decimal(valor_repasse_diaria.replace(",", ".")),
                percentual_comissao=Decimal(percentual_comissao.replace(",", "."))
                if percentual_comissao
                else None,
            ),
        )
        request.session["_flash"] = {"type": "success", "message": "Faixa de preço adicionada."}
    except (AppError, ValueError) as exc:
        await session.rollback()
        request.session["_flash"] = {"type": "danger", "message": _msg(exc)}
    return RedirectResponse(
        url=f"/intermediacao/contratos-fornecedor/{contrato_id}/editar", status_code=303
    )


@router.get("/intermediacao/indisponibilidades", response_class=HTMLResponse)
async def indisponibilidades_list(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("intermediacao.indisponibilidade.visualizar"))
    ],
) -> HTMLResponse:
    from sqlalchemy import select
    from app.modules.intermediacao.models import FrotaIndisponibilidadeTerceiro

    rows = list(
        (
            await session.execute(
                select(FrotaIndisponibilidadeTerceiro)
                .where(
                    FrotaIndisponibilidadeTerceiro.tenant_id == current_user.tenant_id,
                    FrotaIndisponibilidadeTerceiro.deleted_at.is_(None),
                )
                .order_by(FrotaIndisponibilidadeTerceiro.inicio_em.desc())
                .limit(100)
            )
        ).scalars().all()
    )
    veiculos = {
        v.id: v
        for v in (
            await VeiculoService(session).list_items(PageParams(page=1, size=500))
        ).items
    }
    fornecedores = {
        f.id: f
        for f in await IntermediacaoService(session).list_locadoras_parceiras(
            current_user.tenant_id
        )
    }
    return render(
        request,
        "intermediacao/indisponibilidades_list.html",
        {
            "title": "Indisponibilidades de Terceiros",
            "rows": rows,
            "veiculos": veiculos,
            "fornecedores": fornecedores,
            "veiculos_terceiros": [v for v in veiculos.values() if v.propriedade.value == "terceirizada"],
            "motivos": list(IndisponibilidadeTerceiroMotivo),
        },
    )


@router.post("/intermediacao/indisponibilidades")
async def indisponibilidade_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("intermediacao.indisponibilidade.criar"))
    ],
    veiculo_id: Annotated[str, Form()],
    fornecedor_id: Annotated[str, Form()],
    inicio_em: Annotated[str, Form()],
    fim_em: Annotated[str, Form()] = "",
    motivo: Annotated[str, Form()] = "locado_pelo_proprietario",
    sincronizar_site: Annotated[bool, Form()] = False,
    observacoes: Annotated[str, Form()] = "",
) -> RedirectResponse:
    from datetime import datetime

    try:
        await IntermediacaoService(session).registrar_indisponibilidade(
            current_user.tenant_id,
            IndisponibilidadeTerceiroCreate(
                veiculo_id=uuid.UUID(veiculo_id),
                fornecedor_id=uuid.UUID(fornecedor_id),
                inicio_em=datetime.fromisoformat(inicio_em),
                fim_em=datetime.fromisoformat(fim_em) if fim_em else None,
                motivo=IndisponibilidadeTerceiroMotivo(motivo),
                sincronizar_site=sincronizar_site,
                observacoes=observacoes or None,
            ),
            user_id=current_user.id,
        )
        request.session["_flash"] = {"type": "success", "message": "Indisponibilidade registrada."}
    except (AppError, ValueError) as exc:
        await session.rollback()
        request.session["_flash"] = {"type": "danger", "message": _msg(exc)}
    return RedirectResponse(url="/intermediacao/indisponibilidades", status_code=303)


@router.get("/intermediacao/contratos-fornecedor/json")
async def contratos_json(
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("intermediacao.contrato.visualizar"))
    ],
    fornecedor_id: str = "",
) -> JSONResponse:
    svc = IntermediacaoService(session)
    fid = uuid.UUID(fornecedor_id) if fornecedor_id else None
    contratos = await svc.list_contratos_fornecedor(current_user.tenant_id, fornecedor_id=fid)
    return JSONResponse(
        [
            {
                "id": str(c.id),
                "numero": c.numero,
                "titulo": c.titulo,
                "status": c.status.value,
                "modelo_negocio": c.modelo_negocio.value,
            }
            for c in contratos
            if c.status == ContratoFornecedorStatus.ATIVO
        ]
    )


@router.post("/intermediacao/contratos-fornecedor/{contrato_id}/editar")
async def contrato_update(
    contrato_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("intermediacao.contrato.editar"))
    ],
    titulo: Annotated[str, Form()],
    modelo_negocio: Annotated[str, Form()],
    tipo_calculo: Annotated[str, Form()],
    vigencia_inicio: Annotated[str, Form()],
    vigencia_fim: Annotated[str, Form()] = "",
    percentual_repasse: Annotated[str, Form()] = "",
    percentual_comissao: Annotated[str, Form()] = "",
    valor_diaria_repasse: Annotated[str, Form()] = "",
    prazo_pagamento_dias: Annotated[int, Form()] = 30,
    clausulas: Annotated[str, Form()] = "",
    status: Annotated[str, Form()] = "ativo",
) -> RedirectResponse:
    try:
        await IntermediacaoService(session).update_contrato_fornecedor(
            contrato_id,
            ContratoFornecedorUpdate(
                titulo=titulo,
                status=ContratoFornecedorStatus(status),
                modelo_negocio=ModeloNegocioTerceiro(modelo_negocio),
                tipo_calculo=TipoCalculoRepasse(tipo_calculo),
                vigencia_inicio=date.fromisoformat(vigencia_inicio),
                vigencia_fim=date.fromisoformat(vigencia_fim) if vigencia_fim else None,
                percentual_repasse=Decimal(percentual_repasse.replace(",", ".")) if percentual_repasse else None,
                percentual_comissao=Decimal(percentual_comissao.replace(",", ".")) if percentual_comissao else None,
                valor_diaria_repasse=Decimal(valor_diaria_repasse.replace(",", ".")) if valor_diaria_repasse else None,
                prazo_pagamento_dias=prazo_pagamento_dias,
                clausulas=clausulas or None,
            ),
        )
        request.session["_flash"] = {"type": "success", "message": "Contrato atualizado."}
    except (AppError, ValueError) as exc:
        await session.rollback()
        request.session["_flash"] = {"type": "danger", "message": _msg(exc)}
    return RedirectResponse(
        url=f"/intermediacao/contratos-fornecedor/{contrato_id}/editar", status_code=303
    )


@router.get("/intermediacao/aprovacoes", response_class=HTMLResponse)
async def aprovacoes_list(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("intermediacao.reserva.aprovar"))
    ],
) -> HTMLResponse:
    from app.modules.cadastros.service import ClienteService

    svc = IntermediacaoService(session)
    pendentes = await svc.list_aprovacoes_pendentes(current_user.tenant_id)
    fornecedores = {f.id: f for f in await svc.list_locadoras_parceiras(current_user.tenant_id)}
    clientes = {
        c.id: c
        for c in (await ClienteService(session).list_clientes(PageParams(page=1, size=500))).items
    }
    return render(
        request,
        "intermediacao/aprovacoes_list.html",
        {
            "title": "Aprovações de Intermediação",
            "pendentes": pendentes,
            "fornecedores": fornecedores,
            "clientes": clientes,
        },
    )


@router.post("/intermediacao/aprovacoes/{reserva_id}/aprovar")
async def aprovacao_confirmar(
    reserva_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("intermediacao.reserva.aprovar"))
    ],
) -> RedirectResponse:
    try:
        await IntermediacaoService(session).aprovar_reserva_fornecedor(
            reserva_id, user_id=current_user.id
        )
        request.session["_flash"] = {"type": "success", "message": "Intermediação aprovada."}
    except (AppError, ValueError) as exc:
        await session.rollback()
        request.session["_flash"] = {"type": "danger", "message": _msg(exc)}
    return RedirectResponse(url="/intermediacao/aprovacoes", status_code=303)


@router.post("/intermediacao/aprovacoes/{reserva_id}/rejeitar")
async def aprovacao_rejeitar(
    reserva_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("intermediacao.reserva.aprovar"))
    ],
    motivo: Annotated[str, Form()],
) -> RedirectResponse:
    try:
        await IntermediacaoService(session).rejeitar_reserva_fornecedor(
            reserva_id, motivo, user_id=current_user.id
        )
        request.session["_flash"] = {"type": "success", "message": "Intermediação rejeitada."}
    except (AppError, ValueError) as exc:
        await session.rollback()
        request.session["_flash"] = {"type": "danger", "message": _msg(exc)}
    return RedirectResponse(url="/intermediacao/aprovacoes", status_code=303)


@router.get("/intermediacao/repasses", response_class=HTMLResponse)
async def repasses_list(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("intermediacao.repasse.visualizar"))
    ],
) -> HTMLResponse:
    svc = IntermediacaoService(session)
    rows = await svc.list_repasse_lancamentos(current_user.tenant_id)
    fornecedores = {f.id: f for f in await svc.list_locadoras_parceiras(current_user.tenant_id)}
    return render(
        request,
        "intermediacao/repasses_list.html",
        {"title": "Repasses e Comissões", "rows": rows, "fornecedores": fornecedores},
    )


@router.post("/intermediacao/site/sincronizar")
async def site_sincronizar(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("intermediacao.config.editar"))
    ],
) -> RedirectResponse:
    try:
        stats = await IntermediacaoService(session).sincronizar_catalogo_site(current_user.tenant_id)
        request.session["_flash"] = {
            "type": "success",
            "message": f"Site sincronizado: {stats['publicados']} publicados, {stats['ocultos']} ocultos.",
        }
    except (AppError, ValueError) as exc:
        await session.rollback()
        request.session["_flash"] = {"type": "danger", "message": _msg(exc)}
    return RedirectResponse(url="/intermediacao/config", status_code=303)
