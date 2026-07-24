"""Seção promocional Grupos de Carros na home (configurável no ERP)."""

from __future__ import annotations

import base64
from typing import Any

from app.core.storage import storage_service
from app.modules.tenants.models import Tenant
from app.modules.tenants.site_showcase import SHOWCASE_CTA_TARGETS

GROUPS_PROMO_WIDTH_PX = 560
GROUPS_PROMO_HEIGHT_PX = 420
PUBLIC_GROUPS_PROMO_IMAGE_PATH = "/api/v1/public/grupos-promo/imagem"
GROUPS_PROMO_META_SUFFIXES = ("titulo", "subtitulo", "texto", "cta_texto", "cta_url", "cta_target")


def tenant_has_groups_promo_image(tenant: Tenant) -> bool:
    if tenant.site_groups_promo_storage_key:
        return True
    url = (tenant.site_groups_promo_url or "").strip()
    return bool(url)


def resolve_groups_promo_image_bytes(tenant: Tenant) -> tuple[bytes, str] | None:
    storage_key = tenant.site_groups_promo_storage_key
    if storage_key and storage_service.is_configured():
        try:
            data = storage_service.download_bytes(storage_key)
            content_type = tenant.site_groups_promo_content_type or "image/png"
            return data, content_type
        except Exception:
            return None
    url = (tenant.site_groups_promo_url or "").strip()
    if url.startswith("data:"):
        try:
            header, encoded = url.split(",", 1)
            content_type = header.split(";")[0].replace("data:", "") or "image/png"
            return base64.b64decode(encoded), content_type
        except (ValueError, TypeError):
            return None
    return None


def _groups_promo_image_url(tenant: Tenant) -> str | None:
    if not tenant_has_groups_promo_image(tenant):
        return None
    raw = (tenant.site_groups_promo_url or "").strip()
    if raw.startswith("http://") or raw.startswith("https://") or raw.startswith("data:"):
        return raw
    return PUBLIC_GROUPS_PROMO_IMAGE_PATH


def site_groups_promo_payload(tenant: Tenant) -> dict[str, Any]:
    titulo = (tenant.site_groups_promo_titulo or "").strip() or None
    subtitulo = (tenant.site_groups_promo_subtitulo or "").strip() or None
    texto = (tenant.site_groups_promo_texto or "").strip() or None
    cta_texto = (tenant.site_groups_promo_cta_texto or "").strip() or None
    cta_url = (tenant.site_groups_promo_cta_url or "").strip() or None
    cta_target = (tenant.site_groups_promo_cta_target or "_self").strip()
    if cta_target not in SHOWCASE_CTA_TARGETS:
        cta_target = "_self"
    return {
        "imagem_url": _groups_promo_image_url(tenant),
        "largura_px": GROUPS_PROMO_WIDTH_PX,
        "altura_px": GROUPS_PROMO_HEIGHT_PX,
        "titulo": titulo,
        "subtitulo": subtitulo,
        "texto": texto,
        "cta_texto": cta_texto,
        "cta_url": cta_url,
        "cta_target": cta_target,
        "cta_nova_aba": cta_target == "_blank",
    }
