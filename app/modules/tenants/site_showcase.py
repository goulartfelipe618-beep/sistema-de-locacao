"""Vitrine da home do site (3 imagens configuráveis no ERP)."""

from __future__ import annotations

import base64
from typing import Any

from app.core.storage import storage_service
from app.modules.tenants.models import Tenant

SHOWCASE_WIDTH_PX = 1080
SHOWCASE_HEIGHT_PX = 1350
SHOWCASE_SLOTS = (1, 2, 3)
SHOWCASE_META_SUFFIXES = ("titulo", "descricao", "cta_texto", "cta_url", "cta_target")
SHOWCASE_CTA_TARGETS = ("_self", "_blank")
PUBLIC_SHOWCASE_IMAGE_PATH = "/api/v1/public/vitrine/imagem/{slot}"


def _tenant_field(tenant: Tenant, slot: int, suffix: str) -> Any:
    return getattr(tenant, f"site_showcase_{slot}_{suffix}", None)


def tenant_has_showcase_image(tenant: Tenant, slot: int) -> bool:
    if _tenant_field(tenant, slot, "storage_key"):
        return True
    url = (_tenant_field(tenant, slot, "url") or "").strip()
    return bool(url)


def resolve_showcase_image_bytes(tenant: Tenant, slot: int) -> tuple[bytes, str] | None:
    if slot not in SHOWCASE_SLOTS:
        return None
    storage_key = _tenant_field(tenant, slot, "storage_key")
    if storage_key and storage_service.is_configured():
        try:
            data = storage_service.download_bytes(storage_key)
            content_type = _tenant_field(tenant, slot, "content_type") or "image/png"
            return data, content_type
        except Exception:
            return None
    url = (_tenant_field(tenant, slot, "url") or "").strip()
    if url.startswith("data:"):
        try:
            header, encoded = url.split(",", 1)
            content_type = header.split(";")[0].replace("data:", "") or "image/png"
            return base64.b64decode(encoded), content_type
        except (ValueError, TypeError):
            return None
    return None


def _showcase_image_url(tenant: Tenant, slot: int) -> str | None:
    if not tenant_has_showcase_image(tenant, slot):
        return None
    raw = (_tenant_field(tenant, slot, "url") or "").strip()
    if raw.startswith("http://") or raw.startswith("https://") or raw.startswith("data:"):
        return raw
    return PUBLIC_SHOWCASE_IMAGE_PATH.format(slot=slot)


def _showcase_meta(tenant: Tenant, slot: int) -> dict[str, Any]:
    titulo = (_tenant_field(tenant, slot, "titulo") or "").strip() or None
    descricao = (_tenant_field(tenant, slot, "descricao") or "").strip() or None
    cta_texto = (_tenant_field(tenant, slot, "cta_texto") or "").strip() or None
    cta_url = (_tenant_field(tenant, slot, "cta_url") or "").strip() or None
    cta_target = (_tenant_field(tenant, slot, "cta_target") or "_self").strip()
    if cta_target not in SHOWCASE_CTA_TARGETS:
        cta_target = "_self"
    return {
        "titulo": titulo,
        "descricao": descricao,
        "cta_texto": cta_texto,
        "cta_url": cta_url,
        "cta_target": cta_target,
        "cta_nova_aba": cta_target == "_blank",
    }


def site_showcase_payload(tenant: Tenant) -> dict[str, Any]:
    imagens: list[dict[str, Any]] = []
    for slot in SHOWCASE_SLOTS:
        imagens.append(
            {
                "slot": slot,
                "imagem_url": _showcase_image_url(tenant, slot),
                "largura_px": SHOWCASE_WIDTH_PX,
                "altura_px": SHOWCASE_HEIGHT_PX,
                **_showcase_meta(tenant, slot),
            }
        )
    return {"imagens": imagens}


def tenant_showcase_flags(tenant: Tenant) -> dict[int, bool]:
    return {slot: tenant_has_showcase_image(tenant, slot) for slot in SHOWCASE_SLOTS}
