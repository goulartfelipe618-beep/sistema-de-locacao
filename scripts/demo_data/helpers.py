"""Utilitários para seed demo (CPFs válidos, placas, idempotência)."""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

# CPFs válidos (apenas para ambiente demo).
VALID_CPFS: tuple[str, ...] = (
    "52998224725",
    "11144477735",
    "39053344705",
    "45317828791",
    "71128590182",
    "28625587887",
    "10000000019",
    "10000000108",
    "10000000280",
    "10000000361",
    "10000000442",
    "10000000523",
    "10000000604",
    "10000000795",
    "10000000876",
    "10000000957",
    "10000001090",
    "10000001171",
    "10000001252",
    "10000001333",
)

VALID_CNPJS: tuple[str, ...] = (
    "11222333000181",
    "11444777000161",
    "19131243000197",
    "34028316000103",
    "10000000000145",
    "10000001000190",
    "10000002000134",
    "10000003000189",
    "10000004000123",
    "10000005000178",
    "10000006000112",
    "10000007000167",
    "10000008000101",
    "10000009000156",
    "10000010000180",
    "10000011000125",
    "10000012000170",
    "10000013000114",
    "10000014000169",
    "10000015000103",
)


def demo_count() -> int:
    raw = os.getenv("SEED_DEMO_COUNT", "7")
    try:
        n = int(raw)
    except ValueError:
        n = 7
    return max(1, min(n, 50))


def cpf_at(index: int) -> str:
    return VALID_CPFS[index % len(VALID_CPFS)]


def cnpj_at(index: int) -> str:
    return VALID_CNPJS[index % len(VALID_CNPJS)]


def placa_at(index: int) -> str:
    """Placa fictícia 7 chars (formato antigo)."""
    letters = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    a = letters[index % len(letters)]
    b = letters[(index + 3) % len(letters)]
    c = letters[(index + 7) % len(letters)]
    num = 1000 + index
    return f"{a}{b}{c}{num % 10000:04d}"[:7]


def money(base: float, index: int = 0) -> Decimal:
    return Decimal(str(round(base + index * 12.5, 2)))


def dt_future(days: int, hour: int = 10) -> datetime:
    tz = timezone.utc
    base = datetime.now(tz) + timedelta(days=days)
    return base.replace(hour=hour, minute=0, second=0, microsecond=0)


def dt_past(days: int, hour: int = 14) -> datetime:
    tz = timezone.utc
    base = datetime.now(tz) - timedelta(days=days)
    return base.replace(hour=hour, minute=0, second=0, microsecond=0)


def date_future(days: int) -> date:
    return (datetime.now(timezone.utc).date() + timedelta(days=days))


def date_past(days: int) -> date:
    return (datetime.now(timezone.utc).date() - timedelta(days=days))
