"""Upload e consulta de documentos do cliente."""

from __future__ import annotations

import base64
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.core.storage import StorageService, storage_service
from app.modules.audit.service import audit_service
from app.modules.cadastros.models import ClienteDocumento
from app.modules.cadastros.service import ClienteService
from app.shared.enums import AuditAction, ClienteDocumentoTipo

MAX_DOCUMENTO_BYTES = 10 * 1024 * 1024
ALLOWED_CONTENT_TYPES = frozenset(
    {
        "application/pdf",
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
    }
)
ALLOWED_EXTENSIONS = frozenset({".pdf", ".jpg", ".jpeg", ".png", ".webp"})

CLIENTE_DOCUMENTO_CAMPOS: tuple[tuple[str, str, str, bool], ...] = (
    ("cnh", "doc_cnh", "CNH — Carteira de motorista", True),
    ("comprovante_residencia", "doc_comprovante_residencia", "Comprovante de residência", True),
    ("holerite", "doc_holerite", "Holerite / contracheque", False),
    ("identidade", "doc_identidade", "Documento de identidade (RG)", False),
)


@dataclass
class DocumentoDownload:
    filename: str
    content_type: str
    data: bytes | None = None
    redirect_url: str | None = None


class ClienteDocumentoService:
    """Persistência de arquivos anexados ao cliente."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.cliente_svc = ClienteService(session)

    async def map_by_tipo(self, cliente_id: uuid.UUID) -> dict[str, ClienteDocumento]:
        stmt = select(ClienteDocumento).where(
            ClienteDocumento.cliente_id == cliente_id,
            ClienteDocumento.deleted_at.is_(None),
        )
        rows = list((await self.session.execute(stmt)).scalars().all())
        return {row.tipo.value: row for row in rows}

    async def get_by_tipo(
        self, cliente_id: uuid.UUID, tipo: ClienteDocumentoTipo
    ) -> ClienteDocumento | None:
        stmt = (
            select(ClienteDocumento)
            .where(
                ClienteDocumento.cliente_id == cliente_id,
                ClienteDocumento.tipo == tipo,
                ClienteDocumento.deleted_at.is_(None),
            )
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    @staticmethod
    def validate_upload(filename: str, content_type: str, size: int) -> None:
        if size <= 0:
            raise ValidationError("Arquivo vazio.")
        if size > MAX_DOCUMENTO_BYTES:
            raise ValidationError("Arquivo excede o limite de 10 MB.")
        ext = ""
        if "." in filename:
            ext = "." + filename.rsplit(".", 1)[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValidationError("Formato não permitido. Use PDF, JPG, PNG ou WEBP.")
        normalized = (content_type or "").split(";", 1)[0].strip().lower()
        if normalized and normalized not in ALLOWED_CONTENT_TYPES:
            raise ValidationError("Tipo de arquivo não permitido.")

    async def upload(
        self,
        tenant_id: uuid.UUID,
        cliente_id: uuid.UUID,
        tipo: ClienteDocumentoTipo,
        *,
        file_bytes: bytes,
        filename: str,
        content_type: str,
    ) -> ClienteDocumento:
        await self.cliente_svc.get(cliente_id)
        self.validate_upload(filename, content_type, len(file_bytes))

        safe_name = filename.replace("/", "_").replace("\\", "_") or f"{tipo.value}.pdf"
        safe_type = (content_type or "application/octet-stream").split(";", 1)[0].strip()
        storage_key: str | None = None
        inline_data: str | None = None

        if storage_service.is_configured():
            key = StorageService.build_key(tenant_id, "cadastros", "cliente_documento", safe_name)
            storage_service.upload_bytes(key, file_bytes, safe_type or "application/octet-stream")
            storage_key = key
        else:
            encoded = base64.b64encode(file_bytes).decode("ascii")
            inline_data = encoded

        existing = await self.get_by_tipo(cliente_id, tipo)
        if existing:
            doc = existing
            doc.filename = safe_name
            doc.content_type = safe_type or "application/octet-stream"
            doc.size_bytes = len(file_bytes)
            doc.storage_key = storage_key
            doc.inline_data = inline_data
        else:
            doc = ClienteDocumento(
                tenant_id=tenant_id,
                cliente_id=cliente_id,
                tipo=tipo,
                filename=safe_name,
                content_type=safe_type or "application/octet-stream",
                size_bytes=len(file_bytes),
                storage_key=storage_key,
                inline_data=inline_data,
            )
            self.session.add(doc)

        await self.session.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="cliente_documento",
            entity_id=doc.id,
            description=f"Documento {tipo.value} anexado ao cliente",
        )
        return doc

    async def resolve_download(
        self, cliente_id: uuid.UUID, tipo: ClienteDocumentoTipo
    ) -> DocumentoDownload:
        doc = await self.get_by_tipo(cliente_id, tipo)
        if doc is None:
            raise NotFoundError("Documento não encontrado.")

        if doc.storage_key and storage_service.is_configured():
            url = storage_service.generate_presigned_download(doc.storage_key)
            return DocumentoDownload(
                filename=doc.filename,
                content_type=doc.content_type,
                redirect_url=url,
            )

        if doc.inline_data:
            data = base64.b64decode(doc.inline_data.encode("ascii"))
            return DocumentoDownload(
                filename=doc.filename,
                content_type=doc.content_type,
                data=data,
            )

        raise NotFoundError("Arquivo do documento indisponível.")
