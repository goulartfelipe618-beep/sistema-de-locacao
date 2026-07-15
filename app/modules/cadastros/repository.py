"""Repositórios do módulo de Cadastros."""

from __future__ import annotations

from sqlalchemy import Select, func, or_, select

from app.modules.cadastros.models import Cliente, TabelaAuxiliar
from app.shared.repository import BaseRepository


class TabelaAuxiliarRepository(BaseRepository[TabelaAuxiliar]):
    """Persistência de itens de tabelas auxiliares."""

    model = TabelaAuxiliar

    async def get_by_grupo_codigo(self, grupo: str, codigo: str) -> TabelaAuxiliar | None:
        """Busca item único por grupo+código (ativo e não excluído)."""
        stmt = (
            self._base_query()
            .where(TabelaAuxiliar.grupo == grupo, TabelaAuxiliar.codigo == codigo)
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    def query_by_grupo(self, grupo: str, *, apenas_ativos: bool = False) -> Select[tuple[TabelaAuxiliar]]:
        """Query filtrada por grupo."""
        stmt = self._base_query().where(TabelaAuxiliar.grupo == grupo)
        if apenas_ativos:
            stmt = stmt.where(TabelaAuxiliar.ativo.is_(True))
        return stmt.order_by(TabelaAuxiliar.ordem.asc(), TabelaAuxiliar.descricao.asc())

    async def list_grupos(self) -> list[str]:
        """Lista grupos distintos do tenant."""
        stmt = (
            select(TabelaAuxiliar.grupo)
            .where(TabelaAuxiliar.deleted_at.is_(None))
            .group_by(TabelaAuxiliar.grupo)
            .order_by(TabelaAuxiliar.grupo.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())


class ClienteRepository(BaseRepository[Cliente]):
    """Persistência de clientes."""

    model = Cliente

    async def get_by_cpf(self, cpf: str) -> Cliente | None:
        """Retorna cliente ativo pelo CPF."""
        stmt = self._base_query().where(Cliente.cpf == cpf).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_cnpj(self, cnpj: str) -> Cliente | None:
        """Retorna cliente ativo pelo CNPJ."""
        stmt = self._base_query().where(Cliente.cnpj == cnpj).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    def search_query(self, search: str | None = None) -> Select[tuple[Cliente]]:
        """Query com busca textual por nome/documento/e-mail."""
        stmt = self._base_query().order_by(Cliente.nome.asc())
        if search:
            term = f"%{search.strip().lower()}%"
            digits = "".join(ch for ch in search if ch.isdigit())
            filters = [
                func.lower(Cliente.nome).like(term),
                func.lower(func.coalesce(Cliente.nome_fantasia, "")).like(term),
                func.lower(func.coalesce(Cliente.email, "")).like(term),
            ]
            if digits:
                filters.append(Cliente.cpf.like(f"%{digits}%"))
                filters.append(Cliente.cnpj.like(f"%{digits}%"))
            stmt = stmt.where(or_(*filters))
        return stmt
