"""Upload e exibição de fotos de veículos."""

from __future__ import annotations

import base64
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.core.storage import StorageService, storage_service
from app.modules.frota.models import FrotaVeiculoFoto
from app.modules.frota.schemas import VeiculoFotoCreate
from app.modules.frota.service import FotoService

logger = get_logger(__name__)

MAX_VEICULO_FOTOS = 8
MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_CONTENT_TYPES = frozenset({"image/jpeg", "image/png", "image/webp", "image/jpg"})
ALLOWED_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp"})


class VeiculoFotoUploadService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.foto_svc = FotoService(session)

    async def count_active(self, veiculo_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(FrotaVeiculoFoto).where(
            FrotaVeiculoFoto.veiculo_id == veiculo_id,
            FrotaVeiculoFoto.deleted_at.is_(None),
        )
        return int(await self.session.scalar(stmt) or 0)

    @staticmethod
    def validate_image(filename: str, content_type: str, size: int) -> str:
        if size <= 0:
            raise ValidationError("Selecione uma imagem válida.")
        if size > MAX_IMAGE_BYTES:
            raise ValidationError("Imagem muito grande (máximo 5 MB).")
        ext = ""
        if filename and "." in filename:
            ext = "." + filename.rsplit(".", 1)[-1].lower()
        if ext and ext not in ALLOWED_EXTENSIONS:
            raise ValidationError("Formato inválido. Use JPG, PNG ou WebP.")
        safe_type = (content_type or "image/jpeg").split(";", 1)[0].strip().lower()
        if safe_type not in ALLOWED_CONTENT_TYPES:
            raise ValidationError("Formato inválido. Use JPG, PNG ou WebP.")
        return safe_type

    async def _next_ordem(self, veiculo_id: uuid.UUID) -> int:
        stmt = select(func.coalesce(func.max(FrotaVeiculoFoto.ordem), -1)).where(
            FrotaVeiculoFoto.veiculo_id == veiculo_id,
            FrotaVeiculoFoto.deleted_at.is_(None),
        )
        current = await self.session.scalar(stmt)
        return int(current or -1) + 1

    async def upload(
        self,
        tenant_id: uuid.UUID,
        veiculo_id: uuid.UUID,
        *,
        file_bytes: bytes,
        filename: str,
        content_type: str,
        legenda: str | None = None,
    ) -> FrotaVeiculoFoto:
        total = await self.count_active(veiculo_id)
        if total >= MAX_VEICULO_FOTOS:
            raise ValidationError(f"Máximo de {MAX_VEICULO_FOTOS} fotos por veículo.")

        safe_type = self.validate_image(filename, content_type, len(file_bytes))
        safe_name = (filename or "foto.jpg").replace("/", "_").replace("\\", "_")
        storage_key: str
        inline_data: str | None = None

        if storage_service.is_configured():
            try:
                storage_key = StorageService.build_key(
                    tenant_id, "frota", "veiculo_foto", safe_name
                )
                storage_service.upload_bytes(storage_key, file_bytes, safe_type)
            except Exception as exc:
                logger.warning("Falha ao enviar foto ao R2, usando inline: %s", exc)
                storage_key = f"inline:{uuid.uuid4().hex}"
                inline_data = base64.b64encode(file_bytes).decode("ascii")
        else:
            storage_key = f"inline:{uuid.uuid4().hex}"
            inline_data = base64.b64encode(file_bytes).decode("ascii")

        foto = await self.foto_svc.add(
            tenant_id,
            veiculo_id,
            VeiculoFotoCreate(
                storage_key=storage_key,
                legenda=legenda,
                ordem=await self._next_ordem(veiculo_id),
            ),
        )
        foto.content_type = safe_type
        foto.inline_data = inline_data
        await self.session.flush()
        return foto

    @staticmethod
    def purge_storage(foto: FrotaVeiculoFoto) -> None:
        if not foto.storage_key or foto.storage_key.startswith("inline:"):
            return
        if storage_service.is_configured():
            try:
                storage_service.delete(foto.storage_key)
            except Exception as exc:
                logger.warning("Falha ao remover foto do R2 (%s): %s", foto.storage_key, exc)

    async def resolve_image_bytes(self, foto: FrotaVeiculoFoto) -> tuple[bytes, str]:
        content_type = getattr(foto, "content_type", None) or "image/jpeg"
        inline_data = getattr(foto, "inline_data", None)
        if inline_data:
            return base64.b64decode(inline_data.encode("ascii")), content_type
        if foto.storage_key and storage_service.is_configured():
            try:
                data = storage_service.download_bytes(foto.storage_key)
                return data, content_type
            except Exception as exc:
                raise NotFoundError("Imagem indisponível.") from exc
        raise NotFoundError("Imagem não encontrada.")
