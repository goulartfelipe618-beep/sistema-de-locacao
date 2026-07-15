"""Rotas Web: motoristas, parceiros, fornecedores, vendedores."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_web_permission
from app.core.exceptions import AppError
from app.core.pagination import PageParams
from app.core.templating import render
from app.modules.cadastros.schemas_extra import (
    FornecedorCreate,
    FornecedorUpdate,
    MotoristaCreate,
    MotoristaUpdate,
    ParceiroCreate,
    ParceiroUpdate,
    VendedorCreate,
    VendedorUpdate,
)
from app.modules.cadastros.service import TabelaAuxiliarService
from app.modules.cadastros.service_extra import (
    FornecedorService,
    MotoristaService,
    ParceiroService,
    VendedorService,
)
from app.modules.identity.service import AuthenticatedUser
from app.modules.tenants.service import FilialService
from app.shared.enums import (
    CadastroStatus,
    MotoristaCnhStatus,
    MotoristaVinculo,
    ParceiroTipo,
    PersonType,
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
    if not raw:
        return None
    return date.fromisoformat(raw)


async def _categorias_fornecedor(session: AsyncSession, tenant_id: uuid.UUID):
    svc = TabelaAuxiliarService(session)
    await svc.ensure_defaults(tenant_id)
    return (
        await svc.list_by_grupo(
            "categoria_fornecedor", PageParams(page=1, size=100), apenas_ativos=True
        )
    ).items


async def _cnh_cats(session: AsyncSession, tenant_id: uuid.UUID):
    svc = TabelaAuxiliarService(session)
    await svc.ensure_defaults(tenant_id)
    return (
        await svc.list_by_grupo("cnh_categoria", PageParams(page=1, size=50), apenas_ativos=True)
    ).items


# ============================================================== Motoristas
@router.get("/cadastros/motoristas", response_class=HTMLResponse)
async def motoristas_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("cadastros.motorista.visualizar"))],
    page: int = 1,
    q: str = "",
) -> HTMLResponse:
    result = await MotoristaService(session).list_items(PageParams(page=page, size=25), search=q or None)
    return render(
        request,
        "cadastros/motoristas_list.html",
        {"page_result": result, "q": q, "title": "Motoristas"},
    )


@router.get("/cadastros/motoristas/novo", response_class=HTMLResponse)
async def motorista_new(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("cadastros.motorista.criar"))
    ],
) -> HTMLResponse:
    return render(
        request,
        "cadastros/motorista_form.html",
        {
            "item": None,
            "error": None,
            "cnh_cats": await _cnh_cats(session, current_user.tenant_id),
            "title": "Novo Motorista",
            "action": "/cadastros/motoristas/novo",
        },
    )


@router.post("/cadastros/motoristas/novo", response_class=HTMLResponse)
async def motorista_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("cadastros.motorista.criar"))
    ],
    nome: Annotated[str, Form()],
    vinculo: Annotated[str, Form()] = "terceiro",
    status: Annotated[str, Form()] = "active",
    cpf: Annotated[str, Form()] = "",
    email: Annotated[str, Form()] = "",
    celular: Annotated[str, Form()] = "",
    cnh_numero: Annotated[str, Form()] = "",
    cnh_categoria: Annotated[str, Form()] = "",
    cnh_validade: Annotated[str, Form()] = "",
    cnh_status: Annotated[str, Form()] = "regular",
    observacoes: Annotated[str, Form()] = "",
) -> HTMLResponse:
    ctx = {
        "item": None,
        "cnh_cats": await _cnh_cats(session, current_user.tenant_id),
        "title": "Novo Motorista",
        "action": "/cadastros/motoristas/novo",
    }
    try:
        await MotoristaService(session).create(
            current_user.tenant_id,
            MotoristaCreate(
                nome=nome,
                vinculo=MotoristaVinculo(vinculo),
                status=CadastroStatus(status),
                cpf=cpf or None,
                email=email or None,
                celular=celular or None,
                cnh_numero=cnh_numero or None,
                cnh_categoria=cnh_categoria or None,
                cnh_validade=_date(cnh_validade),
                cnh_status=MotoristaCnhStatus(cnh_status),
                observacoes=observacoes or None,
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = exc.message if isinstance(exc, AppError) else str(exc)
        return render(request, "cadastros/motorista_form.html", ctx, status_code=400)
    return RedirectResponse("/cadastros/motoristas", status_code=303)


@router.get("/cadastros/motoristas/{item_id}/editar", response_class=HTMLResponse)
async def motorista_edit(
    request: Request,
    session: SessionDep,
    item_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("cadastros.motorista.editar"))
    ],
) -> HTMLResponse:
    item = await MotoristaService(session).get(item_id)
    return render(
        request,
        "cadastros/motorista_form.html",
        {
            "item": item,
            "error": None,
            "cnh_cats": await _cnh_cats(session, current_user.tenant_id),
            "title": "Editar Motorista",
            "action": f"/cadastros/motoristas/{item_id}/editar",
        },
    )


@router.post("/cadastros/motoristas/{item_id}/editar", response_class=HTMLResponse)
async def motorista_update(
    request: Request,
    session: SessionDep,
    item_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("cadastros.motorista.editar"))
    ],
    nome: Annotated[str, Form()],
    vinculo: Annotated[str, Form()] = "terceiro",
    status: Annotated[str, Form()] = "active",
    email: Annotated[str, Form()] = "",
    celular: Annotated[str, Form()] = "",
    cnh_numero: Annotated[str, Form()] = "",
    cnh_categoria: Annotated[str, Form()] = "",
    cnh_validade: Annotated[str, Form()] = "",
    cnh_status: Annotated[str, Form()] = "regular",
    observacoes: Annotated[str, Form()] = "",
) -> HTMLResponse:
    try:
        await MotoristaService(session).update(
            item_id,
            MotoristaUpdate(
                nome=nome,
                vinculo=MotoristaVinculo(vinculo),
                status=CadastroStatus(status),
                email=email or None,
                celular=celular or None,
                cnh_numero=cnh_numero or None,
                cnh_categoria=cnh_categoria or None,
                cnh_validade=_date(cnh_validade),
                cnh_status=MotoristaCnhStatus(cnh_status),
                observacoes=observacoes or None,
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        item = await MotoristaService(session).get(item_id)
        return render(
            request,
            "cadastros/motorista_form.html",
            {
                "item": item,
                "error": exc.message if isinstance(exc, AppError) else str(exc),
                "cnh_cats": await _cnh_cats(session, current_user.tenant_id),
                "title": "Editar Motorista",
                "action": f"/cadastros/motoristas/{item_id}/editar",
            },
            status_code=400,
        )
    return RedirectResponse("/cadastros/motoristas", status_code=303)


# ============================================================== Parceiros
@router.get("/cadastros/parceiros", response_class=HTMLResponse)
async def parceiros_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("cadastros.parceiro.visualizar"))],
    page: int = 1,
    q: str = "",
) -> HTMLResponse:
    result = await ParceiroService(session).list_items(PageParams(page=page, size=25), search=q or None)
    return render(
        request, "cadastros/parceiros_list.html",
        {"page_result": result, "q": q, "title": "Parceiros"},
    )


@router.get("/cadastros/parceiros/novo", response_class=HTMLResponse)
async def parceiro_new(
    request: Request,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("cadastros.parceiro.criar"))],
) -> HTMLResponse:
    return render(
        request, "cadastros/parceiro_form.html",
        {"item": None, "error": None, "title": "Novo Parceiro", "action": "/cadastros/parceiros/novo"},
    )


@router.post("/cadastros/parceiros/novo", response_class=HTMLResponse)
async def parceiro_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("cadastros.parceiro.criar"))
    ],
    person_type: Annotated[str, Form()],
    nome: Annotated[str, Form()],
    tipo: Annotated[str, Form()] = "indicacao",
    status: Annotated[str, Form()] = "active",
    nome_fantasia: Annotated[str, Form()] = "",
    cpf: Annotated[str, Form()] = "",
    cnpj: Annotated[str, Form()] = "",
    email: Annotated[str, Form()] = "",
    telefone: Annotated[str, Form()] = "",
    comissao_percentual: Annotated[str, Form()] = "0",
    comissao_valor_fixo: Annotated[str, Form()] = "0",
    pix_chave: Annotated[str, Form()] = "",
    observacoes: Annotated[str, Form()] = "",
) -> HTMLResponse:
    try:
        await ParceiroService(session).create(
            current_user.tenant_id,
            ParceiroCreate(
                person_type=PersonType(person_type),
                tipo=ParceiroTipo(tipo),
                status=CadastroStatus(status),
                nome=nome,
                nome_fantasia=nome_fantasia or None,
                cpf=cpf or None,
                cnpj=cnpj or None,
                email=email or None,
                telefone=telefone or None,
                comissao_percentual=_dec(comissao_percentual),
                comissao_valor_fixo=_dec(comissao_valor_fixo),
                pix_chave=pix_chave or None,
                observacoes=observacoes or None,
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        return render(
            request,
            "cadastros/parceiro_form.html",
            {
                "item": None,
                "error": exc.message if isinstance(exc, AppError) else str(exc),
                "title": "Novo Parceiro",
                "action": "/cadastros/parceiros/novo",
            },
            status_code=400,
        )
    return RedirectResponse("/cadastros/parceiros", status_code=303)


@router.get("/cadastros/parceiros/{item_id}/editar", response_class=HTMLResponse)
async def parceiro_edit(
    request: Request,
    session: SessionDep,
    item_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("cadastros.parceiro.editar"))],
) -> HTMLResponse:
    item = await ParceiroService(session).get(item_id)
    return render(
        request, "cadastros/parceiro_form.html",
        {"item": item, "error": None, "title": "Editar Parceiro",
         "action": f"/cadastros/parceiros/{item_id}/editar"},
    )


@router.post("/cadastros/parceiros/{item_id}/editar", response_class=HTMLResponse)
async def parceiro_update(
    request: Request,
    session: SessionDep,
    item_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("cadastros.parceiro.editar"))],
    nome: Annotated[str, Form()],
    tipo: Annotated[str, Form()] = "indicacao",
    status: Annotated[str, Form()] = "active",
    nome_fantasia: Annotated[str, Form()] = "",
    email: Annotated[str, Form()] = "",
    telefone: Annotated[str, Form()] = "",
    comissao_percentual: Annotated[str, Form()] = "0",
    comissao_valor_fixo: Annotated[str, Form()] = "0",
    pix_chave: Annotated[str, Form()] = "",
    observacoes: Annotated[str, Form()] = "",
) -> HTMLResponse:
    try:
        await ParceiroService(session).update(
            item_id,
            ParceiroUpdate(
                nome=nome,
                tipo=ParceiroTipo(tipo),
                status=CadastroStatus(status),
                nome_fantasia=nome_fantasia or None,
                email=email or None,
                telefone=telefone or None,
                comissao_percentual=_dec(comissao_percentual),
                comissao_valor_fixo=_dec(comissao_valor_fixo),
                pix_chave=pix_chave or None,
                observacoes=observacoes or None,
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        item = await ParceiroService(session).get(item_id)
        return render(
            request, "cadastros/parceiro_form.html",
            {"item": item, "error": exc.message if isinstance(exc, AppError) else str(exc),
             "title": "Editar Parceiro", "action": f"/cadastros/parceiros/{item_id}/editar"},
            status_code=400,
        )
    return RedirectResponse("/cadastros/parceiros", status_code=303)


# ============================================================== Fornecedores
@router.get("/cadastros/fornecedores", response_class=HTMLResponse)
async def fornecedores_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("cadastros.fornecedor.visualizar"))
    ],
    page: int = 1,
    q: str = "",
) -> HTMLResponse:
    result = await FornecedorService(session).list_items(PageParams(page=page, size=25), search=q or None)
    return render(
        request, "cadastros/fornecedores_list.html",
        {"page_result": result, "q": q, "title": "Fornecedores"},
    )


@router.get("/cadastros/fornecedores/novo", response_class=HTMLResponse)
async def fornecedor_new(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("cadastros.fornecedor.criar"))
    ],
) -> HTMLResponse:
    return render(
        request, "cadastros/fornecedor_form.html",
        {
            "item": None, "error": None,
            "categorias": await _categorias_fornecedor(session, current_user.tenant_id),
            "title": "Novo Fornecedor", "action": "/cadastros/fornecedores/novo",
        },
    )


@router.post("/cadastros/fornecedores/novo", response_class=HTMLResponse)
async def fornecedor_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("cadastros.fornecedor.criar"))
    ],
    nome: Annotated[str, Form()],
    status: Annotated[str, Form()] = "active",
    nome_fantasia: Annotated[str, Form()] = "",
    cnpj: Annotated[str, Form()] = "",
    categoria_codigo: Annotated[str, Form()] = "",
    email: Annotated[str, Form()] = "",
    telefone: Annotated[str, Form()] = "",
    cidade: Annotated[str, Form()] = "",
    uf: Annotated[str, Form()] = "",
    prazo_pagamento_dias: Annotated[int, Form()] = 30,
    observacoes: Annotated[str, Form()] = "",
) -> HTMLResponse:
    cats = await _categorias_fornecedor(session, current_user.tenant_id)
    try:
        await FornecedorService(session).create(
            current_user.tenant_id,
            FornecedorCreate(
                nome=nome,
                status=CadastroStatus(status),
                nome_fantasia=nome_fantasia or None,
                cnpj=cnpj or None,
                categoria_codigo=categoria_codigo or None,
                email=email or None,
                telefone=telefone or None,
                cidade=cidade or None,
                uf=uf or None,
                prazo_pagamento_dias=prazo_pagamento_dias,
                observacoes=observacoes or None,
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        return render(
            request, "cadastros/fornecedor_form.html",
            {"item": None, "error": exc.message if isinstance(exc, AppError) else str(exc),
             "categorias": cats, "title": "Novo Fornecedor",
             "action": "/cadastros/fornecedores/novo"},
            status_code=400,
        )
    return RedirectResponse("/cadastros/fornecedores", status_code=303)


@router.get("/cadastros/fornecedores/{item_id}/editar", response_class=HTMLResponse)
async def fornecedor_edit(
    request: Request,
    session: SessionDep,
    item_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("cadastros.fornecedor.editar"))
    ],
) -> HTMLResponse:
    item = await FornecedorService(session).get(item_id)
    return render(
        request, "cadastros/fornecedor_form.html",
        {
            "item": item, "error": None,
            "categorias": await _categorias_fornecedor(session, current_user.tenant_id),
            "title": "Editar Fornecedor",
            "action": f"/cadastros/fornecedores/{item_id}/editar",
        },
    )


@router.post("/cadastros/fornecedores/{item_id}/editar", response_class=HTMLResponse)
async def fornecedor_update(
    request: Request,
    session: SessionDep,
    item_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("cadastros.fornecedor.editar"))
    ],
    nome: Annotated[str, Form()],
    status: Annotated[str, Form()] = "active",
    nome_fantasia: Annotated[str, Form()] = "",
    categoria_codigo: Annotated[str, Form()] = "",
    email: Annotated[str, Form()] = "",
    telefone: Annotated[str, Form()] = "",
    cidade: Annotated[str, Form()] = "",
    uf: Annotated[str, Form()] = "",
    prazo_pagamento_dias: Annotated[int, Form()] = 30,
    bloqueado: Annotated[str, Form()] = "",
    motivo_bloqueio: Annotated[str, Form()] = "",
    observacoes: Annotated[str, Form()] = "",
) -> HTMLResponse:
    try:
        await FornecedorService(session).update(
            item_id,
            FornecedorUpdate(
                nome=nome,
                status=CadastroStatus(status),
                nome_fantasia=nome_fantasia or None,
                categoria_codigo=categoria_codigo or None,
                email=email or None,
                telefone=telefone or None,
                cidade=cidade or None,
                uf=uf or None,
                prazo_pagamento_dias=prazo_pagamento_dias,
                bloqueado=bool(bloqueado),
                motivo_bloqueio=motivo_bloqueio or None,
                observacoes=observacoes or None,
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        item = await FornecedorService(session).get(item_id)
        return render(
            request, "cadastros/fornecedor_form.html",
            {
                "item": item,
                "error": exc.message if isinstance(exc, AppError) else str(exc),
                "categorias": await _categorias_fornecedor(session, current_user.tenant_id),
                "title": "Editar Fornecedor",
                "action": f"/cadastros/fornecedores/{item_id}/editar",
            },
            status_code=400,
        )
    return RedirectResponse("/cadastros/fornecedores", status_code=303)


# ============================================================== Vendedores
@router.get("/cadastros/vendedores", response_class=HTMLResponse)
async def vendedores_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("cadastros.vendedor.visualizar"))],
    page: int = 1,
    q: str = "",
) -> HTMLResponse:
    result = await VendedorService(session).list_items(PageParams(page=page, size=25), search=q or None)
    return render(
        request, "cadastros/vendedores_list.html",
        {"page_result": result, "q": q, "title": "Vendedores"},
    )


@router.get("/cadastros/vendedores/novo", response_class=HTMLResponse)
async def vendedor_new(
    request: Request,
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("cadastros.vendedor.criar"))],
) -> HTMLResponse:
    filiais = await FilialService(session).list_filiais(PageParams(page=1, size=100))
    return render(
        request, "cadastros/vendedor_form.html",
        {
            "item": None, "error": None, "filiais": filiais.items,
            "title": "Novo Vendedor", "action": "/cadastros/vendedores/novo",
        },
    )


@router.post("/cadastros/vendedores/novo", response_class=HTMLResponse)
async def vendedor_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("cadastros.vendedor.criar"))
    ],
    nome: Annotated[str, Form()],
    status: Annotated[str, Form()] = "active",
    email: Annotated[str, Form()] = "",
    telefone: Annotated[str, Form()] = "",
    filial_id: Annotated[str, Form()] = "",
    meta_contratos_mes: Annotated[int, Form()] = 0,
    meta_faturamento_mes: Annotated[str, Form()] = "0",
    comissao_percentual: Annotated[str, Form()] = "0",
    observacoes: Annotated[str, Form()] = "",
) -> HTMLResponse:
    filiais = await FilialService(session).list_filiais(PageParams(page=1, size=100))
    try:
        await VendedorService(session).create(
            current_user.tenant_id,
            VendedorCreate(
                nome=nome,
                status=CadastroStatus(status),
                email=email or None,
                telefone=telefone or None,
                filial_id=uuid.UUID(filial_id) if filial_id else None,
                meta_contratos_mes=meta_contratos_mes,
                meta_faturamento_mes=_dec(meta_faturamento_mes),
                comissao_percentual=_dec(comissao_percentual),
                observacoes=observacoes or None,
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        return render(
            request, "cadastros/vendedor_form.html",
            {
                "item": None,
                "error": exc.message if isinstance(exc, AppError) else str(exc),
                "filiais": filiais.items,
                "title": "Novo Vendedor",
                "action": "/cadastros/vendedores/novo",
            },
            status_code=400,
        )
    return RedirectResponse("/cadastros/vendedores", status_code=303)


@router.get("/cadastros/vendedores/{item_id}/editar", response_class=HTMLResponse)
async def vendedor_edit(
    request: Request,
    session: SessionDep,
    item_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("cadastros.vendedor.editar"))],
) -> HTMLResponse:
    item = await VendedorService(session).get(item_id)
    filiais = await FilialService(session).list_filiais(PageParams(page=1, size=100))
    return render(
        request, "cadastros/vendedor_form.html",
        {
            "item": item, "error": None, "filiais": filiais.items,
            "title": "Editar Vendedor",
            "action": f"/cadastros/vendedores/{item_id}/editar",
        },
    )


@router.post("/cadastros/vendedores/{item_id}/editar", response_class=HTMLResponse)
async def vendedor_update(
    request: Request,
    session: SessionDep,
    item_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("cadastros.vendedor.editar"))],
    nome: Annotated[str, Form()],
    status: Annotated[str, Form()] = "active",
    email: Annotated[str, Form()] = "",
    telefone: Annotated[str, Form()] = "",
    filial_id: Annotated[str, Form()] = "",
    meta_contratos_mes: Annotated[int, Form()] = 0,
    meta_faturamento_mes: Annotated[str, Form()] = "0",
    comissao_percentual: Annotated[str, Form()] = "0",
    observacoes: Annotated[str, Form()] = "",
) -> HTMLResponse:
    try:
        await VendedorService(session).update(
            item_id,
            VendedorUpdate(
                nome=nome,
                status=CadastroStatus(status),
                email=email or None,
                telefone=telefone or None,
                filial_id=uuid.UUID(filial_id) if filial_id else None,
                meta_contratos_mes=meta_contratos_mes,
                meta_faturamento_mes=_dec(meta_faturamento_mes),
                comissao_percentual=_dec(comissao_percentual),
                observacoes=observacoes or None,
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        item = await VendedorService(session).get(item_id)
        filiais = await FilialService(session).list_filiais(PageParams(page=1, size=100))
        return render(
            request, "cadastros/vendedor_form.html",
            {
                "item": item,
                "error": exc.message if isinstance(exc, AppError) else str(exc),
                "filiais": filiais.items,
                "title": "Editar Vendedor",
                "action": f"/cadastros/vendedores/{item_id}/editar",
            },
            status_code=400,
        )
    return RedirectResponse("/cadastros/vendedores", status_code=303)
