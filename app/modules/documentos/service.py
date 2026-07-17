"""ReportService — motor único de geração de PDF (§16)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, NotFoundError, ValidationError
from app.core.pagination import Page, PageParams
from app.core.storage import storage_service
from app.modules.audit.service import audit_service
from app.modules.documentos.catalog import TEMPLATES_BY_ID
from app.modules.documentos.context_builders import build_context
from app.modules.documentos.models import DocumentoGerado
from app.modules.documentos.pdf_engine import render_pdf, sha256_bytes
from app.shared.enums import AuditAction, DocGeradoStatus
from app.shared.repository import BaseRepository


def _now() -> datetime:
    return datetime.now(tz=UTC)


class DocumentoRepository(BaseRepository[DocumentoGerado]):
    model = DocumentoGerado

    def list_query(self):
        return select(DocumentoGerado).where(DocumentoGerado.deleted_at.is_(None)).order_by(
            DocumentoGerado.created_at.desc()
        )


class ReportService:
    """Interface única: gerar_pdf(template_id, contexto, sincrono)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = DocumentoRepository(session)

    def get_template(self, template_id: str):
        tpl = TEMPLATES_BY_ID.get(template_id)
        if tpl is None:
            raise NotFoundError(f"Template PDF não encontrado: {template_id}")
        return tpl

    async def get(self, doc_id: uuid.UUID) -> DocumentoGerado:
        item = await self.repo.get(doc_id)
        if item is None:
            raise NotFoundError("Documento não encontrado.")
        return item

    async def list_historico(self, page: int = 1, size: int = 25) -> Page[DocumentoGerado]:
        return await self.repo.paginate(PageParams(page=page, size=size))

    async def gerar_pdf(
        self,
        template_id: str,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID | None,
        entidade_id: uuid.UUID,
        filial_id: uuid.UUID | None = None,
        sincrono: bool | None = None,
        extra: dict[str, Any] | None = None,
    ) -> DocumentoGerado:
        tpl = self.get_template(template_id)
        use_sync = tpl.sincrono if sincrono is None else sincrono
        if tpl.pesado and use_sync:
            use_sync = False

        doc = DocumentoGerado(
            tenant_id=tenant_id,
            filial_id=filial_id,
            user_id=user_id,
            template_id=template_id,
            titulo=tpl.titulo,
            familia=tpl.familia,
            entidade_tipo=tpl.entidade_tipo,
            entidade_id=entidade_id,
            status=DocGeradoStatus.PENDENTE,
            sincrono=use_sync,
        )
        self.repo.add(doc)
        await self.session.flush()

        if use_sync:
            await self.processar(doc.id)
        else:
            from app.modules.documentos.tasks import gerar_pdf_task

            gerar_pdf_task.delay(str(doc.id), str(tenant_id))

        await audit_service.record(
            AuditAction.EXPORT,
            entity="documento_gerado",
            entity_id=doc.id,
            description=f"PDF solicitado: {tpl.titulo} ({template_id})",
        )
        return doc

    async def processar(self, doc_id: uuid.UUID, extra: dict[str, Any] | None = None) -> DocumentoGerado:
        doc = await self.get(doc_id)
        if doc.status == DocGeradoStatus.CONCLUIDO:
            return doc

        doc.status = DocGeradoStatus.PROCESSANDO
        doc.iniciado_em = _now()
        await self.session.flush()

        tpl = self.get_template(doc.template_id)
        try:
            if doc.entidade_id is None:
                raise ValidationError("entidade_id obrigatório para este template.")
            ctx = await build_context(
                self.session,
                doc.template_id,
                doc.tenant_id,
                doc.entidade_id,
                extra=extra,
            )
            doc.watermark = ctx.get("watermark")
            blob = render_pdf(tpl.template_path, ctx)
            doc.content_type = "application/pdf"
            doc.tamanho_bytes = len(blob)
            doc.hash_sha256 = sha256_bytes(blob)
            filename = f"{doc.template_id}_{doc.id.hex[:8]}.pdf"

            if storage_service.is_configured():
                key = storage_service.build_key(
                    doc.tenant_id, "pdfs", doc.template_id, filename
                )
                storage_service.upload_bytes(key, blob, doc.content_type)
                doc.storage_key = key
            else:
                doc.conteudo_inline = blob

            doc.status = DocGeradoStatus.CONCLUIDO
            doc.concluido_em = _now()
            if doc.user_id:
                from app.modules.notificacoes.schemas import NotificacaoSendInput
                from app.modules.notificacoes.service import NotificationService
                from app.shared.enums import NotificacaoCanal

                await NotificationService(self.session).send(
                    doc.tenant_id,
                    NotificacaoSendInput(
                        titulo=f"PDF pronto: {doc.titulo}",
                        mensagem=f"O documento «{doc.titulo}» foi gerado com sucesso.",
                        user_id=doc.user_id,
                        link=f"/documentos/{doc.id}/download",
                        canais=[NotificacaoCanal.IN_APP, NotificacaoCanal.EMAIL],
                        evento="documento.concluido",
                        referencia_tipo="documento_gerado",
                        referencia_id=doc.id,
                    ),
                )
        except Exception as exc:
            doc.status = DocGeradoStatus.ERRO
            doc.erro_mensagem = str(exc)
            doc.concluido_em = _now()
            raise BusinessRuleError(f"Falha ao gerar PDF: {exc}") from exc

        return doc

    def resolve_download_url(self, doc: DocumentoGerado) -> str | None:
        if doc.storage_key and storage_service.is_configured():
            return storage_service.generate_presigned_download(doc.storage_key)
        return None

    def get_inline_bytes(self, doc: DocumentoGerado) -> bytes | None:
        if doc.conteudo_inline:
            return bytes(doc.conteudo_inline)
        return None
