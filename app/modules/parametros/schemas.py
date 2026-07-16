"""Schemas Pydantic do módulo Parâmetros."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field

from app.shared.enums import ParametroCategoria, ParametroTipo


class ParametroValorRead(BaseModel):
    """Valor efetivo de um parâmetro (padrão ou override)."""

    chave: str
    categoria: ParametroCategoria
    label: str
    descricao: str
    tipo: ParametroTipo
    unidade: str | None = None
    valor: Any
    valor_padrao: Any
    override: bool = False
    filial_id: uuid.UUID | None = None


class ParametroUpdate(BaseModel):
    """Atualização de um parâmetro."""

    valor: Any
    filial_id: uuid.UUID | None = None


class ParametroBulkUpdate(BaseModel):
    """Atualização em lote de parâmetros."""

    valores: dict[str, Any] = Field(default_factory=dict)
    filial_id: uuid.UUID | None = None
