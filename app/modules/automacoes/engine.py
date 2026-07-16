"""Motor de avaliação de condições JSON e execução de ações (§13.1)."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.service import audit_service
from app.modules.automacoes.models import AutoRegra
from app.shared.enums import AuditAction, AutoAcaoTipo, AutoEventoGatilho


def _get_field(context: dict[str, Any], field: str) -> Any:
    parts = field.split(".")
    cur: Any = context
    for p in parts:
        if isinstance(cur, dict):
            cur = cur.get(p)
        else:
            return None
    return cur


def evaluate_condition(cond: dict[str, Any], context: dict[str, Any]) -> bool:
    """Avalia condição JSON simples (eq, gt, gte, lt, lte, and, or, always)."""
    if not cond or cond.get("op") == "always":
        return True
    op = cond.get("op")
    if op == "and":
        return all(evaluate_condition(c, context) for c in cond.get("conditions", []))
    if op == "or":
        return any(evaluate_condition(c, context) for c in cond.get("conditions", []))
    field = cond.get("field", "")
    value = cond.get("value")
    actual = _get_field(context, field)
    if op == "eq":
        return actual == value
    if op == "neq":
        return actual != value
    if op == "gt":
        return actual is not None and actual > value
    if op == "gte":
        return actual is not None and actual >= value
    if op == "lt":
        return actual is not None and actual < value
    if op == "lte":
        return actual is not None and actual <= value
    if op == "contains":
        return value in str(actual or "")
    return False


def parse_json(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


class AcaoExecutor:
    """Executa ações de regras contra o contexto informado."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def executar(
        self,
        acao: AutoAcaoTipo,
        params: dict[str, Any],
        context: dict[str, Any],
        *,
        tenant_id: uuid.UUID,
    ) -> dict[str, Any]:
        if acao == AutoAcaoTipo.NOTIFICAR:
            msg = params.get("mensagem") or context.get("mensagem") or "Alerta de automação"
            await audit_service.record(
                AuditAction.UPDATE,
                description=f"[Automação] Notificação: {msg}",
                changes={"contexto": context},
            )
            return {"notificado": True, "mensagem": msg}

        if acao == AutoAcaoTipo.REGISTRAR_ALERTA:
            msg = params.get("mensagem", "Alerta registrado")
            await audit_service.record(
                AuditAction.UPDATE,
                description=f"[Automação] Alerta: {msg}",
                changes=context,
            )
            return {"alerta": msg}

        if acao == AutoAcaoTipo.BLOQUEAR_CLIENTE:
            cliente_id = context.get("cliente_id") or params.get("cliente_id")
            if not cliente_id:
                return {"skipped": True, "reason": "cliente_id ausente"}
            from app.modules.cadastros.service import ClienteService

            cliente = await ClienteService(self.session).get(uuid.UUID(str(cliente_id)))
            motivo = params.get("motivo") or "Bloqueio automático por regra"
            cliente.blacklist = True
            cliente.motivo_bloqueio = motivo
            await self.session.flush()
            return {"cliente_id": str(cliente.id), "bloqueado": True}

        if acao == AutoAcaoTipo.BLOQUEAR_VEICULO:
            veiculo_id = context.get("veiculo_id") or params.get("veiculo_id")
            if not veiculo_id:
                return {"skipped": True, "reason": "veiculo_id ausente"}
            from app.modules.frota.service import VeiculoService
            from app.shared.enums import VeiculoStatus

            veiculo = await VeiculoService(self.session).get(uuid.UUID(str(veiculo_id)))
            veiculo.status = VeiculoStatus.BLOQUEADO
            await self.session.flush()
            return {"veiculo_id": str(veiculo.id), "bloqueado": True}

        if acao == AutoAcaoTipo.GERAR_COBRANCA:
            return {"simulado": True, "mensagem": "Cobrança enfileirada (integração financeiro)"}

        if acao == AutoAcaoTipo.GERAR_OS:
            return {"simulado": True, "mensagem": "OS enfileirada (integração manutenção)"}

        return {"skipped": True}


class RegraEngine:
    """Dispara regras ativas para um evento."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.executor = AcaoExecutor(session)

    async def dispatch(
        self,
        tenant_id: uuid.UUID,
        evento: AutoEventoGatilho,
        context: dict[str, Any],
        *,
        regras: list[AutoRegra] | None = None,
    ) -> list[dict[str, Any]]:
        if regras is None:
            from sqlalchemy import select

            stmt = (
                select(AutoRegra)
                .where(
                    AutoRegra.tenant_id == tenant_id,
                    AutoRegra.evento_gatilho == evento,
                    AutoRegra.ativo.is_(True),
                    AutoRegra.deleted_at.is_(None),
                )
                .order_by(AutoRegra.prioridade)
            )
            regras = list((await self.session.execute(stmt)).scalars().all())

        resultados: list[dict[str, Any]] = []
        for regra in regras:
            cond = parse_json(regra.condicao_json)
            if not evaluate_condition(cond, context):
                continue
            params = parse_json(regra.acao_params_json)
            try:
                out = await self.executor.executar(
                    regra.acao_tipo, params, context, tenant_id=tenant_id
                )
                regra.ultima_execucao_em = datetime.now(tz=UTC)
                resultados.append({"regra_id": str(regra.id), "ok": True, "resultado": out})
            except Exception as exc:  # noqa: BLE001
                resultados.append({"regra_id": str(regra.id), "ok": False, "erro": str(exc)})
        await self.session.flush()
        return resultados
