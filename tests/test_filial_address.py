"""Formatação pública de endereço de filial."""

from __future__ import annotations

import uuid

from app.modules.tenants.filial_address import filial_public_row, format_filial_address
from app.modules.tenants.models import Filial


def test_format_filial_address_full() -> None:
    filial = Filial(
        tenant_id=uuid.uuid4(),
        code="0001",
        name="Matriz",
        address="Av. Paulista",
        number="1000",
        district="Bela Vista",
        city="São Paulo",
        state="SP",
        zip_code="01310100",
        is_headquarters=True,
    )
    assert format_filial_address(filial) == (
        "Av. Paulista, 1000, Bela Vista, São Paulo — SP, CEP 01310-100"
    )


def test_filial_public_row_includes_geo_and_matriz_flag() -> None:
    filial = Filial(
        tenant_id=uuid.uuid4(),
        code="0001",
        name="Matriz",
        city="Brasília",
        state="DF",
        latitude=-15.7942,
        longitude=-47.8825,
        is_headquarters=True,
    )
    row = filial_public_row(filial)
    assert row["matriz"] is True
    assert row["latitude"] == -15.7942
    assert row["longitude"] == -47.8825
    assert row["nome"] == "Matriz"
