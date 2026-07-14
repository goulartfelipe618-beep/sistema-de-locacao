"""Abstração de armazenamento de arquivos sobre o Cloudflare R2 (S3 compatível).

O restante da aplicação usa apenas :class:`StorageService`, nunca o SDK
diretamente. Isso permite trocar o provedor sem impacto nos módulos e organiza
as chaves por ``tenant/módulo/entidade/ano/mês/uuid``.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from functools import lru_cache

import boto3
from botocore.client import BaseClient
from botocore.config import Config

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _get_s3_client() -> BaseClient:
    """Cria (e cacheia) o cliente S3 apontando para o endpoint do R2."""
    return boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint_url or None,
        aws_access_key_id=settings.r2_access_key_id or None,
        aws_secret_access_key=settings.r2_secret_access_key or None,
        region_name="auto",
        config=Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"}),
    )


class StorageService:
    """Serviço de armazenamento de objetos no Cloudflare R2."""

    def __init__(self, bucket: str | None = None) -> None:
        self._bucket = bucket or settings.r2_bucket

    @staticmethod
    def build_key(tenant_id: uuid.UUID, module: str, entity: str, filename: str) -> str:
        """Monta a chave do objeto seguindo o padrão de organização de uploads."""
        now = datetime.now(tz=UTC)
        unique = uuid.uuid4().hex
        safe_name = filename.replace("/", "_").replace("\\", "_")
        return f"{tenant_id}/{module}/{entity}/{now:%Y}/{now:%m}/{unique}_{safe_name}"

    def is_configured(self) -> bool:
        """Indica se as credenciais mínimas do R2 estão presentes."""
        return bool(settings.r2_endpoint_url and settings.r2_access_key_id)

    def upload_bytes(self, key: str, data: bytes, content_type: str) -> str:
        """Envia bytes para o armazenamento e retorna a chave do objeto."""
        _get_s3_client().put_object(
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        logger.info("Objeto enviado ao R2: %s", key)
        return key

    def generate_presigned_upload(self, key: str, content_type: str) -> str:
        """Gera uma URL assinada para *upload* direto do cliente (PUT)."""
        return _get_s3_client().generate_presigned_url(
            "put_object",
            Params={"Bucket": self._bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=settings.r2_presign_expire_seconds,
        )

    def generate_presigned_download(self, key: str) -> str:
        """Gera uma URL assinada para *download* temporário (GET)."""
        return _get_s3_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=settings.r2_presign_expire_seconds,
        )

    def delete(self, key: str) -> None:
        """Remove um objeto do armazenamento."""
        _get_s3_client().delete_object(Bucket=self._bucket, Key=key)
        logger.info("Objeto removido do R2: %s", key)


storage_service = StorageService()
