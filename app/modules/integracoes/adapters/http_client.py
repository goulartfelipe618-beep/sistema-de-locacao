"""Cliente HTTP compartilhado para adaptadores de integração (§12)."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)


def http_get_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 12.0,
) -> dict[str, Any]:
    """GET JSON com timeout; levanta httpx.HTTPError em falha."""
    with httpx.Client(timeout=timeout) as client:
        response = client.get(url, headers=headers or {})
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, dict) else {"data": data}


def http_post_json(
    url: str,
    *,
    payload: dict[str, Any],
    headers: dict[str, str] | None = None,
    timeout: float = 15.0,
) -> dict[str, Any]:
    """POST JSON com timeout; levanta httpx.HTTPError em falha."""
    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, json=payload, headers=headers or {})
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, dict) else {"data": data}
