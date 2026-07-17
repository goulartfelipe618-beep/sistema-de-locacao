"""Rotas Web (HTML/Jinja2) do módulo Frota."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_web_permission
from app.core.exceptions import AppError
from app.core.pagination import PageParams
from app.core.templating import render
from app.modules.frota.schemas import (
    AcessorioCreate,
    AcessorioUpdate,
    CategoriaCreate,
    CategoriaUpdate,
    CombustivelCreate,
    CombustivelUpdate,
    DocumentoCreate,
    DocumentoUpdate,
    MarcaCreate,
    MarcaUpdate,
    ModeloCreate,
    ModeloUpdate,
    TelemetriaDispositivoUpsert,
    TelemetriaEventoCreate,
    VeiculoAcessorioLink,
    VeiculoCreate,
    VeiculoFotoCreate,
    VeiculoUpdate,
)
from app.modules.frota.service import (
    AcessoriosService,
    CategoriasService,
    CombustiveisService,
    DocumentoService,
    FotoService,
    MarcasService,
    ModelosService,
    TelemetriaService,
    VeiculoService,
)
from app.modules.identity.service import AuthenticatedUser
from app.modules.tenants.service import FilialService
from app.shared.enums import (
    AcessorioTipo,
    CadastroStatus,
    CombustivelUnidade,
    DocumentoVeiculoStatus,
    DocumentoVeiculoTipo,
    TelemetriaConnStatus,
    TelemetriaEventoTipo,
    VeiculoPropriedade,
    VeiculoStatus,
)

router = APIRouter()
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/frota/modelos/json")
async def modelos_json(
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("frota.veiculo.visualizar"))],
    marca_id: str = "",
) -> JSONResponse:
    """Lista modelos filtrados por marca (cascata no formulário de veículo)."""
    mid: uuid.UUID | None = None
    if marca_id.strip():
        try:
            mid = uuid.UUID(marca_id.strip())
        except ValueError:
            return JSONResponse(content=[])
    page = await ModelosService(session).list_items(
        PageParams(page=1, size=500), marca_id=mid
    )
    return JSONResponse(content=[{"id": str(m.id), "nome": m.nome} for m in page.items])


@router.get("/frota/veiculos/json")
async def veiculos_json(
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("frota.veiculo.visualizar"))],
    q: str = "",
    page: int = 1,
    categoria_id: str = "",
) -> JSONResponse:
    """Busca async de veículos (placa/chassi) para combobox."""
    cid: uuid.UUID | None = None
    if categoria_id.strip():
        try:
            cid = uuid.UUID(categoria_id.strip())
        except ValueError:
            pass
    page_result = await VeiculoService(session).list_items(
        PageParams(page=page, size=25),
        search=q or None,
        categoria_id=cid,
    )
    items = [
        {"id": str(v.id), "label": v.placa + (f" — {v.cor}" if v.cor else ""), "placa": v.placa}
        for v in page_result.items
    ]
    return JSONResponse(content={"items": items, "total": page_result.total, "page": page})


@router.get("/frota/veiculos/{veiculo_id}/impacto")
async def veiculo_impacto_web(
    veiculo_id: uuid.UUID,
    session: SessionDep,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("frota.veiculo.visualizar"))],
) -> JSONResponse:
    from app.shared.entity_impact import veiculo_impact

    return JSONResponse(content=await veiculo_impact(session, veiculo_id))


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


async def _ensure_frota_defaults(session: AsyncSession, tenant_id: uuid.UUID) -> None:
    await CategoriasService(session).ensure_defaults(tenant_id)
    await MarcasService(session).ensure_defaults(tenant_id)
    await CombustiveisService(session).ensure_defaults(tenant_id)


async def _veiculo_lookups(session: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Any]:
    await _ensure_frota_defaults(session, tenant_id)
    cats = await CategoriasService(session).list_items(PageParams(page=1, size=200))
    marcas = await MarcasService(session).list_items(PageParams(page=1, size=200))
    combustiveis = await CombustiveisService(session).list_items(PageParams(page=1, size=100))
    modelos = await ModelosService(session).list_items(PageParams(page=1, size=500))
    filiais = await FilialService(session).list_filiais(PageParams(page=1, size=100))
    return {
        "categorias": cats.items,
        "marcas": marcas.items,
        "combustiveis": combustiveis.items,
        "modelos": modelos.items,
        "filiais": filiais.items,
    }


def _app_error_message(exc: AppError | ValueError) -> str:
    return exc.message if isinstance(exc, AppError) else str(exc)


# ================================================================ Veículos
@router.get("/frota/veiculos", response_class=HTMLResponse)
async def veiculos_list(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.veiculo.visualizar"))
    ],
    page: int = 1,
    q: str = "",
    status: str = "",
) -> HTMLResponse:
    await _ensure_frota_defaults(session, current_user.tenant_id)
    st = VeiculoStatus(status) if status else None
    result = await VeiculoService(session).list_items(
        PageParams(page=page, size=25), search=q or None, status=st
    )
    return render(
        request,
        "frota/veiculos_list.html",
        {
            "page_result": result,
            "q": q,
            "status": status,
            "title": "Veículos",
        },
    )


@router.get("/frota/veiculos/novo", response_class=HTMLResponse)
async def veiculo_new_form(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.veiculo.criar"))
    ],
) -> HTMLResponse:
    lookups = await _veiculo_lookups(session, current_user.tenant_id)
    return render(
        request,
        "frota/veiculo_form.html",
        {
            "veiculo": None,
            "error": None,
            "title": "Novo Veículo",
            "action": "/frota/veiculos/novo",
            **lookups,
        },
    )


@router.post("/frota/veiculos/novo", response_class=HTMLResponse)
async def veiculo_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.veiculo.criar"))
    ],
    placa: Annotated[str, Form()],
    ano_fabricacao: Annotated[int, Form()],
    ano_modelo: Annotated[int, Form()],
    categoria_id: Annotated[str, Form()],
    marca_id: Annotated[str, Form()],
    modelo_id: Annotated[str, Form()],
    combustivel_id: Annotated[str, Form()],
    renavam: Annotated[str, Form()] = "",
    chassi: Annotated[str, Form()] = "",
    cor: Annotated[str, Form()] = "",
    filial_id: Annotated[str, Form()] = "",
    propriedade: Annotated[str, Form()] = "propria",
    data_compra: Annotated[str, Form()] = "",
    valor_aquisicao: Annotated[str, Form()] = "",
    valor_fipe: Annotated[str, Form()] = "",
    valor_mercado: Annotated[str, Form()] = "",
    proprietario_nome: Annotated[str, Form()] = "",
    km_inicial: Annotated[str, Form()] = "",
    km_atual: Annotated[str, Form()] = "",
    nivel_combustivel_atual: Annotated[int, Form()] = 8,
    observacoes: Annotated[str, Form()] = "",
) -> HTMLResponse:
    lookups = await _veiculo_lookups(session, current_user.tenant_id)
    ctx = {
        "veiculo": None,
        "error": None,
        "title": "Novo Veículo",
        "action": "/frota/veiculos/novo",
        **lookups,
    }
    try:
        data = VeiculoCreate(
            placa=placa,
            renavam=renavam or None,
            chassi=chassi or None,
            ano_fabricacao=ano_fabricacao,
            ano_modelo=ano_modelo,
            cor=cor or None,
            categoria_id=uuid.UUID(categoria_id),
            marca_id=uuid.UUID(marca_id),
            modelo_id=uuid.UUID(modelo_id),
            combustivel_id=uuid.UUID(combustivel_id),
            filial_id=_uuid(filial_id),
            propriedade=VeiculoPropriedade(propriedade),
            data_compra=_date(data_compra),
            valor_aquisicao=_dec(valor_aquisicao) if valor_aquisicao.strip() else None,
            valor_fipe=_dec(valor_fipe) if valor_fipe.strip() else None,
            valor_mercado=_dec(valor_mercado) if valor_mercado.strip() else None,
            proprietario_nome=proprietario_nome or None,
            km_inicial=int(km_inicial) if km_inicial.strip() else None,
            km_atual=int(km_atual) if km_atual.strip() else None,
            nivel_combustivel_atual=nivel_combustivel_atual,
            observacoes=observacoes or None,
        )
        await VeiculoService(session).create(current_user.tenant_id, data)
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _app_error_message(exc)
        return render(request, "frota/veiculo_form.html", ctx, status_code=400)
    return RedirectResponse("/frota/veiculos", status_code=303)


async def _veiculo_extras(session: AsyncSession, veiculo_id: uuid.UUID) -> dict[str, Any]:
    svc = VeiculoService(session)
    vinculos = await svc.list_acessorios(PageParams(page=1, size=100), veiculo_id)
    catalogo = await AcessoriosService(session).list_items(PageParams(page=1, size=200))
    fotos = await FotoService(session).list_by_veiculo(PageParams(page=1, size=100), veiculo_id)
    nomes = {str(a.id): a.nome for a in catalogo.items}
    return {
        "vinculos": vinculos,
        "catalogo_acessorios": catalogo.items,
        "fotos": fotos,
        "acessorio_nomes": nomes,
    }


@router.get("/frota/veiculos/{veiculo_id}/editar", response_class=HTMLResponse)
async def veiculo_edit_form(
    request: Request,
    session: SessionDep,
    veiculo_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.veiculo.editar"))
    ],
) -> HTMLResponse:
    veiculo = await VeiculoService(session).get(veiculo_id)
    lookups = await _veiculo_lookups(session, current_user.tenant_id)
    extras = await _veiculo_extras(session, veiculo_id)
    return render(
        request,
        "frota/veiculo_form.html",
        {
            "veiculo": veiculo,
            "error": None,
            "title": "Editar Veículo",
            "action": f"/frota/veiculos/{veiculo_id}/editar",
            **lookups,
            **extras,
        },
    )


@router.post("/frota/veiculos/{veiculo_id}/editar", response_class=HTMLResponse)
async def veiculo_update(
    request: Request,
    session: SessionDep,
    veiculo_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.veiculo.editar"))
    ],
    placa: Annotated[str, Form()],
    ano_fabricacao: Annotated[int, Form()],
    ano_modelo: Annotated[int, Form()],
    categoria_id: Annotated[str, Form()],
    marca_id: Annotated[str, Form()],
    modelo_id: Annotated[str, Form()],
    combustivel_id: Annotated[str, Form()],
    renavam: Annotated[str, Form()] = "",
    chassi: Annotated[str, Form()] = "",
    cor: Annotated[str, Form()] = "",
    filial_id: Annotated[str, Form()] = "",
    propriedade: Annotated[str, Form()] = "propria",
    data_compra: Annotated[str, Form()] = "",
    valor_aquisicao: Annotated[str, Form()] = "",
    valor_fipe: Annotated[str, Form()] = "",
    valor_mercado: Annotated[str, Form()] = "",
    proprietario_nome: Annotated[str, Form()] = "",
    km_inicial: Annotated[str, Form()] = "",
    km_atual: Annotated[str, Form()] = "",
    nivel_combustivel_atual: Annotated[int, Form()] = 8,
    observacoes: Annotated[str, Form()] = "",
) -> HTMLResponse:
    lookups = await _veiculo_lookups(session, current_user.tenant_id)
    extras = await _veiculo_extras(session, veiculo_id)
    try:
        data = VeiculoUpdate(
            placa=placa,
            renavam=renavam or None,
            chassi=chassi or None,
            ano_fabricacao=ano_fabricacao,
            ano_modelo=ano_modelo,
            cor=cor or None,
            categoria_id=uuid.UUID(categoria_id),
            marca_id=uuid.UUID(marca_id),
            modelo_id=uuid.UUID(modelo_id),
            combustivel_id=uuid.UUID(combustivel_id),
            filial_id=_uuid(filial_id),
            propriedade=VeiculoPropriedade(propriedade),
            data_compra=_date(data_compra),
            valor_aquisicao=_dec(valor_aquisicao) if valor_aquisicao.strip() else None,
            valor_fipe=_dec(valor_fipe) if valor_fipe.strip() else None,
            valor_mercado=_dec(valor_mercado) if valor_mercado.strip() else None,
            proprietario_nome=proprietario_nome or None,
            km_inicial=int(km_inicial) if km_inicial.strip() else None,
            km_atual=int(km_atual) if km_atual.strip() else None,
            nivel_combustivel_atual=nivel_combustivel_atual,
            observacoes=observacoes or None,
        )
        await VeiculoService(session).update(veiculo_id, data)
    except (AppError, ValueError) as exc:
        await session.rollback()
        veiculo = await VeiculoService(session).get(veiculo_id)
        return render(
            request,
            "frota/veiculo_form.html",
            {
                "veiculo": veiculo,
                "error": _app_error_message(exc),
                "title": "Editar Veículo",
                "action": f"/frota/veiculos/{veiculo_id}/editar",
                **lookups,
                **extras,
            },
            status_code=400,
        )
    return RedirectResponse(f"/frota/veiculos/{veiculo_id}/editar", status_code=303)


@router.post("/frota/veiculos/{veiculo_id}/acessorios", response_class=HTMLResponse)
async def veiculo_link_acessorio(
    session: SessionDep,
    veiculo_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.veiculo.editar"))
    ],
    acessorio_id: Annotated[str, Form()],
    data_instalacao: Annotated[str, Form()] = "",
) -> RedirectResponse:
    await VeiculoService(session).link_acessorio(
        current_user.tenant_id,
        veiculo_id,
        VeiculoAcessorioLink(
            acessorio_id=uuid.UUID(acessorio_id),
            data_instalacao=_date(data_instalacao),
        ),
    )
    return RedirectResponse(f"/frota/veiculos/{veiculo_id}/editar", status_code=303)


@router.post(
    "/frota/veiculos/{veiculo_id}/acessorios/{acessorio_id}/remover",
    response_class=HTMLResponse,
)
async def veiculo_unlink_acessorio(
    session: SessionDep,
    veiculo_id: uuid.UUID,
    acessorio_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("frota.veiculo.editar"))],
) -> RedirectResponse:
    await VeiculoService(session).unlink_acessorio(veiculo_id, acessorio_id)
    return RedirectResponse(f"/frota/veiculos/{veiculo_id}/editar", status_code=303)


@router.post("/frota/veiculos/{veiculo_id}/fotos", response_class=HTMLResponse)
async def veiculo_add_foto(
    session: SessionDep,
    veiculo_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.veiculo.editar"))
    ],
    storage_key: Annotated[str, Form()],
    legenda: Annotated[str, Form()] = "",
    tirada_em: Annotated[str, Form()] = "",
) -> RedirectResponse:
    await FotoService(session).add(
        current_user.tenant_id,
        veiculo_id,
        VeiculoFotoCreate(
            storage_key=storage_key,
            legenda=legenda or None,
            tirada_em=_date(tirada_em),
        ),
    )
    return RedirectResponse(f"/frota/veiculos/{veiculo_id}/editar", status_code=303)


@router.post(
    "/frota/veiculos/{veiculo_id}/fotos/{foto_id}/remover",
    response_class=HTMLResponse,
)
async def veiculo_remove_foto(
    session: SessionDep,
    veiculo_id: uuid.UUID,
    foto_id: uuid.UUID,
    _user: Annotated[AuthenticatedUser, Depends(require_web_permission("frota.veiculo.editar"))],
) -> RedirectResponse:
    await FotoService(session).remove(foto_id)
    return RedirectResponse(f"/frota/veiculos/{veiculo_id}/editar", status_code=303)


@router.post("/frota/veiculos/{veiculo_id}/bloquear", response_class=HTMLResponse)
async def veiculo_bloquear(
    session: SessionDep,
    veiculo_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.veiculo.bloquear"))
    ],
    motivo: Annotated[str, Form()],
) -> RedirectResponse:
    await VeiculoService(session).bloquear(veiculo_id, motivo)
    return RedirectResponse(f"/frota/veiculos/{veiculo_id}/editar", status_code=303)


@router.post("/frota/veiculos/{veiculo_id}/baixar", response_class=HTMLResponse)
async def veiculo_baixar(
    session: SessionDep,
    veiculo_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.veiculo.baixar"))
    ],
    motivo: Annotated[str, Form()],
    destinatario_nome: Annotated[str, Form()] = "",
    destinatario_doc: Annotated[str, Form()] = "",
    valor_venda: Annotated[str, Form()] = "",
) -> RedirectResponse:
    veiculo = await VeiculoService(session).baixar(veiculo_id, motivo)
    # Hook §10.2: se for venda com dados do comprador, gera NF-e (rascunho a_emitir).
    if "venda" in (motivo or "").lower() and destinatario_nome.strip() and veiculo.filial_id:
        try:
            valor = Decimal((valor_venda or "0").replace(".", "").replace(",", "."))
        except InvalidOperation:
            valor = veiculo.valor_mercado or veiculo.valor_fipe or Decimal("0")
        if valor <= 0:
            valor = veiculo.valor_mercado or veiculo.valor_fipe or Decimal("0")
        try:
            from app.modules.fiscal.service import NfeService

            await NfeService(session).create_from_veiculo_baixar(
                current_user.tenant_id,
                veiculo_id=veiculo.id,
                filial_id=veiculo.filial_id,
                destinatario_nome=destinatario_nome.strip(),
                destinatario_doc=destinatario_doc.strip() or None,
                valor=valor,
                descricao=f"Venda do veículo {veiculo.placa}",
            )
        except Exception:  # noqa: BLE001 - NF-e não deve bloquear a baixa
            pass
    return RedirectResponse(f"/frota/veiculos/{veiculo_id}/editar", status_code=303)


@router.post("/frota/veiculos/{veiculo_id}/liberar", response_class=HTMLResponse)
async def veiculo_liberar(
    session: SessionDep,
    veiculo_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.veiculo.bloquear"))
    ],
    motivo: Annotated[str, Form()] = "",
) -> RedirectResponse:
    await VeiculoService(session).liberar(veiculo_id, motivo or None)
    return RedirectResponse(f"/frota/veiculos/{veiculo_id}/editar", status_code=303)


# ============================================================== Categorias
@router.get("/frota/categorias", response_class=HTMLResponse)
async def categorias_list(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.categoria.visualizar"))
    ],
    page: int = 1,
    q: str = "",
) -> HTMLResponse:
    await _ensure_frota_defaults(session, current_user.tenant_id)
    result = await CategoriasService(session).list_items(
        PageParams(page=page, size=25), search=q or None
    )
    return render(
        request,
        "frota/categorias_list.html",
        {"page_result": result, "q": q, "title": "Categorias"},
    )


@router.get("/frota/categorias/novo", response_class=HTMLResponse)
async def categoria_new_form(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.categoria.criar"))
    ],
) -> HTMLResponse:
    await _ensure_frota_defaults(session, current_user.tenant_id)
    return render(
        request,
        "frota/categoria_form.html",
        {"item": None, "error": None, "title": "Nova Categoria", "action": "/frota/categorias/novo"},
    )


@router.post("/frota/categorias/novo", response_class=HTMLResponse)
async def categoria_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.categoria.criar"))
    ],
    nome: Annotated[str, Form()],
    descricao: Annotated[str, Form()] = "",
    capacidade_passageiros: Annotated[int, Form()] = 5,
    capacidade_porta_malas: Annotated[str, Form()] = "",
    transmissao_tipica: Annotated[str, Form()] = "",
    imagem_url: Annotated[str, Form()] = "",
    ordem: Annotated[int, Form()] = 0,
    grupo_tarifario: Annotated[str, Form()] = "",
    status: Annotated[str, Form()] = "active",
) -> HTMLResponse:
    ctx = {"item": None, "error": None, "title": "Nova Categoria", "action": "/frota/categorias/novo"}
    try:
        await CategoriasService(session).create(
            current_user.tenant_id,
            CategoriaCreate(
                nome=nome,
                descricao=descricao or None,
                capacidade_passageiros=capacidade_passageiros,
                capacidade_porta_malas=capacidade_porta_malas or None,
                transmissao_tipica=transmissao_tipica or None,
                imagem_url=imagem_url or None,
                ordem=ordem,
                grupo_tarifario=grupo_tarifario or None,
                status=CadastroStatus(status),
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _app_error_message(exc)
        return render(request, "frota/categoria_form.html", ctx, status_code=400)
    return RedirectResponse("/frota/categorias", status_code=303)


@router.get("/frota/categorias/{item_id}/editar", response_class=HTMLResponse)
async def categoria_edit_form(
    request: Request,
    session: SessionDep,
    item_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.categoria.editar"))
    ],
) -> HTMLResponse:
    await _ensure_frota_defaults(session, current_user.tenant_id)
    item = await CategoriasService(session).get(item_id)
    return render(
        request,
        "frota/categoria_form.html",
        {
            "item": item,
            "error": None,
            "title": "Editar Categoria",
            "action": f"/frota/categorias/{item_id}/editar",
        },
    )


@router.post("/frota/categorias/{item_id}/editar", response_class=HTMLResponse)
async def categoria_update(
    request: Request,
    session: SessionDep,
    item_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.categoria.editar"))
    ],
    nome: Annotated[str, Form()],
    descricao: Annotated[str, Form()] = "",
    capacidade_passageiros: Annotated[int, Form()] = 5,
    capacidade_porta_malas: Annotated[str, Form()] = "",
    transmissao_tipica: Annotated[str, Form()] = "",
    imagem_url: Annotated[str, Form()] = "",
    ordem: Annotated[int, Form()] = 0,
    grupo_tarifario: Annotated[str, Form()] = "",
    status: Annotated[str, Form()] = "active",
) -> HTMLResponse:
    try:
        await CategoriasService(session).update(
            item_id,
            CategoriaUpdate(
                nome=nome,
                descricao=descricao or None,
                capacidade_passageiros=capacidade_passageiros,
                capacidade_porta_malas=capacidade_porta_malas or None,
                transmissao_tipica=transmissao_tipica or None,
                imagem_url=imagem_url or None,
                ordem=ordem,
                grupo_tarifario=grupo_tarifario or None,
                status=CadastroStatus(status),
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        item = await CategoriasService(session).get(item_id)
        return render(
            request,
            "frota/categoria_form.html",
            {
                "item": item,
                "error": _app_error_message(exc),
                "title": "Editar Categoria",
                "action": f"/frota/categorias/{item_id}/editar",
            },
            status_code=400,
        )
    return RedirectResponse("/frota/categorias", status_code=303)


# ================================================================== Marcas
@router.get("/frota/marcas", response_class=HTMLResponse)
async def marcas_list(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.marca.visualizar"))
    ],
    page: int = 1,
    q: str = "",
) -> HTMLResponse:
    await _ensure_frota_defaults(session, current_user.tenant_id)
    result = await MarcasService(session).list_items(PageParams(page=page, size=25), search=q or None)
    return render(
        request,
        "frota/marcas_list.html",
        {"page_result": result, "q": q, "title": "Marcas"},
    )


@router.get("/frota/marcas/novo", response_class=HTMLResponse)
async def marca_new_form(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.marca.criar"))
    ],
) -> HTMLResponse:
    await _ensure_frota_defaults(session, current_user.tenant_id)
    return render(
        request,
        "frota/marca_form.html",
        {"item": None, "error": None, "title": "Nova Marca", "action": "/frota/marcas/novo"},
    )


@router.post("/frota/marcas/novo", response_class=HTMLResponse)
async def marca_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.marca.criar"))
    ],
    nome: Annotated[str, Form()],
    logo_url: Annotated[str, Form()] = "",
    pais_origem: Annotated[str, Form()] = "",
    status: Annotated[str, Form()] = "active",
) -> HTMLResponse:
    ctx = {"item": None, "error": None, "title": "Nova Marca", "action": "/frota/marcas/novo"}
    try:
        await MarcasService(session).create(
            current_user.tenant_id,
            MarcaCreate(
                nome=nome,
                logo_url=logo_url or None,
                pais_origem=pais_origem or None,
                status=CadastroStatus(status),
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _app_error_message(exc)
        return render(request, "frota/marca_form.html", ctx, status_code=400)
    return RedirectResponse("/frota/marcas", status_code=303)


@router.get("/frota/marcas/{item_id}/editar", response_class=HTMLResponse)
async def marca_edit_form(
    request: Request,
    session: SessionDep,
    item_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.marca.editar"))
    ],
) -> HTMLResponse:
    await _ensure_frota_defaults(session, current_user.tenant_id)
    item = await MarcasService(session).get(item_id)
    return render(
        request,
        "frota/marca_form.html",
        {
            "item": item,
            "error": None,
            "title": "Editar Marca",
            "action": f"/frota/marcas/{item_id}/editar",
        },
    )


@router.post("/frota/marcas/{item_id}/editar", response_class=HTMLResponse)
async def marca_update(
    request: Request,
    session: SessionDep,
    item_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.marca.editar"))
    ],
    nome: Annotated[str, Form()],
    logo_url: Annotated[str, Form()] = "",
    pais_origem: Annotated[str, Form()] = "",
    status: Annotated[str, Form()] = "active",
) -> HTMLResponse:
    try:
        await MarcasService(session).update(
            item_id,
            MarcaUpdate(
                nome=nome,
                logo_url=logo_url or None,
                pais_origem=pais_origem or None,
                status=CadastroStatus(status),
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        item = await MarcasService(session).get(item_id)
        return render(
            request,
            "frota/marca_form.html",
            {
                "item": item,
                "error": _app_error_message(exc),
                "title": "Editar Marca",
                "action": f"/frota/marcas/{item_id}/editar",
            },
            status_code=400,
        )
    return RedirectResponse("/frota/marcas", status_code=303)


# ============================================================== Combustíveis
@router.get("/frota/combustiveis", response_class=HTMLResponse)
async def combustiveis_list(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.combustivel.visualizar"))
    ],
    page: int = 1,
    q: str = "",
) -> HTMLResponse:
    await _ensure_frota_defaults(session, current_user.tenant_id)
    result = await CombustiveisService(session).list_items(
        PageParams(page=page, size=25), search=q or None
    )
    return render(
        request,
        "frota/combustiveis_list.html",
        {"page_result": result, "q": q, "title": "Combustíveis"},
    )


@router.get("/frota/combustiveis/novo", response_class=HTMLResponse)
async def combustivel_new_form(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.combustivel.criar"))
    ],
) -> HTMLResponse:
    await _ensure_frota_defaults(session, current_user.tenant_id)
    return render(
        request,
        "frota/combustivel_form.html",
        {"item": None, "error": None, "title": "Novo Combustível", "action": "/frota/combustiveis/novo"},
    )


@router.post("/frota/combustiveis/novo", response_class=HTMLResponse)
async def combustivel_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.combustivel.criar"))
    ],
    nome: Annotated[str, Form()],
    unidade: Annotated[str, Form()] = "litro",
    preco_referencia: Annotated[str, Form()] = "0",
    status: Annotated[str, Form()] = "active",
) -> HTMLResponse:
    ctx = {
        "item": None,
        "error": None,
        "title": "Novo Combustível",
        "action": "/frota/combustiveis/novo",
    }
    try:
        await CombustiveisService(session).create(
            current_user.tenant_id,
            CombustivelCreate(
                nome=nome,
                unidade=CombustivelUnidade(unidade),
                preco_referencia=_dec(preco_referencia),
                status=CadastroStatus(status),
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _app_error_message(exc)
        return render(request, "frota/combustivel_form.html", ctx, status_code=400)
    return RedirectResponse("/frota/combustiveis", status_code=303)


@router.get("/frota/combustiveis/{item_id}/editar", response_class=HTMLResponse)
async def combustivel_edit_form(
    request: Request,
    session: SessionDep,
    item_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.combustivel.editar"))
    ],
) -> HTMLResponse:
    await _ensure_frota_defaults(session, current_user.tenant_id)
    item = await CombustiveisService(session).get(item_id)
    return render(
        request,
        "frota/combustivel_form.html",
        {
            "item": item,
            "error": None,
            "title": "Editar Combustível",
            "action": f"/frota/combustiveis/{item_id}/editar",
        },
    )


@router.post("/frota/combustiveis/{item_id}/editar", response_class=HTMLResponse)
async def combustivel_update(
    request: Request,
    session: SessionDep,
    item_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.combustivel.editar"))
    ],
    nome: Annotated[str, Form()],
    unidade: Annotated[str, Form()] = "litro",
    preco_referencia: Annotated[str, Form()] = "0",
    status: Annotated[str, Form()] = "active",
) -> HTMLResponse:
    try:
        await CombustiveisService(session).update(
            item_id,
            CombustivelUpdate(
                nome=nome,
                unidade=CombustivelUnidade(unidade),
                preco_referencia=_dec(preco_referencia),
                status=CadastroStatus(status),
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        item = await CombustiveisService(session).get(item_id)
        return render(
            request,
            "frota/combustivel_form.html",
            {
                "item": item,
                "error": _app_error_message(exc),
                "title": "Editar Combustível",
                "action": f"/frota/combustiveis/{item_id}/editar",
            },
            status_code=400,
        )
    return RedirectResponse("/frota/combustiveis", status_code=303)


# ================================================================== Modelos
@router.get("/frota/modelos", response_class=HTMLResponse)
async def modelos_list(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.modelo.visualizar"))
    ],
    page: int = 1,
    q: str = "",
    marca_id: str = "",
) -> HTMLResponse:
    await _ensure_frota_defaults(session, current_user.tenant_id)
    mid = _uuid(marca_id)
    result = await ModelosService(session).list_items(
        PageParams(page=page, size=25), search=q or None, marca_id=mid
    )
    marcas = await MarcasService(session).list_items(PageParams(page=1, size=200))
    return render(
        request,
        "frota/modelos_list.html",
        {
            "page_result": result,
            "q": q,
            "marca_id": marca_id,
            "marcas": marcas.items,
            "title": "Modelos",
        },
    )


@router.get("/frota/modelos/novo", response_class=HTMLResponse)
async def modelo_new_form(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.modelo.criar"))
    ],
) -> HTMLResponse:
    await _ensure_frota_defaults(session, current_user.tenant_id)
    marcas = await MarcasService(session).list_items(PageParams(page=1, size=200))
    categorias = await CategoriasService(session).list_items(PageParams(page=1, size=200))
    return render(
        request,
        "frota/modelo_form.html",
        {
            "item": None,
            "error": None,
            "marcas": marcas.items,
            "categorias": categorias.items,
            "title": "Novo Modelo",
            "action": "/frota/modelos/novo",
        },
    )


@router.post("/frota/modelos/novo", response_class=HTMLResponse)
async def modelo_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.modelo.criar"))
    ],
    marca_id: Annotated[str, Form()],
    nome: Annotated[str, Form()],
    categoria_padrao_id: Annotated[str, Form()] = "",
    versao: Annotated[str, Form()] = "",
    motorizacao: Annotated[str, Form()] = "",
    cambio: Annotated[str, Form()] = "",
    portas: Annotated[str, Form()] = "",
    capacidade_tanque: Annotated[str, Form()] = "",
    consumo_medio_km_l: Annotated[str, Form()] = "",
    codigo_fipe: Annotated[str, Form()] = "",
    status: Annotated[str, Form()] = "active",
) -> HTMLResponse:
    marcas = await MarcasService(session).list_items(PageParams(page=1, size=200))
    categorias = await CategoriasService(session).list_items(PageParams(page=1, size=200))
    ctx = {
        "item": None,
        "error": None,
        "marcas": marcas.items,
        "categorias": categorias.items,
        "title": "Novo Modelo",
        "action": "/frota/modelos/novo",
    }
    try:
        await ModelosService(session).create(
            current_user.tenant_id,
            ModeloCreate(
                marca_id=uuid.UUID(marca_id),
                categoria_padrao_id=_uuid(categoria_padrao_id),
                nome=nome,
                versao=versao or None,
                motorizacao=motorizacao or None,
                cambio=cambio or None,
                portas=int(portas) if portas.strip() else None,
                capacidade_tanque=_dec(capacidade_tanque) if capacidade_tanque.strip() else None,
                consumo_medio_km_l=_dec(consumo_medio_km_l) if consumo_medio_km_l.strip() else None,
                codigo_fipe=codigo_fipe or None,
                status=CadastroStatus(status),
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _app_error_message(exc)
        return render(request, "frota/modelo_form.html", ctx, status_code=400)
    return RedirectResponse("/frota/modelos", status_code=303)


@router.get("/frota/modelos/{item_id}/editar", response_class=HTMLResponse)
async def modelo_edit_form(
    request: Request,
    session: SessionDep,
    item_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.modelo.editar"))
    ],
) -> HTMLResponse:
    await _ensure_frota_defaults(session, current_user.tenant_id)
    item = await ModelosService(session).get(item_id)
    marcas = await MarcasService(session).list_items(PageParams(page=1, size=200))
    categorias = await CategoriasService(session).list_items(PageParams(page=1, size=200))
    return render(
        request,
        "frota/modelo_form.html",
        {
            "item": item,
            "error": None,
            "marcas": marcas.items,
            "categorias": categorias.items,
            "title": "Editar Modelo",
            "action": f"/frota/modelos/{item_id}/editar",
        },
    )


@router.post("/frota/modelos/{item_id}/editar", response_class=HTMLResponse)
async def modelo_update(
    request: Request,
    session: SessionDep,
    item_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.modelo.editar"))
    ],
    marca_id: Annotated[str, Form()],
    nome: Annotated[str, Form()],
    categoria_padrao_id: Annotated[str, Form()] = "",
    versao: Annotated[str, Form()] = "",
    motorizacao: Annotated[str, Form()] = "",
    cambio: Annotated[str, Form()] = "",
    portas: Annotated[str, Form()] = "",
    capacidade_tanque: Annotated[str, Form()] = "",
    consumo_medio_km_l: Annotated[str, Form()] = "",
    codigo_fipe: Annotated[str, Form()] = "",
    status: Annotated[str, Form()] = "active",
) -> HTMLResponse:
    marcas = await MarcasService(session).list_items(PageParams(page=1, size=200))
    categorias = await CategoriasService(session).list_items(PageParams(page=1, size=200))
    try:
        await ModelosService(session).update(
            item_id,
            ModeloUpdate(
                marca_id=uuid.UUID(marca_id),
                categoria_padrao_id=_uuid(categoria_padrao_id),
                nome=nome,
                versao=versao or None,
                motorizacao=motorizacao or None,
                cambio=cambio or None,
                portas=int(portas) if portas.strip() else None,
                capacidade_tanque=_dec(capacidade_tanque) if capacidade_tanque.strip() else None,
                consumo_medio_km_l=_dec(consumo_medio_km_l) if consumo_medio_km_l.strip() else None,
                codigo_fipe=codigo_fipe or None,
                status=CadastroStatus(status),
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        item = await ModelosService(session).get(item_id)
        return render(
            request,
            "frota/modelo_form.html",
            {
                "item": item,
                "error": _app_error_message(exc),
                "marcas": marcas.items,
                "categorias": categorias.items,
                "title": "Editar Modelo",
                "action": f"/frota/modelos/{item_id}/editar",
            },
            status_code=400,
        )
    return RedirectResponse("/frota/modelos", status_code=303)


# ================================================================ Acessórios
@router.get("/frota/acessorios", response_class=HTMLResponse)
async def acessorios_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.acessorio.visualizar"))
    ],
    page: int = 1,
    q: str = "",
) -> HTMLResponse:
    result = await AcessoriosService(session).list_items(
        PageParams(page=page, size=25), search=q or None
    )
    return render(
        request,
        "frota/acessorios_list.html",
        {"page_result": result, "q": q, "title": "Acessórios"},
    )


@router.get("/frota/acessorios/novo", response_class=HTMLResponse)
async def acessorio_new_form(
    request: Request,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.acessorio.criar"))
    ],
) -> HTMLResponse:
    return render(
        request,
        "frota/acessorio_form.html",
        {"item": None, "error": None, "title": "Novo Acessório", "action": "/frota/acessorios/novo"},
    )


@router.post("/frota/acessorios/novo", response_class=HTMLResponse)
async def acessorio_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.acessorio.criar"))
    ],
    nome: Annotated[str, Form()],
    descricao: Annotated[str, Form()] = "",
    tipo: Annotated[str, Form()] = "fixo",
    valor_diaria: Annotated[str, Form()] = "0",
    estoque_disponivel: Annotated[int, Form()] = 0,
    foto_url: Annotated[str, Form()] = "",
    status: Annotated[str, Form()] = "active",
) -> HTMLResponse:
    ctx = {"item": None, "error": None, "title": "Novo Acessório", "action": "/frota/acessorios/novo"}
    try:
        await AcessoriosService(session).create(
            current_user.tenant_id,
            AcessorioCreate(
                nome=nome,
                descricao=descricao or None,
                tipo=AcessorioTipo(tipo),
                valor_diaria=_dec(valor_diaria),
                estoque_disponivel=estoque_disponivel,
                foto_url=foto_url or None,
                status=CadastroStatus(status),
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _app_error_message(exc)
        return render(request, "frota/acessorio_form.html", ctx, status_code=400)
    return RedirectResponse("/frota/acessorios", status_code=303)


@router.get("/frota/acessorios/{item_id}/editar", response_class=HTMLResponse)
async def acessorio_edit_form(
    request: Request,
    session: SessionDep,
    item_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.acessorio.editar"))
    ],
) -> HTMLResponse:
    item = await AcessoriosService(session).get(item_id)
    return render(
        request,
        "frota/acessorio_form.html",
        {
            "item": item,
            "error": None,
            "title": "Editar Acessório",
            "action": f"/frota/acessorios/{item_id}/editar",
        },
    )


@router.post("/frota/acessorios/{item_id}/editar", response_class=HTMLResponse)
async def acessorio_update(
    request: Request,
    session: SessionDep,
    item_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.acessorio.editar"))
    ],
    nome: Annotated[str, Form()],
    descricao: Annotated[str, Form()] = "",
    tipo: Annotated[str, Form()] = "fixo",
    valor_diaria: Annotated[str, Form()] = "0",
    estoque_disponivel: Annotated[int, Form()] = 0,
    foto_url: Annotated[str, Form()] = "",
    status: Annotated[str, Form()] = "active",
) -> HTMLResponse:
    try:
        await AcessoriosService(session).update(
            item_id,
            AcessorioUpdate(
                nome=nome,
                descricao=descricao or None,
                tipo=AcessorioTipo(tipo),
                valor_diaria=_dec(valor_diaria),
                estoque_disponivel=estoque_disponivel,
                foto_url=foto_url or None,
                status=CadastroStatus(status),
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        item = await AcessoriosService(session).get(item_id)
        return render(
            request,
            "frota/acessorio_form.html",
            {
                "item": item,
                "error": _app_error_message(exc),
                "title": "Editar Acessório",
                "action": f"/frota/acessorios/{item_id}/editar",
            },
            status_code=400,
        )
    return RedirectResponse("/frota/acessorios", status_code=303)


# ============================================================== Documentação
@router.get("/frota/documentacao", response_class=HTMLResponse)
async def documentacao_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.documentacao.visualizar"))
    ],
    page: int = 1,
    veiculo_id: str = "",
    status: str = "",
    days: str = "",
) -> HTMLResponse:
    svc = DocumentoService(session)
    vid = _uuid(veiculo_id)
    st = DocumentoVeiculoStatus(status) if status else None
    if days and days in {"30", "60", "90"}:
        result = await svc.list_vencimentos(PageParams(page=page, size=25), days=int(days))
    else:
        result = await svc.list_items(
            PageParams(page=page, size=25), veiculo_id=vid, status=st
        )
    veiculos = await VeiculoService(session).list_items(PageParams(page=1, size=200))
    return render(
        request,
        "frota/documentacao_list.html",
        {
            "page_result": result,
            "veiculo_id": veiculo_id,
            "status": status,
            "days": days,
            "veiculos": veiculos.items,
            "title": "Documentação",
        },
    )


@router.get("/frota/documentacao/novo", response_class=HTMLResponse)
async def documento_new_form(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.documentacao.criar"))
    ],
) -> HTMLResponse:
    veiculos = await VeiculoService(session).list_items(PageParams(page=1, size=200))
    return render(
        request,
        "frota/documento_form.html",
        {
            "item": None,
            "error": None,
            "veiculos": veiculos.items,
            "title": "Novo Documento",
            "action": "/frota/documentacao/novo",
        },
    )


@router.post("/frota/documentacao/novo", response_class=HTMLResponse)
async def documento_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.documentacao.criar"))
    ],
    veiculo_id: Annotated[str, Form()],
    tipo: Annotated[str, Form()],
    data_validade: Annotated[str, Form()],
    numero: Annotated[str, Form()] = "",
    orgao_emissor: Annotated[str, Form()] = "",
    data_emissao: Annotated[str, Form()] = "",
    arquivo_key: Annotated[str, Form()] = "",
    observacoes: Annotated[str, Form()] = "",
) -> HTMLResponse:
    veiculos = await VeiculoService(session).list_items(PageParams(page=1, size=200))
    ctx = {
        "item": None,
        "error": None,
        "veiculos": veiculos.items,
        "title": "Novo Documento",
        "action": "/frota/documentacao/novo",
    }
    try:
        validade = _date(data_validade)
        if validade is None:
            raise ValueError("Data de validade é obrigatória.")
        await DocumentoService(session).create(
            current_user.tenant_id,
            DocumentoCreate(
                veiculo_id=uuid.UUID(veiculo_id),
                tipo=DocumentoVeiculoTipo(tipo),
                numero=numero or None,
                orgao_emissor=orgao_emissor or None,
                data_emissao=_date(data_emissao),
                data_validade=validade,
                arquivo_key=arquivo_key or None,
                observacoes=observacoes or None,
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _app_error_message(exc)
        return render(request, "frota/documento_form.html", ctx, status_code=400)
    return RedirectResponse("/frota/documentacao", status_code=303)


@router.get("/frota/documentacao/{item_id}/editar", response_class=HTMLResponse)
async def documento_edit_form(
    request: Request,
    session: SessionDep,
    item_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.documentacao.editar"))
    ],
) -> HTMLResponse:
    item = await DocumentoService(session).get(item_id)
    veiculos = await VeiculoService(session).list_items(PageParams(page=1, size=200))
    return render(
        request,
        "frota/documento_form.html",
        {
            "item": item,
            "error": None,
            "veiculos": veiculos.items,
            "title": "Editar Documento",
            "action": f"/frota/documentacao/{item_id}/editar",
        },
    )


@router.post("/frota/documentacao/{item_id}/editar", response_class=HTMLResponse)
async def documento_update(
    request: Request,
    session: SessionDep,
    item_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.documentacao.editar"))
    ],
    tipo: Annotated[str, Form()],
    data_validade: Annotated[str, Form()] = "",
    numero: Annotated[str, Form()] = "",
    orgao_emissor: Annotated[str, Form()] = "",
    data_emissao: Annotated[str, Form()] = "",
    arquivo_key: Annotated[str, Form()] = "",
    observacoes: Annotated[str, Form()] = "",
) -> HTMLResponse:
    veiculos = await VeiculoService(session).list_items(PageParams(page=1, size=200))
    try:
        await DocumentoService(session).update(
            item_id,
            DocumentoUpdate(
                tipo=DocumentoVeiculoTipo(tipo),
                numero=numero or None,
                orgao_emissor=orgao_emissor or None,
                data_emissao=_date(data_emissao),
                data_validade=_date(data_validade),
                arquivo_key=arquivo_key or None,
                observacoes=observacoes or None,
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        item = await DocumentoService(session).get(item_id)
        return render(
            request,
            "frota/documento_form.html",
            {
                "item": item,
                "error": _app_error_message(exc),
                "veiculos": veiculos.items,
                "title": "Editar Documento",
                "action": f"/frota/documentacao/{item_id}/editar",
            },
            status_code=400,
        )
    return RedirectResponse("/frota/documentacao", status_code=303)


# ================================================================ Telemetria
@router.get("/frota/telemetria", response_class=HTMLResponse)
async def telemetria_list(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.telemetria.visualizar"))
    ],
    page: int = 1,
) -> HTMLResponse:
    result = await TelemetriaService(session).list_dispositivos(PageParams(page=page, size=25))
    return render(
        request,
        "frota/telemetria_list.html",
        {"page_result": result, "title": "Telemetria"},
    )


@router.get("/frota/telemetria/novo", response_class=HTMLResponse)
async def telemetria_new_form(
    request: Request,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.telemetria.criar"))
    ],
) -> HTMLResponse:
    veiculos = await VeiculoService(session).list_items(PageParams(page=1, size=200))
    return render(
        request,
        "frota/telemetria_form.html",
        {
            "dispositivo": None,
            "eventos": None,
            "error": None,
            "veiculos": veiculos.items,
            "title": "Novo Dispositivo",
            "action": "/frota/telemetria/novo",
        },
    )


@router.post("/frota/telemetria/novo", response_class=HTMLResponse)
async def telemetria_upsert(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.telemetria.criar"))
    ],
    veiculo_id: Annotated[str, Form()],
    provedor: Annotated[str, Form()],
    equipamento_id: Annotated[str, Form()],
    conn_status: Annotated[str, Form()] = "offline",
    lat: Annotated[str, Form()] = "",
    lng: Annotated[str, Form()] = "",
    ultima_posicao_em: Annotated[str, Form()] = "",
    km_telemetria: Annotated[str, Form()] = "",
    bloqueio_remoto: Annotated[str, Form()] = "",
    observacoes: Annotated[str, Form()] = "",
) -> HTMLResponse:
    veiculos = await VeiculoService(session).list_items(PageParams(page=1, size=200))
    ctx = {
        "dispositivo": None,
        "eventos": None,
        "error": None,
        "veiculos": veiculos.items,
        "title": "Novo Dispositivo",
        "action": "/frota/telemetria/novo",
    }
    try:
        dispositivo = await TelemetriaService(session).upsert_dispositivo(
            current_user.tenant_id,
            TelemetriaDispositivoUpsert(
                veiculo_id=uuid.UUID(veiculo_id),
                provedor=provedor,
                equipamento_id=equipamento_id,
                conn_status=TelemetriaConnStatus(conn_status),
                lat=_dec(lat) if lat.strip() else None,
                lng=_dec(lng) if lng.strip() else None,
                ultima_posicao_em=_datetime(ultima_posicao_em),
                km_telemetria=int(km_telemetria) if km_telemetria.strip() else None,
                bloqueio_remoto=bool(bloqueio_remoto),
                observacoes=observacoes or None,
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        ctx["error"] = _app_error_message(exc)
        return render(request, "frota/telemetria_form.html", ctx, status_code=400)
    return RedirectResponse(f"/frota/telemetria/{dispositivo.veiculo_id}", status_code=303)


@router.get("/frota/telemetria/{veiculo_id}", response_class=HTMLResponse)
async def telemetria_detail(
    request: Request,
    session: SessionDep,
    veiculo_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.telemetria.visualizar"))
    ],
) -> HTMLResponse:
    svc = TelemetriaService(session)
    veiculo = await VeiculoService(session).get(veiculo_id)
    dispositivos = await svc.list_dispositivos(PageParams(page=1, size=500))
    dispositivo = next((d for d in dispositivos.items if d.veiculo_id == veiculo_id), None)
    eventos = await svc.list_eventos(PageParams(page=1, size=50), veiculo_id)
    veiculos = await VeiculoService(session).list_items(PageParams(page=1, size=200))
    return render(
        request,
        "frota/telemetria_form.html",
        {
            "dispositivo": dispositivo,
            "veiculo": veiculo,
            "eventos": eventos,
            "error": None,
            "veiculos": veiculos.items,
            "title": f"Telemetria — {veiculo.placa}",
            "action": f"/frota/telemetria/{veiculo_id}",
        },
    )


@router.post("/frota/telemetria/{veiculo_id}", response_class=HTMLResponse)
async def telemetria_detail_upsert(
    request: Request,
    session: SessionDep,
    veiculo_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.telemetria.editar"))
    ],
    provedor: Annotated[str, Form()],
    equipamento_id: Annotated[str, Form()],
    conn_status: Annotated[str, Form()] = "offline",
    lat: Annotated[str, Form()] = "",
    lng: Annotated[str, Form()] = "",
    ultima_posicao_em: Annotated[str, Form()] = "",
    km_telemetria: Annotated[str, Form()] = "",
    bloqueio_remoto: Annotated[str, Form()] = "",
    observacoes: Annotated[str, Form()] = "",
) -> HTMLResponse:
    svc = TelemetriaService(session)
    veiculo = await VeiculoService(session).get(veiculo_id)
    veiculos = await VeiculoService(session).list_items(PageParams(page=1, size=200))
    try:
        await svc.upsert_dispositivo(
            current_user.tenant_id,
            TelemetriaDispositivoUpsert(
                veiculo_id=veiculo_id,
                provedor=provedor,
                equipamento_id=equipamento_id,
                conn_status=TelemetriaConnStatus(conn_status),
                lat=_dec(lat) if lat.strip() else None,
                lng=_dec(lng) if lng.strip() else None,
                ultima_posicao_em=_datetime(ultima_posicao_em),
                km_telemetria=int(km_telemetria) if km_telemetria.strip() else None,
                bloqueio_remoto=bool(bloqueio_remoto),
                observacoes=observacoes or None,
            ),
        )
    except (AppError, ValueError) as exc:
        await session.rollback()
        dispositivos = await svc.list_dispositivos(PageParams(page=1, size=500))
        dispositivo = next((d for d in dispositivos.items if d.veiculo_id == veiculo_id), None)
        eventos = await svc.list_eventos(PageParams(page=1, size=50), veiculo_id)
        return render(
            request,
            "frota/telemetria_form.html",
            {
                "dispositivo": dispositivo,
                "veiculo": veiculo,
                "eventos": eventos,
                "error": _app_error_message(exc),
                "veiculos": veiculos.items,
                "title": f"Telemetria — {veiculo.placa}",
                "action": f"/frota/telemetria/{veiculo_id}",
            },
            status_code=400,
        )
    return RedirectResponse(f"/frota/telemetria/{veiculo_id}", status_code=303)


@router.post("/frota/telemetria/{veiculo_id}/evento", response_class=HTMLResponse)
async def telemetria_register_evento(
    session: SessionDep,
    veiculo_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("frota.telemetria.criar"))
    ],
    dispositivo_id: Annotated[str, Form()],
    tipo: Annotated[str, Form()],
    ocorrido_em: Annotated[str, Form()],
    descricao: Annotated[str, Form()] = "",
    lat: Annotated[str, Form()] = "",
    lng: Annotated[str, Form()] = "",
    velocidade: Annotated[str, Form()] = "",
    payload_json: Annotated[str, Form()] = "",
) -> RedirectResponse:
    ocorrido = _datetime(ocorrido_em)
    if ocorrido is None:
        ocorrido = datetime.now()
    await TelemetriaService(session).register_evento(
        current_user.tenant_id,
        TelemetriaEventoCreate(
            dispositivo_id=uuid.UUID(dispositivo_id),
            veiculo_id=veiculo_id,
            tipo=TelemetriaEventoTipo(tipo),
            descricao=descricao or None,
            lat=_dec(lat) if lat.strip() else None,
            lng=_dec(lng) if lng.strip() else None,
            velocidade=_dec(velocidade) if velocidade.strip() else None,
            ocorrido_em=ocorrido,
            payload_json=payload_json or None,
        ),
    )
    return RedirectResponse(f"/frota/telemetria/{veiculo_id}", status_code=303)
