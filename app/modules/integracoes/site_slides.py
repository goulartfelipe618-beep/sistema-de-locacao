"""Slides do site institucional (upload, listagem e API pública)."""

from __future__ import annotations

import base64
import re
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.core.storage import storage_service
from app.modules.audit.service import audit_service
from app.modules.integracoes.models import IntSiteSlide
from app.shared.enums import AuditAction
from app.shared.repository import BaseRepository

logger = get_logger(__name__)

MAX_SLIDES = 10
MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_CONTENT_TYPES = frozenset({"image/jpeg", "image/png", "image/webp", "image/jpg"})


class SiteSlideRepository(BaseRepository[IntSiteSlide]):
    model = IntSiteSlide

    def list_active_query(self, tenant_id: uuid.UUID):
        return (
            select(IntSiteSlide)
            .where(
                IntSiteSlide.tenant_id == tenant_id,
                IntSiteSlide.deleted_at.is_(None),
                IntSiteSlide.ativo.is_(True),
            )
            .order_by(IntSiteSlide.sort_order, IntSiteSlide.created_at)
        )

    def list_all_query(self, tenant_id: uuid.UUID):
        return (
            select(IntSiteSlide)
            .where(IntSiteSlide.tenant_id == tenant_id, IntSiteSlide.deleted_at.is_(None))
            .order_by(IntSiteSlide.sort_order, IntSiteSlide.created_at)
        )


def resolve_slide_image_url(slide: IntSiteSlide, *, request_base: str | None = None) -> str | None:
    """URL para exibir a imagem (presign R2, data URI ou rota pública do ERP)."""
    if slide.image_url:
        return slide.image_url
    if request_base:
        base = request_base.rstrip("/")
        return f"{base}/api/v1/public/slides/{slide.id}/imagem"
    if slide.storage_key and storage_service.is_configured():
        try:
            return storage_service.generate_presigned_download(slide.storage_key)
        except Exception:
            return None
    return None


def decode_slide_image_bytes(slide: IntSiteSlide) -> tuple[bytes, str]:
    """Retorna bytes e content-type da imagem do slide."""
    if slide.storage_key and storage_service.is_configured():
        try:
            data = storage_service.download_bytes(slide.storage_key)
            return data, slide.content_type or "image/jpeg"
        except Exception as exc:
            raise NotFoundError("Imagem do slide indisponível.") from exc
    if slide.image_url and slide.image_url.startswith("data:"):
        match = re.match(r"^data:([^;]+);base64,(.+)$", slide.image_url, re.DOTALL)
        if match:
            return base64.b64decode(match.group(2)), match.group(1)
    raise NotFoundError("Imagem do slide não encontrada.")


class SiteSlideService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = SiteSlideRepository(session)

    async def list_slides(self, tenant_id: uuid.UUID, *, active_only: bool = False) -> list[IntSiteSlide]:
        stmt = self.repo.list_active_query(tenant_id) if active_only else self.repo.list_all_query(tenant_id)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def get(self, tenant_id: uuid.UUID, slide_id: uuid.UUID) -> IntSiteSlide:
        slide = await self.repo.get(slide_id)
        if slide is None or slide.tenant_id != tenant_id or slide.deleted_at is not None:
            raise NotFoundError("Slide não encontrado.")
        return slide

    async def _next_sort_order(self, tenant_id: uuid.UUID) -> int:
        stmt = select(func.coalesce(func.max(IntSiteSlide.sort_order), -1)).where(
            IntSiteSlide.tenant_id == tenant_id,
            IntSiteSlide.deleted_at.is_(None),
        )
        current = await self.session.scalar(stmt)
        return int(current or -1) + 1

    def _validate_image(self, file_bytes: bytes, content_type: str) -> str:
        if not file_bytes:
            raise ValidationError("Selecione uma imagem para o slide.")
        if len(file_bytes) > MAX_IMAGE_BYTES:
            raise ValidationError("Imagem muito grande (máximo 5 MB).")
        safe_type = (content_type or "image/jpeg").split(";")[0].strip().lower()
        if safe_type not in ALLOWED_CONTENT_TYPES:
            raise ValidationError("Formato inválido. Use JPG, PNG ou WebP.")
        return safe_type

    async def _store_image(
        self,
        tenant_id: uuid.UUID,
        file_bytes: bytes,
        filename: str,
        content_type: str,
    ) -> tuple[str | None, str | None, str]:
        safe_type = self._validate_image(file_bytes, content_type)
        if storage_service.is_configured():
            try:
                key = storage_service.build_key(tenant_id, "integracoes", "site_slide", filename or "slide.jpg")
                storage_service.upload_bytes(key, file_bytes, safe_type)
                return key, None, safe_type
            except Exception as exc:
                logger.warning("Falha ao enviar slide ao R2, usando inline: %s", exc)
        encoded = base64.b64encode(file_bytes).decode("ascii")
        return None, f"data:{safe_type};base64,{encoded}", safe_type

    async def create_slide(
        self,
        tenant_id: uuid.UUID,
        *,
        file_bytes: bytes,
        filename: str,
        content_type: str,
        titulo: str | None = None,
        link_url: str | None = None,
    ) -> IntSiteSlide:
        count = len(await self.list_slides(tenant_id))
        if count >= MAX_SLIDES:
            raise ValidationError(f"Máximo de {MAX_SLIDES} slides por empresa.")
        storage_key, image_url, safe_type = await self._store_image(
            tenant_id, file_bytes, filename, content_type
        )
        slide = IntSiteSlide(
            tenant_id=tenant_id,
            titulo=(titulo or "").strip() or None,
            storage_key=storage_key,
            image_url=image_url,
            content_type=safe_type,
            link_url=(link_url or "").strip() or None,
            sort_order=await self._next_sort_order(tenant_id),
            ativo=True,
        )
        self.session.add(slide)
        await self.session.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="int_site_slide",
            entity_id=slide.id,
            description=f"Slide do site criado: {slide.titulo or slide.id}",
        )
        return slide

    async def update_slide(
        self,
        tenant_id: uuid.UUID,
        slide_id: uuid.UUID,
        *,
        titulo: str | None = None,
        link_url: str | None = None,
        sort_order: int | None = None,
        ativo: bool | None = None,
    ) -> IntSiteSlide:
        slide = await self.get(tenant_id, slide_id)
        if titulo is not None:
            slide.titulo = titulo.strip() or None
        if link_url is not None:
            slide.link_url = link_url.strip() or None
        if sort_order is not None:
            slide.sort_order = sort_order
        if ativo is not None:
            slide.ativo = ativo
        slide.updated_at = datetime.now(tz=UTC)
        await audit_service.record(
            AuditAction.UPDATE,
            entity="int_site_slide",
            entity_id=slide.id,
            description="Slide do site atualizado",
        )
        return slide

    async def replace_image(
        self,
        tenant_id: uuid.UUID,
        slide_id: uuid.UUID,
        *,
        file_bytes: bytes,
        filename: str,
        content_type: str,
    ) -> IntSiteSlide:
        slide = await self.get(tenant_id, slide_id)
        old_key = slide.storage_key
        storage_key, image_url, safe_type = await self._store_image(
            tenant_id, file_bytes, filename, content_type
        )
        slide.storage_key = storage_key
        slide.image_url = image_url
        slide.content_type = safe_type
        slide.updated_at = datetime.now(tz=UTC)
        if old_key and storage_service.is_configured():
            try:
                storage_service.delete(old_key)
            except Exception:
                pass
        await audit_service.record(
            AuditAction.UPDATE,
            entity="int_site_slide",
            entity_id=slide.id,
            description="Imagem do slide substituída",
        )
        return slide

    async def delete_slide(self, tenant_id: uuid.UUID, slide_id: uuid.UUID) -> None:
        slide = await self.get(tenant_id, slide_id)
        slide.deleted_at = datetime.now(tz=UTC)
        if slide.storage_key and storage_service.is_configured():
            try:
                storage_service.delete(slide.storage_key)
            except Exception:
                pass
        await audit_service.record(
            AuditAction.DELETE,
            entity="int_site_slide",
            entity_id=slide.id,
            description="Slide do site removido",
        )
