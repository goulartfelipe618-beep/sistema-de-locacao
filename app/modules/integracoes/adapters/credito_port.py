"""Porta (Protocol) de consulta de crédito (§12.3)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(slots=True)
class CreditoConsultaResultado:
    score: int
    restricao: bool
    motivo: str | None
    bureau: str


@runtime_checkable
class CreditoPort(Protocol):
    nome: str

    def consultar_score(
        self, *, documento: str, tipo_pessoa: str, credenciais: dict[str, str]
    ) -> CreditoConsultaResultado:
        ...
