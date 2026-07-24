"""Geocodificação de endereços via Mapbox (servidor)."""

from __future__ import annotations

from urllib.parse import quote

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)


async def geocode_address(access_token: str, query: str) -> tuple[float, float] | None:
    token = (access_token or "").strip()
    text = (query or "").strip()
    if not token or not text:
        return None
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{quote(text, safe='')}.json"
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.get(
                url,
                params={
                    "access_token": token,
                    "country": "BR",
                    "limit": 1,
                    "language": "pt",
                },
            )
    except Exception as exc:  # pragma: no cover - rede externa
        logger.warning("Mapbox geocode falhou: %s", exc)
        return None

    if response.status_code >= 400:
        logger.warning("Mapbox geocode HTTP %s", response.status_code)
        return None
    try:
        payload = response.json()
    except ValueError:
        return None
    features = payload.get("features") if isinstance(payload, dict) else None
    if not features:
        return None
    center = features[0].get("center")
    if not isinstance(center, list) or len(center) < 2:
        return None
    try:
        lng, lat = float(center[0]), float(center[1])
    except (TypeError, ValueError):
        return None
    return lat, lng
