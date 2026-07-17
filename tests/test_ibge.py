"""Testes do módulo IBGE (UF/municípios)."""

from __future__ import annotations

import pytest

from app.core.exceptions import ValidationError
from app.shared.ibge import list_municipios


@pytest.mark.asyncio
async def test_list_municipios_invalid_uf() -> None:
    with pytest.raises(ValidationError, match="UF inválida"):
        await list_municipios("XX")
