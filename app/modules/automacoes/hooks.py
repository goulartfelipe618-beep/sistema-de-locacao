"""Ganchos de integração — dispara regras/workflows a partir de outros módulos (§13)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.automacoes.engine import RegraEngine
from app.modules.automacoes.schemas import WorkflowInstanciaCreate
from app.modules.automacoes.service import ExecucaoService, WorkflowService
from app.shared.enums import AutoEventoGatilho, AutoExecucaoStatus, AutoExecucaoTipo

logger = get_logger(__name__)


def _now() -> datetime:
    return datetime.now(tz=UTC)


async def fire_regra_event(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    evento: AutoEventoGatilho,
    context: dict[str, Any],
) -> None:
    """Dispara regras para um evento de negócio (não interrompe fluxo em erro)."""
    exec_svc = ExecucaoService(session)
    t0 = _now()
    execucao = await exec_svc.registrar(
        tenant_id,
        tipo=AutoExecucaoTipo.REGRA,
        evento=evento.value,
        payload=context,
    )
    try:
        resultados = await RegraEngine(session).dispatch(tenant_id, evento, context)
        await exec_svc.concluir(
            execucao,
            status=AutoExecucaoStatus.SUCESSO if resultados else AutoExecucaoStatus.IGNORADO,
            resultado={"disparos": len(resultados), "resultados": resultados},
            iniciado=t0,
        )
    except Exception as exc:  # noqa: BLE001
        await exec_svc.concluir(
            execucao, status=AutoExecucaoStatus.ERRO, erro=str(exc), iniciado=t0
        )
        logger.exception("Falha ao disparar regras para %s", evento.value)


async def try_start_workflow(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    workflow_codigo: str,
    entidade_tipo: str,
    entidade_id: uuid.UUID,
    contexto: dict[str, Any] | None = None,
) -> None:
    """Inicia workflow se configurado; ignora silenciosamente se inexistente."""
    try:
        await WorkflowService(session).iniciar(
            tenant_id,
            WorkflowInstanciaCreate(
                workflow_codigo=workflow_codigo,
                entidade_tipo=entidade_tipo,
                entidade_id=entidade_id,
                contexto=contexto or {},
            ),
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("Workflow %s não iniciado: %s", workflow_codigo, exc)
