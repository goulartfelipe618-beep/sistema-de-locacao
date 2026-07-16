"""Porta (Protocol) de telemetria/rastreamento (§12.4)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable


@dataclass(slots=True)
class TelemetriaPosicao:
    equipamento_id: str
    lat: Decimal
    lng: Decimal
    km: int | None
    conn_status: str
    atualizado_em: datetime


@dataclass(slots=True)
class TelemetriaEventoExterno:
    equipamento_id: str
    tipo: str
    descricao: str | None
    lat: Decimal | None
    lng: Decimal | None
    velocidade: Decimal | None
    ocorrido_em: datetime
    payload: dict[str, Any] | None = None


@runtime_checkable
class TelemetriaPort(Protocol):
    nome: str

    def sincronizar(
        self, *, credenciais: dict[str, str], equipamentos: list[str]
    ) -> tuple[list[TelemetriaPosicao], list[TelemetriaEventoExterno]]:
        ...
