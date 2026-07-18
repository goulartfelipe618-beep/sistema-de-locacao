"""Serviço de emissão e agendamento de relatórios (§11)."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, ValidationError
from app.core.pagination import Page, PageParams
from app.core.storage import storage_service
from app.modules.audit.service import audit_service
from app.modules.relatorios.catalog import get_report
from app.modules.relatorios.engine import (
    CONTENT_TYPES,
    render_csv,
    render_pdf_html,
    render_xlsx,
    sha256_bytes,
)
from app.modules.relatorios.generators import gerar
from app.modules.relatorios.models import RelAgendamento, RelEmissao
from app.shared.enums import AuditAction, RelCategoria, RelEmissaoStatus, RelFormato, RelRecorrencia
from app.shared.repository import BaseRepository

CACHE_DAYS = 7


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _params_hash(codigo: str, formato: str, params: dict[str, Any]) -> str:
    payload = json.dumps({"codigo": codigo, "formato": formato, "params": params}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


class EmissaoRepository(BaseRepository[RelEmissao]):
    model = RelEmissao

    def list_query(self):
        return select(RelEmissao).where(RelEmissao.deleted_at.is_(None)).order_by(
            RelEmissao.created_at.desc()
        )


class AgendamentoRepository(BaseRepository[RelAgendamento]):
    model = RelAgendamento

    def list_query(self):
        return select(RelAgendamento).where(RelAgendamento.deleted_at.is_(None)).order_by(
            RelAgendamento.nome
        )


class EmissaoService:
    """Orquestra geração síncrona/assíncrona e histórico de emissões."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = EmissaoRepository(session)

    async def get(self, emissao_id: uuid.UUID) -> RelEmissao:
        item = await self.repo.get(emissao_id)
        if item is None:
            raise BusinessRuleError("Emissão não encontrada.")
        return item

    async def list_historico(
        self,
        *,
        categoria: RelCategoria | None = None,
        page: int = 1,
        size: int = 25,
    ) -> Page[RelEmissao]:
        stmt = self.repo.list_query()
        if categoria:
            stmt = stmt.where(RelEmissao.categoria == categoria)
        return await self.repo.paginate(PageParams(page=page, size=size), stmt=stmt)

    async def find_cache(
        self,
        tenant_id: uuid.UUID,
        codigo: str,
        formato: RelFormato,
        params: dict[str, Any],
    ) -> RelEmissao | None:
        ph = _params_hash(codigo, formato.value, params)
        stmt = (
            select(RelEmissao)
            .where(
                RelEmissao.tenant_id == tenant_id,
                RelEmissao.relatorio_codigo == codigo,
                RelEmissao.formato == formato,
                RelEmissao.hash_sha256 == ph,
                RelEmissao.status == RelEmissaoStatus.CONCLUIDO,
                RelEmissao.cache_valido_ate > _now(),
                RelEmissao.deleted_at.is_(None),
            )
            .order_by(RelEmissao.concluido_em.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def solicitar(
        self,
        tenant_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None,
        categoria: RelCategoria,
        relatorio_codigo: str,
        formato: RelFormato,
        params: dict[str, Any],
        usar_cache: bool = True,
        forcar_async: bool = False,
    ) -> RelEmissao:
        report = get_report(relatorio_codigo)
        if report is None or report.categoria != categoria:
            raise ValidationError("Relatório inválido para a categoria informada.")

        if usar_cache:
            cached = await self.find_cache(tenant_id, relatorio_codigo, formato, params)
            if cached:
                return cached

        pesado = report.pesado or forcar_async
        emissao = RelEmissao(
            tenant_id=tenant_id,
            user_id=user_id,
            categoria=categoria,
            relatorio_codigo=relatorio_codigo,
            titulo=report.titulo,
            parametros_json=json.dumps(params, ensure_ascii=False, default=str),
            formato=formato,
            status=RelEmissaoStatus.PENDENTE,
            pesado=pesado,
            hash_sha256=_params_hash(relatorio_codigo, formato.value, params),
        )
        self.repo.add(emissao)
        await self.session.flush()

        if pesado:
            from app.modules.relatorios.tasks import processar_emissao_task

            processar_emissao_task.delay(str(emissao.id), str(tenant_id))
        else:
            await self.processar(emissao.id)

        await audit_service.record(
            AuditAction.EXPORT,
            entity="rel_emissao",
            entity_id=emissao.id,
            description=f"Relatório solicitado: {report.titulo} ({formato.value})",
        )
        return emissao

    async def processar(self, emissao_id: uuid.UUID) -> RelEmissao:
        emissao = await self.get(emissao_id)
        if emissao.status == RelEmissaoStatus.CONCLUIDO:
            return emissao

        emissao.status = RelEmissaoStatus.PROCESSANDO
        emissao.iniciado_em = _now()
        await self.session.flush()

        try:
            params = json.loads(emissao.parametros_json or "{}")
            data = await gerar(self.session, emissao.relatorio_codigo, params)
            fmt = emissao.formato.value
            if fmt == "csv":
                blob = render_csv(data.columns, data.rows)
            elif fmt == "xlsx":
                blob = render_xlsx(data.columns, data.rows)
            else:
                from app.modules.documentos.context_builders import build_empresa_pdf_context

                empresa = await build_empresa_pdf_context(self.session, emissao.tenant_id)
                blob = render_pdf_html(
                    data.titulo,
                    data.columns,
                    data.rows,
                    data.summary,
                    empresa=empresa,
                )

            emissao.content_type = CONTENT_TYPES.get(fmt, "application/octet-stream")
            emissao.tamanho_bytes = len(blob)
            emissao.linhas_count = len(data.rows)
            filename = f"{emissao.relatorio_codigo}_{emissao.id.hex[:8]}.{fmt}"

            if storage_service.is_configured():
                key = storage_service.build_key(
                    emissao.tenant_id, "relatorios", emissao.relatorio_codigo, filename
                )
                storage_service.upload_bytes(key, blob, emissao.content_type)
                emissao.storage_key = key
                emissao.conteudo_inline = None
            else:
                emissao.conteudo_inline = blob
                emissao.storage_key = None

            emissao.status = RelEmissaoStatus.CONCLUIDO
            emissao.concluido_em = _now()
            emissao.cache_valido_ate = _now() + timedelta(days=CACHE_DAYS)
            emissao.erro_mensagem = None
        except Exception as exc:  # noqa: BLE001
            emissao.status = RelEmissaoStatus.ERRO
            emissao.erro_mensagem = str(exc)[:2000]
            emissao.concluido_em = _now()

        await self.session.flush()
        return emissao

    async def get_download(self, emissao_id: uuid.UUID) -> tuple[bytes, str, str]:
        emissao = await self.get(emissao_id)
        if emissao.status != RelEmissaoStatus.CONCLUIDO:
            raise BusinessRuleError("Relatório ainda não está pronto para download.")
        ct = emissao.content_type or "application/octet-stream"
        ext = emissao.formato.value
        filename = f"{emissao.relatorio_codigo}.{ext}"
        if emissao.conteudo_inline:
            return emissao.conteudo_inline, ct, filename
        if emissao.storage_key and storage_service.is_configured():
            import boto3
            from app.core.config import settings

            client = boto3.client(
                "s3",
                endpoint_url=settings.r2_endpoint_url,
                aws_access_key_id=settings.r2_access_key_id,
                aws_secret_access_key=settings.r2_secret_access_key,
                region_name="auto",
            )
            obj = client.get_object(Bucket=settings.r2_bucket, Key=emissao.storage_key)
            return obj["Body"].read(), ct, filename
        raise BusinessRuleError("Arquivo do relatório não disponível.")


class AgendamentoService:
    """Agendamentos recorrentes de relatórios (§11)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AgendamentoRepository(session)
        self.emissao_svc = EmissaoService(session)

    async def list_items(self, page: int = 1, size: int = 50) -> Page[RelAgendamento]:
        return await self.repo.paginate(PageParams(page=page, size=size), stmt=self.repo.list_query())

    async def create(
        self,
        tenant_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None,
        nome: str,
        categoria: RelCategoria,
        relatorio_codigo: str,
        formato: RelFormato,
        parametros: dict[str, Any],
        recorrencia: RelRecorrencia,
        hora_execucao: str = "08:00",
        dia_semana: int | None = None,
        dia_mes: int | None = None,
        email_destinatarios: str | None = None,
    ) -> RelAgendamento:
        if get_report(relatorio_codigo) is None:
            raise ValidationError("Relatório inválido.")
        item = RelAgendamento(
            tenant_id=tenant_id,
            user_id=user_id,
            nome=nome,
            categoria=categoria,
            relatorio_codigo=relatorio_codigo,
            parametros_json=json.dumps(parametros, ensure_ascii=False, default=str),
            formato=formato,
            recorrencia=recorrencia,
            hora_execucao=hora_execucao,
            dia_semana=dia_semana,
            dia_mes=dia_mes,
            email_destinatarios=email_destinatarios,
            proxima_execucao_em=_now() + timedelta(days=1),
        )
        self.repo.add(item)
        await self.session.flush()
        return item

    async def processar_vencidos(self, tenant_id: uuid.UUID) -> int:
        now = _now()
        stmt = select(RelAgendamento).where(
            RelAgendamento.tenant_id == tenant_id,
            RelAgendamento.ativo.is_(True),
            RelAgendamento.deleted_at.is_(None),
            RelAgendamento.proxima_execucao_em <= now,
        )
        items = list((await self.session.execute(stmt)).scalars().all())
        count = 0
        for ag in items:
            params = json.loads(ag.parametros_json or "{}")
            emissao = await self.emissao_svc.solicitar(
                tenant_id,
                user_id=ag.user_id,
                categoria=ag.categoria,
                relatorio_codigo=ag.relatorio_codigo,
                formato=ag.formato,
                params=params,
                usar_cache=True,
            )
            ag.ultima_execucao_em = now
            ag.ultima_emissao_id = emissao.id
            if ag.recorrencia == RelRecorrencia.DIARIA:
                ag.proxima_execucao_em = now + timedelta(days=1)
            elif ag.recorrencia == RelRecorrencia.SEMANAL:
                ag.proxima_execucao_em = now + timedelta(days=7)
            else:
                ag.proxima_execucao_em = now + timedelta(days=30)
            count += 1
        await self.session.flush()
        return count
