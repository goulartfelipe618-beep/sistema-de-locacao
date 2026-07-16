"""Serviços do módulo Automações (§13)."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BusinessRuleError, NotFoundError, ValidationError
from app.core.pagination import Page, PageParams
from app.modules.audit.service import audit_service
from app.modules.automacoes.beat_catalog import get_beat_job, list_beat_jobs
from app.modules.automacoes.engine import RegraEngine
from app.modules.automacoes.models import (
    AutoExecucao,
    AutoRegra,
    AutoWorkflow,
    AutoWorkflowAprovacao,
    AutoWorkflowEtapa,
    AutoWorkflowInstancia,
)
from app.modules.automacoes.schemas import (
    RegraCreate,
    RegraUpdate,
    WorkflowCreate,
    WorkflowDecisaoInput,
    WorkflowEtapaInput,
    WorkflowInstanciaCreate,
)
from app.shared.enums import (
    AuditAction,
    AutoAprovacaoStatus,
    AutoEventoGatilho,
    AutoExecucaoStatus,
    AutoExecucaoTipo,
    AutoWorkflowInstanciaStatus,
    AutoWorkflowTimeoutAcao,
)
from app.shared.repository import BaseRepository


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


class RegraRepository(BaseRepository[AutoRegra]):
    model = AutoRegra

    def list_query(self, *, ativo: bool | None = None):
        stmt = select(AutoRegra).where(AutoRegra.deleted_at.is_(None)).order_by(
            AutoRegra.prioridade, AutoRegra.nome
        )
        if ativo is not None:
            stmt = stmt.where(AutoRegra.ativo.is_(ativo))
        return stmt


class WorkflowRepository(BaseRepository[AutoWorkflow]):
    model = AutoWorkflow

    def list_query(self):
        return (
            select(AutoWorkflow)
            .where(AutoWorkflow.deleted_at.is_(None))
            .options(selectinload(AutoWorkflow.etapas))
            .order_by(AutoWorkflow.nome)
        )

    async def get_by_codigo(self, codigo: str) -> AutoWorkflow | None:
        stmt = (
            select(AutoWorkflow)
            .where(
                AutoWorkflow.codigo == codigo,
                AutoWorkflow.deleted_at.is_(None),
            )
            .options(selectinload(AutoWorkflow.etapas))
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()


class ExecucaoRepository(BaseRepository[AutoExecucao]):
    model = AutoExecucao

    def list_query(self, *, tipo: AutoExecucaoTipo | None = None):
        stmt = (
            select(AutoExecucao)
            .where(AutoExecucao.deleted_at.is_(None))
            .order_by(AutoExecucao.created_at.desc())
        )
        if tipo:
            stmt = stmt.where(AutoExecucao.tipo == tipo)
        return stmt


class ExecucaoService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ExecucaoRepository(session)

    async def list_items(
        self, params: PageParams, *, tipo: AutoExecucaoTipo | None = None
    ) -> Page[AutoExecucao]:
        return await self.repo.paginate(params, stmt=self.repo.list_query(tipo=tipo))

    async def registrar(
        self,
        tenant_id: uuid.UUID,
        *,
        tipo: AutoExecucaoTipo,
        referencia_id: uuid.UUID | None = None,
        referencia_codigo: str | None = None,
        evento: str | None = None,
        payload: dict | None = None,
    ) -> AutoExecucao:
        item = AutoExecucao(
            tenant_id=tenant_id,
            tipo=tipo,
            referencia_id=referencia_id,
            referencia_codigo=referencia_codigo,
            evento=evento,
            status=AutoExecucaoStatus.PENDENTE,
            payload_json=_json_dumps(payload or {}),
            iniciado_em=_now(),
        )
        self.repo.add(item)
        await self.repo.flush()
        return item

    async def concluir(
        self,
        execucao: AutoExecucao,
        *,
        status: AutoExecucaoStatus,
        resultado: dict | None = None,
        erro: str | None = None,
        iniciado: datetime | None = None,
    ) -> AutoExecucao:
        fim = _now()
        execucao.status = status
        execucao.resultado_json = _json_dumps(resultado) if resultado else None
        execucao.erro_mensagem = erro[:2000] if erro else None
        execucao.concluido_em = fim
        if iniciado:
            execucao.duracao_ms = int((fim - iniciado).total_seconds() * 1000)
        await self.repo.flush()
        return execucao


class RegraService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = RegraRepository(session)
        self.execucoes = ExecucaoService(session)
        self.engine = RegraEngine(session)

    async def list_items(self, params: PageParams) -> Page[AutoRegra]:
        return await self.repo.paginate(params, stmt=self.repo.list_query())

    async def get(self, regra_id: uuid.UUID) -> AutoRegra:
        item = await self.repo.get(regra_id)
        if item is None:
            raise NotFoundError("Regra não encontrada.")
        return item

    async def create(self, tenant_id: uuid.UUID, data: RegraCreate) -> AutoRegra:
        item = AutoRegra(
            tenant_id=tenant_id,
            nome=data.nome,
            descricao=data.descricao,
            evento_gatilho=data.evento_gatilho,
            condicao_json=_json_dumps(data.condicao_json),
            acao_tipo=data.acao_tipo,
            acao_params_json=_json_dumps(data.acao_params_json),
            prioridade=data.prioridade,
            ativo=data.ativo,
        )
        self.repo.add(item)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="auto_regra",
            entity_id=item.id,
            description=f"Regra criada: {item.nome}",
        )
        return item

    async def update(self, regra_id: uuid.UUID, data: RegraUpdate) -> AutoRegra:
        item = await self.get(regra_id)
        if data.nome is not None:
            item.nome = data.nome
        if data.descricao is not None:
            item.descricao = data.descricao
        if data.condicao_json is not None:
            item.condicao_json = _json_dumps(data.condicao_json)
        if data.acao_tipo is not None:
            item.acao_tipo = data.acao_tipo
        if data.acao_params_json is not None:
            item.acao_params_json = _json_dumps(data.acao_params_json)
        if data.prioridade is not None:
            item.prioridade = data.prioridade
        if data.ativo is not None:
            item.ativo = data.ativo
        await self.repo.flush()
        return item

    async def delete(self, regra_id: uuid.UUID) -> None:
        item = await self.get(regra_id)
        await self.repo.delete(item)

    async def executar_manual(
        self, tenant_id: uuid.UUID, regra_id: uuid.UUID, context: dict[str, Any]
    ) -> AutoExecucao:
        regra = await self.get(regra_id)
        execucao = await self.execucoes.registrar(
            tenant_id,
            tipo=AutoExecucaoTipo.REGRA,
            referencia_id=regra.id,
            referencia_codigo=regra.nome,
            evento=AutoEventoGatilho.MANUAL.value,
            payload=context,
        )
        t0 = _now()
        try:
            resultados = await self.engine.dispatch(
                tenant_id, regra.evento_gatilho, context, regras=[regra]
            )
            await self.execucoes.concluir(
                execucao,
                status=AutoExecucaoStatus.SUCESSO if resultados else AutoExecucaoStatus.IGNORADO,
                resultado={"resultados": resultados},
                iniciado=t0,
            )
        except Exception as exc:  # noqa: BLE001
            await self.execucoes.concluir(
                execucao, status=AutoExecucaoStatus.ERRO, erro=str(exc), iniciado=t0
            )
        return execucao

    async def _avaliar_evento(
        self,
        tenant_id: uuid.UUID,
        evento: AutoEventoGatilho,
        context: dict[str, Any],
        *,
        referencia_id: uuid.UUID | None = None,
    ) -> bool:
        execucao = await self.execucoes.registrar(
            tenant_id,
            tipo=AutoExecucaoTipo.REGRA,
            referencia_id=referencia_id,
            evento=evento.value,
            payload=context,
        )
        t0 = _now()
        try:
            res = await self.engine.dispatch(tenant_id, evento, context)
            await self.execucoes.concluir(
                execucao,
                status=AutoExecucaoStatus.SUCESSO if res else AutoExecucaoStatus.IGNORADO,
                resultado={"disparos": len(res)},
                iniciado=t0,
            )
            return bool(res)
        except Exception as exc:  # noqa: BLE001
            await self.execucoes.concluir(
                execucao, status=AutoExecucaoStatus.ERRO, erro=str(exc), iniciado=t0
            )
            return False

    async def avaliar_periodicas(self, tenant_id: uuid.UUID) -> int:
        """Avalia gatilhos temporais (títulos, documentação, estoque)."""
        from datetime import date, timedelta

        from app.modules.frota.models import FrotaAcessorio, FrotaDocumento
        from app.modules.financeiro.models import FinContaReceber
        from app.modules.parametros.service import ParametroService
        from app.shared.enums import TituloStatus

        count = 0

        stmt = select(FinContaReceber).where(
            FinContaReceber.tenant_id == tenant_id,
            FinContaReceber.deleted_at.is_(None),
            FinContaReceber.status == TituloStatus.VENCIDO,
        ).limit(50)
        titulos = list((await self.session.execute(stmt)).scalars().all())
        clientes_inad: set[str] = set()
        for t in titulos:
            dias = (_now().date() - t.vencimento).days
            ctx = {
                "titulo_id": str(t.id),
                "dias_vencido": dias,
                "cliente_id": str(t.cliente_id) if t.cliente_id else None,
                "filial_id": str(t.filial_id),
                "valor": float(t.valor_saldo),
            }
            if await self._avaliar_evento(
                tenant_id, AutoEventoGatilho.TITULO_VENCIDO, ctx, referencia_id=t.id
            ):
                count += 1
            if t.cliente_id and dias >= 30:
                cid = str(t.cliente_id)
                if cid not in clientes_inad:
                    clientes_inad.add(cid)
                    if await self._avaliar_evento(
                        tenant_id,
                        AutoEventoGatilho.CLIENTE_INADIMPLENTE,
                        {**ctx, "cliente_id": cid},
                        referencia_id=t.cliente_id,
                    ):
                        count += 1

        try:
            dias_raw = await ParametroService(self.session).get_valor(
                "automacoes.dias_alerta_documento", tenant_id
            )
            alerta_dias = max(int(x.strip()) for x in str(dias_raw).split(",") if x.strip())
        except (ValueError, TypeError):
            alerta_dias = 30

        limite_doc = date.today() + timedelta(days=alerta_dias)
        docs = list(
            (
                await self.session.execute(
                    select(FrotaDocumento).where(
                        FrotaDocumento.tenant_id == tenant_id,
                        FrotaDocumento.deleted_at.is_(None),
                        FrotaDocumento.data_validade.is_not(None),
                        FrotaDocumento.data_validade <= limite_doc,
                    ).limit(50)
                )
            )
            .scalars()
            .all()
        )
        for d in docs:
            dias_para = (d.data_validade - date.today()).days if d.data_validade else 0
            if await self._avaliar_evento(
                tenant_id,
                AutoEventoGatilho.DOCUMENTO_VENCER,
                {
                    "documento_id": str(d.id),
                    "veiculo_id": str(d.veiculo_id),
                    "tipo": d.tipo.value,
                    "dias_para_vencer": dias_para,
                },
                referencia_id=d.id,
            ):
                count += 1

        acessorios = list(
            (
                await self.session.execute(
                    select(FrotaAcessorio).where(
                        FrotaAcessorio.tenant_id == tenant_id,
                        FrotaAcessorio.deleted_at.is_(None),
                        FrotaAcessorio.estoque_disponivel <= 0,
                    ).limit(50)
                )
            )
            .scalars()
            .all()
        )
        for a in acessorios:
            if await self._avaliar_evento(
                tenant_id,
                AutoEventoGatilho.ESTOQUE_MINIMO,
                {
                    "acessorio_id": str(a.id),
                    "nome": a.nome,
                    "estoque_disponivel": a.estoque_disponivel,
                },
                referencia_id=a.id,
            ):
                count += 1

        return count


class InstanciaRepository(BaseRepository[AutoWorkflowInstancia]):
    model = AutoWorkflowInstancia


class WorkflowService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = WorkflowRepository(session)
        self.execucoes = ExecucaoService(session)

    async def list_items(self, params: PageParams) -> Page[AutoWorkflow]:
        return await self.repo.paginate(params, stmt=self.repo.list_query())

    async def get(self, workflow_id: uuid.UUID) -> AutoWorkflow:
        stmt = (
            select(AutoWorkflow)
            .where(AutoWorkflow.id == workflow_id, AutoWorkflow.deleted_at.is_(None))
            .options(selectinload(AutoWorkflow.etapas))
        )
        item = (await self.session.execute(stmt)).scalar_one_or_none()
        if item is None:
            raise NotFoundError("Workflow não encontrado.")
        return item

    async def create(self, tenant_id: uuid.UUID, data: WorkflowCreate) -> AutoWorkflow:
        if await self.repo.get_by_codigo(data.codigo):
            raise ValidationError("Código de workflow já existe.")
        wf = AutoWorkflow(
            tenant_id=tenant_id,
            codigo=data.codigo,
            nome=data.nome,
            descricao=data.descricao,
        )
        self.repo.add(wf)
        await self.repo.flush()
        for etapa in sorted(data.etapas, key=lambda e: e.ordem):
            self._add_etapa(tenant_id, wf.id, etapa)
        await self.repo.flush()
        return await self.get(wf.id)

    def _add_etapa(
        self, tenant_id: uuid.UUID, workflow_id: uuid.UUID, data: WorkflowEtapaInput
    ) -> AutoWorkflowEtapa:
        etapa = AutoWorkflowEtapa(
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            ordem=data.ordem,
            nome=data.nome,
            aprovador_papel_slug=data.aprovador_papel_slug,
            aprovador_user_id=data.aprovador_user_id,
            sla_horas=data.sla_horas,
            timeout_acao=data.timeout_acao,
        )
        self.session.add(etapa)
        return etapa

    async def iniciar(
        self, tenant_id: uuid.UUID, data: WorkflowInstanciaCreate
    ) -> AutoWorkflowInstancia:
        wf = await self.repo.get_by_codigo(data.workflow_codigo)
        if wf is None or not wf.ativo:
            raise BusinessRuleError("Workflow não encontrado ou inativo.")
        etapas = sorted(wf.etapas, key=lambda e: e.ordem)
        if not etapas:
            raise ValidationError("Workflow sem etapas.")
        primeira = etapas[0]
        inst = AutoWorkflowInstancia(
            tenant_id=tenant_id,
            workflow_id=wf.id,
            etapa_atual_id=primeira.id,
            entidade_tipo=data.entidade_tipo,
            entidade_id=data.entidade_id,
            status=AutoWorkflowInstanciaStatus.EM_ANDAMENTO,
            contexto_json=_json_dumps(data.contexto),
            iniciado_em=_now(),
            etapa_vence_em=_now() + timedelta(hours=primeira.sla_horas),
        )
        self.session.add(inst)
        await self.session.flush()
        aprov = AutoWorkflowAprovacao(
            tenant_id=tenant_id,
            instancia_id=inst.id,
            etapa_id=primeira.id,
            status=AutoAprovacaoStatus.PENDENTE,
        )
        self.session.add(aprov)
        await self.session.flush()
        await self.execucoes.registrar(
            tenant_id,
            tipo=AutoExecucaoTipo.WORKFLOW,
            referencia_id=inst.id,
            referencia_codigo=wf.codigo,
            evento="iniciado",
            payload=data.contexto,
        )
        return inst

    async def list_instancias(
        self, params: PageParams, *, status: AutoWorkflowInstanciaStatus | None = None
    ) -> Page[AutoWorkflowInstancia]:
        stmt = select(AutoWorkflowInstancia).where(AutoWorkflowInstancia.deleted_at.is_(None))
        if status:
            stmt = stmt.where(AutoWorkflowInstancia.status == status)
        stmt = stmt.order_by(AutoWorkflowInstancia.created_at.desc())
        return await InstanciaRepository(self.session).paginate(params, stmt=stmt)

    async def get_instancia(self, instancia_id: uuid.UUID) -> AutoWorkflowInstancia:
        stmt = select(AutoWorkflowInstancia).where(
            AutoWorkflowInstancia.id == instancia_id,
            AutoWorkflowInstancia.deleted_at.is_(None),
        )
        item = (await self.session.execute(stmt)).scalar_one_or_none()
        if item is None:
            raise NotFoundError("Instância de workflow não encontrada.")
        return item

    async def decidir(
        self,
        instancia_id: uuid.UUID,
        user_id: uuid.UUID,
        data: WorkflowDecisaoInput,
    ) -> AutoWorkflowInstancia:
        inst = await self.get_instancia(instancia_id)
        if inst.status not in {
            AutoWorkflowInstanciaStatus.PENDENTE,
            AutoWorkflowInstanciaStatus.EM_ANDAMENTO,
        }:
            raise BusinessRuleError("Workflow já finalizado.")

        stmt = select(AutoWorkflowAprovacao).where(
            AutoWorkflowAprovacao.instancia_id == inst.id,
            AutoWorkflowAprovacao.etapa_id == inst.etapa_atual_id,
            AutoWorkflowAprovacao.status == AutoAprovacaoStatus.PENDENTE,
        )
        aprov = (await self.session.execute(stmt)).scalar_one_or_none()
        if aprov is None:
            raise BusinessRuleError("Nenhuma aprovação pendente.")

        aprov.user_id = user_id
        aprov.comentario = data.comentario
        aprov.decidido_em = _now()
        aprov.status = (
            AutoAprovacaoStatus.APROVADO if data.aprovar else AutoAprovacaoStatus.REJEITADO
        )

        if not data.aprovar:
            inst.status = AutoWorkflowInstanciaStatus.REJEITADO
            inst.concluido_em = _now()
            await self.session.flush()
            return inst

        wf = await self.get(inst.workflow_id)
        etapas = sorted(wf.etapas, key=lambda e: e.ordem)
        idx = next(i for i, e in enumerate(etapas) if e.id == inst.etapa_atual_id)
        if idx + 1 >= len(etapas):
            inst.status = AutoWorkflowInstanciaStatus.APROVADO
            inst.concluido_em = _now()
            inst.etapa_atual_id = None
            inst.etapa_vence_em = None
        else:
            prox = etapas[idx + 1]
            inst.etapa_atual_id = prox.id
            inst.etapa_vence_em = _now() + timedelta(hours=prox.sla_horas)
            self.session.add(
                AutoWorkflowAprovacao(
                    tenant_id=inst.tenant_id,
                    instancia_id=inst.id,
                    etapa_id=prox.id,
                    status=AutoAprovacaoStatus.PENDENTE,
                )
            )
        await self.session.flush()
        return inst

    async def processar_timeouts(self, tenant_id: uuid.UUID) -> int:
        now = _now()
        stmt = select(AutoWorkflowInstancia).where(
            AutoWorkflowInstancia.tenant_id == tenant_id,
            AutoWorkflowInstancia.status == AutoWorkflowInstanciaStatus.EM_ANDAMENTO,
            AutoWorkflowInstancia.etapa_vence_em <= now,
            AutoWorkflowInstancia.deleted_at.is_(None),
        )
        instancias = list((await self.session.execute(stmt)).scalars().all())
        count = 0
        for inst in instancias:
            wf = await self.get(inst.workflow_id)
            etapa = next((e for e in wf.etapas if e.id == inst.etapa_atual_id), None)
            if etapa is None:
                continue
            if etapa.timeout_acao == AutoWorkflowTimeoutAcao.REJEITAR_AUTO:
                inst.status = AutoWorkflowInstanciaStatus.EXPIRADO
                inst.concluido_em = now
            elif etapa.timeout_acao == AutoWorkflowTimeoutAcao.APROVAR_AUTO:
                await self.decidir(
                    inst.id,
                    user_id=inst.tenant_id,
                    data=WorkflowDecisaoInput(
                        aprovar=True, comentario="Aprovação automática por SLA"
                    ),
                )
            else:
                inst.etapa_vence_em = now + timedelta(hours=etapa.sla_horas)
            count += 1
        await self.session.flush()
        return count


class BeatAdminService:
    """Gestão administrativa dos jobs Celery Beat (§13.3)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.execucoes = ExecucaoService(session)

    def catalogo(self) -> list[dict]:
        return list_beat_jobs()

    async def ultima_execucao(self, tenant_id: uuid.UUID, job_key: str) -> AutoExecucao | None:
        stmt = (
            select(AutoExecucao)
            .where(
                AutoExecucao.tenant_id == tenant_id,
                AutoExecucao.tipo == AutoExecucaoTipo.BEAT,
                AutoExecucao.referencia_codigo == job_key,
                AutoExecucao.deleted_at.is_(None),
            )
            .order_by(AutoExecucao.created_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def disparar(self, tenant_id: uuid.UUID, job_key: str) -> AutoExecucao:
        job = get_beat_job(job_key)
        if job is None:
            raise NotFoundError("Job Beat não encontrado.")
        execucao = await self.execucoes.registrar(
            tenant_id,
            tipo=AutoExecucaoTipo.BEAT,
            referencia_codigo=job_key,
            evento=job["task"],
            payload={"manual": True},
        )
        t0 = _now()
        try:
            from app.workers.celery_app import celery_app

            celery_app.send_task(
                job["task"],
                queue=job.get("queue", "default"),
            )
            await self.execucoes.concluir(
                execucao,
                status=AutoExecucaoStatus.SUCESSO,
                resultado={"enfileirado": True, "task": job["task"]},
                iniciado=t0,
            )
        except Exception as exc:  # noqa: BLE001
            await self.execucoes.concluir(
                execucao, status=AutoExecucaoStatus.ERRO, erro=str(exc), iniciado=t0
            )
        return execucao

    @staticmethod
    async def log_beat_conclusao(
        session: AsyncSession,
        tenant_id: uuid.UUID,
        task_name: str,
        *,
        sucesso: bool,
        resultado: dict | None = None,
        erro: str | None = None,
        duracao_ms: int | None = None,
    ) -> None:
        key = task_name
        for job in list_beat_jobs():
            if job["task"] == task_name:
                key = job["key"]
                break
        svc = ExecucaoService(session)
        execucao = await svc.registrar(
            tenant_id,
            tipo=AutoExecucaoTipo.BEAT,
            referencia_codigo=key,
            evento=task_name,
        )
        await svc.concluir(
            execucao,
            status=AutoExecucaoStatus.SUCESSO if sucesso else AutoExecucaoStatus.ERRO,
            resultado=resultado,
            erro=erro,
            iniciado=_now() - timedelta(milliseconds=duracao_ms or 0),
        )
