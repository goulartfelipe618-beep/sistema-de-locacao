"""Rotas Web (HTML/Jinja2/HTMX) do módulo de Cadastros."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_web_permission, require_web_user
from app.core.exceptions import AppError
from app.core.pagination import PageParams
from app.core.templating import render
from app.modules.cadastros.cliente_documentos import (
    CLIENTE_DOCUMENTO_CAMPOS,
    ClienteDocumentoService,
)
from app.modules.cadastros.dossier import build_cliente_dossier
from app.modules.cadastros.schemas import ClienteCreate, ClienteUpdate, TabelaAuxiliarCreate
from app.modules.cadastros.service import ClienteService, TabelaAuxiliarService
from app.modules.cadastros.web_extra import router as cadastros_extra_router
from app.modules.identity.service import AuthenticatedUser
from app.shared.enums import ClienteDocumentoTipo, ClienteStatus, MotoristaCnhStatus, PersonType

router = APIRouter()
router.include_router(cadastros_extra_router)
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/cadastros/cep/{cep}")
async def consultar_cep_web(
    cep: str,
    _user: Annotated[AuthenticatedUser, Depends(require_web_user)],
) -> JSONResponse:
    from app.shared.viacep import consultar_cep

    data = await consultar_cep(cep)
    return JSONResponse(content=data)


@router.get("/cadastros/ibge/ufs")
async def ibge_ufs_web(
    _user: Annotated[AuthenticatedUser, Depends(require_web_user)],
) -> JSONResponse:
    from app.shared.ibge import list_ufs

    return JSONResponse(content=await list_ufs())


@router.get("/cadastros/ibge/municipios/{uf}")
async def ibge_municipios_web(
    uf: str,
    _user: Annotated[AuthenticatedUser, Depends(require_web_user)],
) -> JSONResponse:
    from app.shared.ibge import list_municipios

    return JSONResponse(content=await list_municipios(uf))


@router.get("/cadastros/clientes/json")
async def clientes_json(
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("cadastros.cliente.visualizar"))
    ],
    q: str = "",
    page: int = 1,
) -> JSONResponse:
    """Busca async de clientes para combobox nos formulários."""
    result = await ClienteService(session).list_clientes(
        PageParams(page=page, size=25), search=q or None
    )
    items = []
    for c in result.items:
        doc = c.cpf or c.cnpj or ""
        label = c.nome if not doc else f"{c.nome} ({doc})"
        items.append({"id": str(c.id), "label": label, "nome": c.nome, "doc": doc})
    return JSONResponse(content={"items": items, "total": result.total, "page": page})


@router.get("/cadastros/clientes/{cliente_id}/resumo")
async def cliente_resumo_json(
    cliente_id: uuid.UUID,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("cadastros.cliente.visualizar"))
    ],
) -> JSONResponse:
    cliente = await ClienteService(session).get(cliente_id)
    doc = cliente.cpf or cliente.cnpj or ""
    return JSONResponse(content={"id": str(cliente.id), "nome": cliente.nome, "doc": doc})


@router.get("/cadastros/clientes/{cliente_id}/impacto")
async def cliente_impacto_web(
    cliente_id: uuid.UUID,
    session: SessionDep,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("cadastros.cliente.visualizar"))
    ],
) -> JSONResponse:
    from app.shared.entity_impact import cliente_impact

    return JSONResponse(content=await cliente_impact(session, cliente_id))


def _parse_decimal(raw: str | None) -> Decimal:
    if not raw or not raw.strip():
        return Decimal("0.00")
    normalized = raw.strip().replace(".", "").replace(",", ".")
    try:
        return Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError("Limite de crédito inválido.") from exc


def _parse_date(raw: str | None) -> date | None:
    if not raw or not raw.strip():
        return None
    return date.fromisoformat(raw.strip())


async def _cnh_categorias(session: AsyncSession, tenant_id: uuid.UUID):
    await TabelaAuxiliarService(session).ensure_defaults(tenant_id)
    return (
        await TabelaAuxiliarService(session).list_by_grupo(
            "cnh_categoria", PageParams(page=1, size=50), apenas_ativos=True
        )
    ).items


def _cliente_cnh_fields(
    *,
    cnh_numero: str,
    cnh_categoria: str,
    cnh_validade: str,
    cnh_status: str,
    cnh_emissao: str = "",
    cnh_orgao: str = "",
    cnh_pontuacao: str = "",
) -> dict:
    return {
        "cnh_numero": cnh_numero.strip() or None,
        "cnh_categoria": cnh_categoria.strip() or None,
        "cnh_validade": _parse_date(cnh_validade),
        "cnh_emissao": _parse_date(cnh_emissao),
        "cnh_orgao": cnh_orgao.strip() or None,
        "cnh_status": MotoristaCnhStatus(cnh_status or "regular"),
        "cnh_pontuacao": int(cnh_pontuacao) if cnh_pontuacao.strip().isdigit() else None,
    }


async def _motivos_bloqueio(session: AsyncSession, tenant_id: uuid.UUID):
    await TabelaAuxiliarService(session).ensure_defaults(tenant_id)
    return (
        await TabelaAuxiliarService(session).list_by_grupo(
            "motivo_bloqueio", PageParams(page=1, size=50), apenas_ativos=True
        )
    ).items


async def _cliente_documentos_context(session: AsyncSession, cliente_id: uuid.UUID) -> dict:
    documentos = await ClienteDocumentoService(session).map_by_tipo(cliente_id)
    return {"documentos": documentos, "documento_campos": CLIENTE_DOCUMENTO_CAMPOS}


_UPLOAD_FIELD_TO_TIPO: dict[str, ClienteDocumentoTipo] = {
    field_name: ClienteDocumentoTipo(tipo_value)
    for tipo_value, field_name, _label, _required in CLIENTE_DOCUMENTO_CAMPOS
}


# ============================================================== Clientes
@router.get("/cadastros/clientes", response_class=HTMLResponse)
async def clientes_list(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("cadastros.cliente.visualizar"))
    ],
    page: int = 1,
    q: str = "",
) -> HTMLResponse:
    """Lista clientes com busca."""
    await TabelaAuxiliarService(session).ensure_defaults(current_user.tenant_id)
    result = await ClienteService(session).list_clientes(PageParams(page=page, size=25), search=q or None)
    return render(
        request,
        "cadastros/clientes_list.html",
        {"page_result": result, "q": q, "title": "Clientes"},
    )


@router.get("/cadastros/clientes/novo", response_class=HTMLResponse)
async def cliente_new_form(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("cadastros.cliente.criar"))
    ],
) -> HTMLResponse:
    """Formulário de novo cliente."""
    await TabelaAuxiliarService(session).ensure_defaults(current_user.tenant_id)
    categorias = await TabelaAuxiliarService(session).list_by_grupo(
        "categoria_cliente", PageParams(page=1, size=100), apenas_ativos=True
    )
    return render(
        request,
        "cadastros/cliente_form.html",
        {
            "cliente": None,
            "error": None,
            "categorias": categorias.items,
            "cnh_cats": await _cnh_categorias(session, current_user.tenant_id),
            "title": "Novo Cliente",
            "action": "/cadastros/clientes/novo",
        },
    )


@router.post("/cadastros/clientes/novo", response_class=HTMLResponse)
async def cliente_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("cadastros.cliente.criar"))
    ],
    person_type: Annotated[str, Form()],
    nome: Annotated[str, Form()],
    status: Annotated[str, Form()] = "active",
    nome_fantasia: Annotated[str, Form()] = "",
    cpf: Annotated[str, Form()] = "",
    cnpj: Annotated[str, Form()] = "",
    email: Annotated[str, Form()] = "",
    telefone: Annotated[str, Form()] = "",
    celular: Annotated[str, Form()] = "",
    cep: Annotated[str, Form()] = "",
    endereco: Annotated[str, Form()] = "",
    numero: Annotated[str, Form()] = "",
    complemento: Annotated[str, Form()] = "",
    bairro: Annotated[str, Form()] = "",
    cidade: Annotated[str, Form()] = "",
    uf: Annotated[str, Form()] = "",
    categoria_codigo: Annotated[str, Form()] = "",
    limite_credito: Annotated[str, Form()] = "0",
    observacoes: Annotated[str, Form()] = "",
    cnh_numero: Annotated[str, Form()] = "",
    cnh_categoria: Annotated[str, Form()] = "",
    cnh_validade: Annotated[str, Form()] = "",
    cnh_status: Annotated[str, Form()] = "regular",
    cnh_emissao: Annotated[str, Form()] = "",
    cnh_orgao: Annotated[str, Form()] = "",
    cnh_pontuacao: Annotated[str, Form()] = "",
) -> HTMLResponse:
    """Cria cliente."""
    categorias = await TabelaAuxiliarService(session).list_by_grupo(
        "categoria_cliente", PageParams(page=1, size=100), apenas_ativos=True
    )
    cnh_cats = await _cnh_categorias(session, current_user.tenant_id)
    try:
        data = ClienteCreate(
            person_type=PersonType(person_type),
            status=ClienteStatus(status),
            nome=nome,
            nome_fantasia=nome_fantasia or None,
            cpf=cpf or None,
            cnpj=cnpj or None,
            email=email or None,
            telefone=telefone or None,
            celular=celular or None,
            cep=cep or None,
            endereco=endereco or None,
            numero=numero or None,
            complemento=complemento or None,
            bairro=bairro or None,
            cidade=cidade or None,
            uf=uf or None,
            categoria_codigo=categoria_codigo or None,
            limite_credito=_parse_decimal(limite_credito),
            observacoes=observacoes or None,
            **_cliente_cnh_fields(
                cnh_numero=cnh_numero,
                cnh_categoria=cnh_categoria,
                cnh_validade=cnh_validade,
                cnh_status=cnh_status,
                cnh_emissao=cnh_emissao,
                cnh_orgao=cnh_orgao,
                cnh_pontuacao=cnh_pontuacao,
            ),
        )
        cliente = await ClienteService(session).create(current_user.tenant_id, data)
    except (AppError, ValueError) as exc:
        await session.rollback()
        message = exc.message if isinstance(exc, AppError) else str(exc)
        return render(
            request,
            "cadastros/cliente_form.html",
            {
                "cliente": None,
                "error": message,
                "categorias": categorias.items,
                "cnh_cats": cnh_cats,
                "title": "Novo Cliente",
                "action": "/cadastros/clientes/novo",
                "form": {
                    "person_type": person_type,
                    "nome": nome,
                    "cpf": cpf,
                    "cnpj": cnpj,
                    "email": email,
                },
            },
            status_code=400,
        )
    return RedirectResponse(url=f"/cadastros/clientes/{cliente.id}", status_code=303)


@router.get("/cadastros/clientes/{cliente_id}", response_class=HTMLResponse)
async def cliente_dossie(
    request: Request,
    session: SessionDep,
    cliente_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("cadastros.cliente.visualizar"))
    ],
    msg: str = "",
) -> HTMLResponse:
    """Dossiê completo do cliente."""
    await TabelaAuxiliarService(session).ensure_defaults(current_user.tenant_id)
    dossier = await build_cliente_dossier(session, cliente_id)
    return render(
        request,
        "cadastros/cliente_dossie.html",
        {
            "dossier": dossier,
            "cliente": dossier.cliente,
            "motivos_bloqueio": await _motivos_bloqueio(session, current_user.tenant_id),
            "documento_campos": CLIENTE_DOCUMENTO_CAMPOS,
            "title": f"Dossiê — {dossier.cliente.nome}",
            "msg": msg,
        },
    )


@router.get("/cadastros/clientes/{cliente_id}/editar", response_class=HTMLResponse)
async def cliente_edit_form(
    request: Request,
    session: SessionDep,
    cliente_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("cadastros.cliente.editar"))
    ],
    msg: str = "",
) -> HTMLResponse:
    """Formulário de edição de cliente."""
    await TabelaAuxiliarService(session).ensure_defaults(current_user.tenant_id)
    cliente = await ClienteService(session).get(cliente_id)
    categorias = await TabelaAuxiliarService(session).list_by_grupo(
        "categoria_cliente", PageParams(page=1, size=100), apenas_ativos=True
    )
    return render(
        request,
        "cadastros/cliente_form.html",
        {
            "cliente": cliente,
            "error": None,
            "msg": msg,
            "categorias": categorias.items,
            "cnh_cats": await _cnh_categorias(session, current_user.tenant_id),
            "title": "Editar Cliente",
            "action": f"/cadastros/clientes/{cliente_id}/editar",
            **await _cliente_documentos_context(session, cliente_id),
        },
    )


@router.post("/cadastros/clientes/{cliente_id}/editar", response_class=HTMLResponse)
async def cliente_update(
    request: Request,
    session: SessionDep,
    cliente_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("cadastros.cliente.editar"))
    ],
    nome: Annotated[str, Form()],
    status: Annotated[str, Form()] = "active",
    nome_fantasia: Annotated[str, Form()] = "",
    email: Annotated[str, Form()] = "",
    telefone: Annotated[str, Form()] = "",
    celular: Annotated[str, Form()] = "",
    cep: Annotated[str, Form()] = "",
    endereco: Annotated[str, Form()] = "",
    numero: Annotated[str, Form()] = "",
    complemento: Annotated[str, Form()] = "",
    bairro: Annotated[str, Form()] = "",
    cidade: Annotated[str, Form()] = "",
    uf: Annotated[str, Form()] = "",
    categoria_codigo: Annotated[str, Form()] = "",
    limite_credito: Annotated[str, Form()] = "0",
    observacoes: Annotated[str, Form()] = "",
    cnh_numero: Annotated[str, Form()] = "",
    cnh_categoria: Annotated[str, Form()] = "",
    cnh_validade: Annotated[str, Form()] = "",
    cnh_status: Annotated[str, Form()] = "regular",
    cnh_emissao: Annotated[str, Form()] = "",
    cnh_orgao: Annotated[str, Form()] = "",
    cnh_pontuacao: Annotated[str, Form()] = "",
) -> HTMLResponse:
    """Atualiza cliente."""
    categorias = await TabelaAuxiliarService(session).list_by_grupo(
        "categoria_cliente", PageParams(page=1, size=100), apenas_ativos=True
    )
    cnh_cats = await _cnh_categorias(session, current_user.tenant_id)
    existing = await ClienteService(session).get(cliente_id)
    try:
        if existing.status == ClienteStatus.BLOCKED:
            status_value = ClienteStatus.BLOCKED
        else:
            status_value = ClienteStatus(status)
            if status_value == ClienteStatus.BLOCKED:
                raise ValueError("Use o Dossiê para bloquear o cliente.")
        data = ClienteUpdate(
            status=status_value,
            nome=nome,
            nome_fantasia=nome_fantasia or None,
            email=email or None,
            telefone=telefone or None,
            celular=celular or None,
            cep=cep or None,
            endereco=endereco or None,
            numero=numero or None,
            complemento=complemento or None,
            bairro=bairro or None,
            cidade=cidade or None,
            uf=uf or None,
            categoria_codigo=categoria_codigo or None,
            limite_credito=_parse_decimal(limite_credito),
            observacoes=observacoes or None,
            **_cliente_cnh_fields(
                cnh_numero=cnh_numero,
                cnh_categoria=cnh_categoria,
                cnh_validade=cnh_validade,
                cnh_status=cnh_status,
                cnh_emissao=cnh_emissao,
                cnh_orgao=cnh_orgao,
                cnh_pontuacao=cnh_pontuacao,
            ),
        )
        await ClienteService(session).update(cliente_id, data)
    except (AppError, ValueError) as exc:
        await session.rollback()
        cliente = await ClienteService(session).get(cliente_id)
        message = exc.message if isinstance(exc, AppError) else str(exc)
        return render(
            request,
            "cadastros/cliente_form.html",
            {
                "cliente": cliente,
                "error": message,
                "categorias": categorias.items,
                "cnh_cats": cnh_cats,
                "title": "Editar Cliente",
                "action": f"/cadastros/clientes/{cliente_id}/editar",
                **await _cliente_documentos_context(session, cliente_id),
            },
            status_code=400,
        )
    return RedirectResponse(url=f"/cadastros/clientes/{cliente_id}", status_code=303)


@router.post("/cadastros/clientes/{cliente_id}/documentos", response_class=HTMLResponse)
async def cliente_upload_documentos(
    session: SessionDep,
    cliente_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("cadastros.cliente.editar"))
    ],
    doc_cnh: UploadFile | None = File(None),
    doc_comprovante_residencia: UploadFile | None = File(None),
    doc_holerite: UploadFile | None = File(None),
    doc_identidade: UploadFile | None = File(None),
) -> RedirectResponse:
    """Envia documentos anexados ao cliente."""
    uploads = {
        "doc_cnh": doc_cnh,
        "doc_comprovante_residencia": doc_comprovante_residencia,
        "doc_holerite": doc_holerite,
        "doc_identidade": doc_identidade,
    }
    svc = ClienteDocumentoService(session)
    enviados = 0
    erros: list[str] = []
    for field_name, upload in uploads.items():
        if upload is None or not upload.filename:
            continue
        tipo = _UPLOAD_FIELD_TO_TIPO[field_name]
        try:
            data = await upload.read()
            await svc.upload(
                current_user.tenant_id,
                cliente_id,
                tipo,
                file_bytes=data,
                filename=upload.filename,
                content_type=upload.content_type or "application/octet-stream",
            )
            enviados += 1
        except AppError as exc:
            await session.rollback()
            erros.append(exc.message)

    if erros and not enviados:
        msg = erros[0].replace(" ", "+")
    elif erros:
        msg = f"{enviados}+documento(s)+enviado(s).+Erros:+" + "+".join(erros).replace(" ", "+")
    elif enviados:
        msg = f"{enviados}+documento(s)+anexado(s)+com+sucesso"
    else:
        msg = "Nenhum+arquivo+selecionado"
    return RedirectResponse(
        url=f"/cadastros/clientes/{cliente_id}/editar?msg={msg}",
        status_code=303,
    )


@router.get(
    "/cadastros/clientes/{cliente_id}/documentos/{tipo}/download",
    response_model=None,
)
async def cliente_documento_download(
    session: SessionDep,
    cliente_id: uuid.UUID,
    tipo: str,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("cadastros.cliente.visualizar"))
    ],
) -> Response:
    """Download de documento anexado ao cliente."""
    try:
        tipo_enum = ClienteDocumentoTipo(tipo)
    except ValueError as exc:
        from app.core.exceptions import ValidationError

        raise ValidationError("Tipo de documento inválido.") from exc

    dl = await ClienteDocumentoService(session).resolve_download(cliente_id, tipo_enum)
    if dl.redirect_url:
        return RedirectResponse(url=dl.redirect_url, status_code=302)
    assert dl.data is not None
    return Response(
        content=dl.data,
        media_type=dl.content_type,
        headers={"Content-Disposition": f'inline; filename="{dl.filename}"'},
    )


@router.post("/cadastros/clientes/{cliente_id}/bloquear", response_class=HTMLResponse)
async def cliente_bloquear(
    session: SessionDep,
    cliente_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("cadastros.cliente.bloquear"))
    ],
    motivo_codigo: Annotated[str, Form()] = "",
    motivo_detalhe: Annotated[str, Form()] = "",
) -> RedirectResponse:
    """Bloqueia cliente via dossiê."""
    motivos = {m.codigo: m.descricao for m in await _motivos_bloqueio(session, _user.tenant_id)}
    codigo = motivo_codigo.strip().lower()
    if not codigo or codigo not in motivos:
        return RedirectResponse(
            url=f"/cadastros/clientes/{cliente_id}?msg=Selecione+um+motivo+de+bloqueio",
            status_code=303,
        )
    detalhe = motivo_detalhe.strip()
    if codigo == "outros" and not detalhe:
        return RedirectResponse(
            url=f"/cadastros/clientes/{cliente_id}?msg=Descreva+o+motivo+ao+selecionar+Outros",
            status_code=303,
        )
    rotulo = motivos[codigo]
    motivo = f"{rotulo}: {detalhe}" if detalhe else rotulo
    await ClienteService(session).bloquear(cliente_id, motivo, motivo_codigo=codigo)
    return RedirectResponse(
        url=f"/cadastros/clientes/{cliente_id}?msg=Cliente+bloqueado+com+sucesso",
        status_code=303,
    )


@router.post("/cadastros/clientes/{cliente_id}/desbloquear", response_class=HTMLResponse)
async def cliente_desbloquear(
    session: SessionDep,
    cliente_id: uuid.UUID,
    _user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("cadastros.cliente.bloquear"))
    ],
    observacao: Annotated[str, Form()] = "",
) -> RedirectResponse:
    """Remove bloqueio do cliente."""
    await ClienteService(session).desbloquear(cliente_id, observacao)
    return RedirectResponse(
        url=f"/cadastros/clientes/{cliente_id}?msg=Cliente+desbloqueado+com+sucesso",
        status_code=303,
    )


# ======================================================= Tabelas Auxiliares
@router.get("/cadastros/tabelas", response_class=HTMLResponse)
async def tabelas_list(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("cadastros.tabela.visualizar"))
    ],
    grupo: str = "categoria_cliente",
    page: int = 1,
) -> HTMLResponse:
    """Lista itens de tabelas auxiliares."""
    svc = TabelaAuxiliarService(session)
    await svc.ensure_defaults(current_user.tenant_id)
    grupos = await svc.list_grupos()
    result = await svc.list_by_grupo(grupo, PageParams(page=page, size=50))
    return render(
        request,
        "cadastros/tabelas_list.html",
        {
            "page_result": result,
            "grupos": grupos,
            "grupo": grupo,
            "title": "Tabelas Auxiliares",
        },
    )


@router.post("/cadastros/tabelas", response_class=HTMLResponse)
async def tabelas_create(
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("cadastros.tabela.criar"))
    ],
    grupo: Annotated[str, Form()],
    codigo: Annotated[str, Form()],
    descricao: Annotated[str, Form()],
    ordem: Annotated[int, Form()] = 0,
) -> RedirectResponse:
    """Cria item auxiliar."""
    await TabelaAuxiliarService(session).create(
        current_user.tenant_id,
        TabelaAuxiliarCreate(grupo=grupo, codigo=codigo, descricao=descricao, ordem=ordem),
    )
    return RedirectResponse(url=f"/cadastros/tabelas?grupo={grupo}", status_code=303)
