"""Rotas Web do módulo Relatórios (§11)."""

from __future__ import annotations

import json
import uuid
from datetime import date, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_web_permission
from app.core.exceptions import AppError
from app.core.templating import render
from app.modules.identity.service import AuthenticatedUser
from app.modules.relatorios.catalog import CATEGORIA_LABELS, REPORT_CATALOG, list_by_categoria
from app.modules.relatorios.service import AgendamentoService, EmissaoService
from app.modules.tenants.service import FilialService
from app.shared.enums import RelCategoria, RelFormato, RelRecorrencia

router = APIRouter()
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]

_CATEGORIA_PERM = {
    RelCategoria.FROTA: "relatorios.frota",
    RelCategoria.LOCACAO: "relatorios.locacao",
    RelCategoria.FINANCEIRO: "relatorios.financeiro",
    RelCategoria.FISCAL: "relatorios.fiscal",
    RelCategoria.GERENCIAL: "relatorios.gerencial",
}


def _default_periodo() -> tuple[str, str]:
    fim = date.today()
    ini = fim - timedelta(days=30)
    return ini.isoformat(), fim.isoformat()


def _parse_colunas(raw: list[str] | None) -> list[str] | None:
    return [c for c in (raw or []) if c.strip()] or None


@router.get("/relatorios/historico", response_class=HTMLResponse)
async def historico_list(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("relatorios.historico.visualizar"))
    ],
    page: int = 1,
) -> Any:
    result = await EmissaoService(session).list_historico(page=page, size=30)
    return render(
        request,
        "relatorios/historico.html",
        {
            "title": "Histórico de Emissões",
            "emissoes": result.items,
            "page": result.page,
            "pages": result.pages,
            "total": result.total,
        },
    )


@router.get("/relatorios/agendamentos", response_class=HTMLResponse)
async def agendamentos_list(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("relatorios.agendamento.visualizar"))
    ],
) -> Any:
    result = await AgendamentoService(session).list_items()
    return render(
        request,
        "relatorios/agendamentos_list.html",
        {"title": "Agendamentos de Relatórios", "agendamentos": result.items},
    )


@router.get("/relatorios/agendamentos/novo", response_class=HTMLResponse)
async def agendamento_novo_form(
    request: Request,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("relatorios.agendamento.criar"))
    ],
) -> Any:
    ini, fim = _default_periodo()
    return render(
        request,
        "relatorios/agendamento_form.html",
        {
            "title": "Novo agendamento",
            "agendamento": None,
            "catalogo": REPORT_CATALOG,
            "periodo_inicio": ini,
            "periodo_fim": fim,
        },
    )


@router.post("/relatorios/agendamentos/novo", response_class=HTMLResponse)
async def agendamento_novo_create(
    request: Request,
    session: SessionDep,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("relatorios.agendamento.criar"))
    ],
    nome: Annotated[str, Form()],
    categoria: Annotated[str, Form()],
    relatorio_codigo: Annotated[str, Form()],
    formato: Annotated[str, Form()] = "pdf",
    recorrencia: Annotated[str, Form()] = "mensal",
    periodo_inicio: Annotated[str, Form()] = "",
    periodo_fim: Annotated[str, Form()] = "",
    email_destinatarios: Annotated[str, Form()] = "",
) -> Any:
    params = {"periodo_inicio": periodo_inicio, "periodo_fim": periodo_fim}
    try:
        await AgendamentoService(session).create(
            current_user.tenant_id,
            user_id=current_user.id,
            nome=nome,
            categoria=RelCategoria(categoria),
            relatorio_codigo=relatorio_codigo,
            formato=RelFormato(formato),
            parametros=params,
            recorrencia=RelRecorrencia(recorrencia),
            email_destinatarios=email_destinatarios or None,
        )
        return RedirectResponse("/relatorios/agendamentos", status_code=303)
    except AppError as exc:
        ini, fim = _default_periodo()
        return render(
            request,
            "relatorios/agendamento_form.html",
            {
                "title": "Novo agendamento",
                "agendamento": None,
                "catalogo": REPORT_CATALOG,
                "periodo_inicio": periodo_inicio or ini,
                "periodo_fim": periodo_fim or fim,
                "error": str(exc),
            },
            status_code=400,
        )


def _hub(categoria: RelCategoria):
    slug = categoria.value

    async def handler(
        request: Request,
        session: SessionDep,
        current_user: Annotated[
            AuthenticatedUser,
            Depends(require_web_permission(f"relatorios.{slug}.visualizar")),
        ],
    ) -> Any:
        if categoria == RelCategoria.FISCAL:
            from app.modules.fiscal.guards import assert_fiscal_emissao_habilitada

            await assert_fiscal_emissao_habilitada(session, current_user.tenant_id)
        relatorios = list_by_categoria(categoria)
        return render(
            request,
            "relatorios/categoria_hub.html",
            {
                "title": f"Relatórios — {CATEGORIA_LABELS[categoria]}",
                "categoria": categoria,
                "categoria_label": CATEGORIA_LABELS[categoria],
                "relatorios": relatorios,
            },
        )

    return handler


for _cat in RelCategoria:
    router.add_api_route(
        f"/relatorios/{_cat.value}",
        _hub(_cat),
        methods=["GET"],
        response_class=HTMLResponse,
    )


@router.get("/relatorios/{categoria_slug}/{codigo}/emitir", response_class=HTMLResponse)
async def emitir_form(
    request: Request,
    session: SessionDep,
    categoria_slug: str,
    codigo: str,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("relatorios.historico.visualizar"))
    ],
) -> Any:
    try:
        categoria = RelCategoria(categoria_slug)
    except ValueError as exc:
        raise AppError("Categoria inválida.") from exc
    perm = f"{_CATEGORIA_PERM[categoria]}.visualizar"
    if not current_user.is_superuser and perm not in current_user.permissions:
        raise AppError("Sem permissão.")
    if categoria == RelCategoria.FISCAL:
        from app.modules.fiscal.guards import assert_fiscal_emissao_habilitada

        await assert_fiscal_emissao_habilitada(session, current_user.tenant_id)

    from app.modules.relatorios.catalog import get_report

    report = get_report(codigo)
    if report is None or report.categoria != categoria:
        raise AppError("Relatório não encontrado.")

    ini, fim = _default_periodo()
    filiais = await FilialService(session).list_all()
    return render(
        request,
        "relatorios/emitir_form.html",
        {
            "title": f"Emitir — {report.titulo}",
            "report": report,
            "categoria": categoria,
            "periodo_inicio": ini,
            "periodo_fim": fim,
            "filiais": filiais,
        },
    )


@router.post("/relatorios/{categoria_slug}/{codigo}/emitir", response_class=HTMLResponse)
async def emitir_submit(
    request: Request,
    session: SessionDep,
    categoria_slug: str,
    codigo: str,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("relatorios.historico.visualizar"))
    ],
    formato: Annotated[str, Form()] = "pdf",
    periodo_inicio: Annotated[str, Form()] = "",
    periodo_fim: Annotated[str, Form()] = "",
    filial_id: Annotated[str, Form()] = "",
    colunas: Annotated[list[str] | None, Form()] = None,
) -> Any:
    try:
        categoria = RelCategoria(categoria_slug)
    except ValueError as exc:
        raise AppError("Categoria inválida.") from exc
    export_perm = f"{_CATEGORIA_PERM[categoria]}.exportar"
    if not current_user.is_superuser and export_perm not in current_user.permissions:
        raise AppError("Sem permissão para exportar.")
    if categoria == RelCategoria.FISCAL:
        from app.modules.fiscal.guards import assert_fiscal_emissao_habilitada

        await assert_fiscal_emissao_habilitada(session, current_user.tenant_id)

    params: dict[str, Any] = {
        "periodo_inicio": periodo_inicio,
        "periodo_fim": periodo_fim,
    }
    if filial_id.strip():
        params["filial_id"] = filial_id.strip()
    cols = _parse_colunas(colunas)
    if cols:
        params["colunas"] = cols

    emissao = await EmissaoService(session).solicitar(
        current_user.tenant_id,
        user_id=current_user.id,
        categoria=categoria,
        relatorio_codigo=codigo,
        formato=RelFormato(formato),
        params=params,
    )
    return RedirectResponse(f"/relatorios/emissoes/{emissao.id}", status_code=303)


@router.get("/relatorios/emissoes/{emissao_id}", response_class=HTMLResponse)
async def emissao_status(
    request: Request,
    session: SessionDep,
    emissao_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("relatorios.historico.visualizar"))
    ],
) -> Any:
    emissao = await EmissaoService(session).get(emissao_id)
    return render(
        request,
        "relatorios/resultado.html",
        {"title": emissao.titulo, "emissao": emissao},
    )


@router.get("/relatorios/emissoes/{emissao_id}/status", response_class=HTMLResponse)
async def emissao_status_partial(
    request: Request,
    session: SessionDep,
    emissao_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("relatorios.historico.visualizar"))
    ],
) -> Any:
    emissao = await EmissaoService(session).get(emissao_id)
    return render(
        request,
        "relatorios/_status_partial.html",
        {"emissao": emissao},
    )


@router.get("/relatorios/emissoes/{emissao_id}/download")
async def emissao_download(
    session: SessionDep,
    emissao_id: uuid.UUID,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_web_permission("relatorios.historico.visualizar"))
    ],
):
    blob, ct, filename = await EmissaoService(session).get_download(emissao_id)
    return StreamingResponse(
        iter([blob]),
        media_type=ct,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
