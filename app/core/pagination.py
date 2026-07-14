"""Utilitários de paginação padronizados para listagens (API e Web)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")

MAX_PAGE_SIZE = 200
DEFAULT_PAGE_SIZE = 25


@dataclass(frozen=True, slots=True)
class PageParams:
    """Parâmetros de paginação normalizados (1-indexed)."""

    page: int = 1
    size: int = DEFAULT_PAGE_SIZE

    def __post_init__(self) -> None:
        object.__setattr__(self, "page", max(1, self.page))
        object.__setattr__(self, "size", min(max(1, self.size), MAX_PAGE_SIZE))

    @property
    def offset(self) -> int:
        """Deslocamento para a query (OFFSET)."""
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        """Quantidade de itens por página (LIMIT)."""
        return self.size


@dataclass(frozen=True, slots=True)
class Page(Generic[T]):
    """Resultado paginado genérico (independente de protocolo)."""

    items: list[T]
    total: int
    page: int
    size: int

    @property
    def pages(self) -> int:
        """Total de páginas."""
        if self.size == 0:
            return 0
        return (self.total + self.size - 1) // self.size

    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    @property
    def has_prev(self) -> bool:
        return self.page > 1


class PageMeta(BaseModel):
    """Metadados de paginação para respostas de API."""

    page: int = Field(ge=1)
    size: int = Field(ge=1)
    total: int = Field(ge=0)
    pages: int = Field(ge=0)


class PagedResponse(BaseModel, Generic[T]):
    """Envelope padrão de resposta paginada da API REST."""

    data: list[T]
    meta: PageMeta

    @classmethod
    def from_page(cls, page: Page[T]) -> PagedResponse[T]:
        """Constrói a resposta a partir de um :class:`Page` de domínio."""
        return cls(
            data=page.items,
            meta=PageMeta(page=page.page, size=page.size, total=page.total, pages=page.pages),
        )
