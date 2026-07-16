"""Estrutura de dados retornada pelos geradores."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ReportData:
    titulo: str
    columns: list[str]
    rows: list[list[Any]]
    summary: dict[str, Any] = field(default_factory=dict)
