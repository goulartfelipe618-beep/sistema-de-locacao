"""Transição de carregamento do site público (splash configurável no ERP)."""

from __future__ import annotations

import base64
from typing import Any

from app.core.storage import storage_service
from app.modules.tenants.models import Tenant

DEFAULT_SITE_BACKGROUND = "#ffffff"
PUBLIC_TRANSITION_IMAGE_PATH = "/api/v1/public/transicao/imagem"


def _tenant_color(tenant: Tenant, field: str) -> str | None:
    return getattr(tenant, field, None)


def tenant_has_transition_image(tenant: Tenant) -> bool:
    if tenant.site_transition_image_storage_key:
        return True
    url = (tenant.site_transition_image_url or "").strip()
    return bool(url)


def resolve_transition_image_bytes(tenant: Tenant) -> tuple[bytes, str] | None:
    if tenant.site_transition_image_storage_key and storage_service.is_configured():
        try:
            data = storage_service.download_bytes(tenant.site_transition_image_storage_key)
            content_type = tenant.site_transition_image_content_type or "image/png"
            return data, content_type
        except Exception:
            return None
    url = (tenant.site_transition_image_url or "").strip()
    if url.startswith("data:"):
        try:
            header, encoded = url.split(",", 1)
            content_type = header.split(";")[0].replace("data:", "") or "image/png"
            return base64.b64decode(encoded), content_type
        except (ValueError, TypeError):
            return None
    return None


def site_transition_payload(tenant: Tenant) -> dict[str, Any]:
    bg = _tenant_color(tenant, "site_transition_bg_color") or (
        _tenant_color(tenant, "site_background_color") or DEFAULT_SITE_BACKGROUND
    )
    size = tenant.site_transition_image_size_px or 120
    size = max(48, min(400, int(size)))
    imagem_url: str | None = None
    if tenant.site_transition_enabled and tenant_has_transition_image(tenant):
        raw = (tenant.site_transition_image_url or "").strip()
        if raw.startswith("http://") or raw.startswith("https://"):
            imagem_url = raw
        elif raw.startswith("data:"):
            imagem_url = raw
        else:
            imagem_url = PUBLIC_TRANSITION_IMAGE_PATH
    return {
        "ativo": bool(tenant.site_transition_enabled),
        "fundo": bg,
        "tamanho_px": size,
        "imagem_url": imagem_url,
    }
