"""Porta (Protocol) de consultas de trânsito/DETRAN (§12.2)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol, runtime_checkable


@dataclass(slots=True)
class MultaTransito:
    ait: str
    codigo_infracao: str
    orgao: str
    valor: Decimal
    pontuacao: int
    ocorrido_em: datetime


@dataclass(slots=True)
class CnhConsulta:
    numero: str
    categoria: str
    validade: datetime | None
    pontuacao: int
    status: str


@dataclass(slots=True)
class DebitoVeicular:
    tipo: str
    descricao: str
    valor: Decimal
    vencimento: datetime | None


@dataclass(slots=True)
class TransitoConsultaResultado:
    multas: list[MultaTransito]
    cnh: CnhConsulta | None = None
    debitos: list[DebitoVeicular] | None = None


@runtime_checkable
class TransitoPort(Protocol):
    nome: str

    def consultar_multas_veiculo(
        self, *, placa: str, renavam: str | None, credenciais: dict[str, str]
    ) -> list[MultaTransito]:
        ...

    def consultar_cnh(
        self, *, cnh_numero: str, cpf: str | None, credenciais: dict[str, str]
    ) -> CnhConsulta:
        ...

    def consultar_debitos_veiculo(
        self, *, placa: str, renavam: str | None, credenciais: dict[str, str]
    ) -> list[DebitoVeicular]:
        ...
