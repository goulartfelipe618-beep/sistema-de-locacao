"""Upload e exibição da capa de categoria (grupo no site)."""

from __future__ import annotations

import base64
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.core.storage import StorageService, storage_service
from app.modules.frota.veiculo_fotos import VeiculoFotoUploadService

logger = get_logger(__name__)


def categoria_tem_capa(categoria) -> bool:
    return bool(
        getattr(categoria, "capa_inline_data", None)
        or getattr(categoria, "capa_storage_key", None)
    )


def public_categoria_capa_url(categoria_id: uuid.UUID) -> str:
    return f"/api/v1/public/categorias/{categoria_id}/imagem"


class CategoriaCapaService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _purge_capa_storage(categoria) -> None:
        key = getattr(categoria, "capa_storage_key", None)
        if not key or str(key).startswith("inline:"):
            return
        if storage_service.is_configured():
            try:
                storage_service.delete(key)
            except Exception as exc:
                logger.warning("Falha ao remover capa de categoria do R2 (%s): %s", key, exc)

    async def upload_capa(
        self,
        tenant_id: uuid.UUID,
        categoria_id: uuid.UUID,
        *,
        file_bytes: bytes,
        filename: str,
        content_type: str,
    ):
        from app.modules.frota.service import CategoriasService

        categoria = await CategoriasService(self.session).get(categoria_id)
        safe_type = VeiculoFotoUploadService.validate_image(filename, content_type, len(file_bytes))
        safe_name = (filename or "capa.jpg").replace("/", "_").replace("\\", "_")
        self._purge_capa_storage(categoria)

        storage_key: str
        inline_data: str | None = None
        if storage_service.is_configured():
            try:
                storage_key = StorageService.build_key(
                    tenant_id, "frota", "categoria_capa", safe_name
                )
                storage_service.upload_bytes(storage_key, file_bytes, safe_type)
            except Exception as exc:
                logger.warning("Falha ao enviar capa de categoria ao R2, usando inline: %s", exc)
                storage_key = f"inline:{uuid.uuid4().hex}"
                inline_data = base64.b64encode(file_bytes).decode("ascii")
        else:
            storage_key = f"inline:{uuid.uuid4().hex}"
            inline_data = base64.b64encode(file_bytes).decode("ascii")

        categoria.capa_storage_key = storage_key
        categoria.capa_content_type = safe_type
        categoria.capa_inline_data = inline_data
        await self.session.flush()
        return categoria

    async def remove_capa(self, categoria_id: uuid.UUID) -> None:
        from app.modules.frota.service import CategoriasService

        categoria = await CategoriasService(self.session).get(categoria_id)
        self._purge_capa_storage(categoria)
        categoria.capa_storage_key = None
        categoria.capa_content_type = None
        categoria.capa_inline_data = None
        await self.session.flush()

    async def resolve_capa_bytes(self, categoria) -> tuple[bytes, str]:
        if not categoria_tem_capa(categoria):
            raise NotFoundError("Capa da categoria não encontrada.")
        content_type = categoria.capa_content_type or "image/jpeg"
        if categoria.capa_inline_data:
            return base64.b64decode(categoria.capa_inline_data.encode("ascii")), content_type
        if categoria.capa_storage_key and storage_service.is_configured():
            try:
                data = storage_service.download_bytes(categoria.capa_storage_key)
                return data, content_type
            except Exception as exc:
                raise NotFoundError("Imagem de capa indisponível.") from exc
        raise NotFoundError("Capa da categoria não encontrada.")
