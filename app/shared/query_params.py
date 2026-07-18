"""Helpers para parâmetros de query string em rotas Web."""

from __future__ import annotations

import uuid


def parse_optional_uuid(value: str | None) -> uuid.UUID | None:
    """Converte query param em UUID ou None (vazio/inválido → None, sem 422)."""
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    try:
        return uuid.UUID(cleaned)
    except ValueError:
        return None
