"""Schemas da API pública (site B2C) — sem dados sensíveis de operação interna."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.shared.value_objects import only_digits


class PublicClienteInput(BaseModel):
    nome: str = Field(min_length=2, max_length=200)
    email: EmailStr
    cpf: str = Field(min_length=11, max_length=14)
    telefone: str | None = Field(default=None, max_length=20)

    @field_validator("cpf")
    @classmethod
    def _cpf_digits(cls, value: str) -> str:
        digits = only_digits(value)
        if len(digits) != 11:
            raise ValueError("CPF inválido.")
        return digits


class PublicReservaSiteCreate(BaseModel):
    """Reserva originada no site — cliente resolvido/criado no servidor."""

    cliente: PublicClienteInput
    categoria_id: uuid.UUID
    filial_retirada_id: uuid.UUID
    filial_devolucao_id: uuid.UUID | None = None
    retirada_em: datetime
    devolucao_em: datetime
    veiculo_id: uuid.UUID | None = None
    cupom_codigo: str | None = Field(default=None, max_length=40)
    protecao_ids: list[uuid.UUID] = Field(default_factory=list)
    taxa_ids: list[uuid.UUID] = Field(default_factory=list)
    observacoes: str | None = None


class PublicCotacaoSiteCreate(BaseModel):
    categoria_id: uuid.UUID
    filial_retirada_id: uuid.UUID
    filial_devolucao_id: uuid.UUID | None = None
    retirada_em: datetime
    devolucao_em: datetime
    veiculo_id: uuid.UUID | None = None
    protecao_ids: list[uuid.UUID] = Field(default_factory=list)
    taxa_ids: list[uuid.UUID] = Field(default_factory=list)
    cupom_codigo: str | None = Field(default=None, max_length=40)


class PublicCotacaoSiteRead(BaseModel):
    diaria_unitaria: Decimal
    dias: int
    dias_cobrados: int
    subtotal_diarias: Decimal
    subtotal_taxas: Decimal
    subtotal_protecoes: Decimal
    total: Decimal
    tabela_nome: str
    km_livre: bool
    desconto_cupom: Decimal = Decimal("0")
    total_com_desconto: Decimal
    moeda: str = "BRL"
