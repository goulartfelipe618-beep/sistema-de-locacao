"""Serviços de negócio do módulo Tarifário."""

from __future__ import annotations

import math
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.pagination import Page, PageParams
from app.modules.audit.service import audit_service
from app.modules.frota.models import FrotaAcessorio
from app.modules.tarifario.models import (
    TarPoliticaCancelamento,
    TarPoliticaFaixa,
    TarProtecao,
    TarProtecaoCategoria,
    TarTabela,
    TarTabelaItem,
    TarTaxa,
    TarTemporada,
)
from app.modules.tarifario.schemas import (
    CancelamentoSimulacao,
    PoliticaCreate,
    PoliticaFaixaCreate,
    PoliticaFaixaUpdate,
    PoliticaUpdate,
    PricingLineItem,
    PricingQuoteInput,
    PricingQuoteResult,
    ProtecaoCreate,
    ProtecaoUpdate,
    TabelaCreate,
    TabelaItemCreate,
    TabelaItemUpdate,
    TabelaUpdate,
    TaxaCreate,
    TaxaUpdate,
    TemporadaCreate,
    TemporadaUpdate,
)
from app.shared.enums import (
    AuditAction,
    CadastroStatus,
    PoliticaRetencaoTipo,
    TarifarioCanal,
    TaxaAplicacao,
    TaxaCalculoTipo,
    TemporadaAjusteTipo,
)
from app.shared.repository import BaseRepository

_MONEY = Decimal("0.01")
_ZERO = Decimal("0")


# ---------------------------------------------------------------- Repositories
class TabelaRepository(BaseRepository[TarTabela]):
    model = TarTabela

    def list_query(
        self,
        *,
        canal: TarifarioCanal | None = None,
        filial_id: uuid.UUID | None = None,
        status: CadastroStatus | None = None,
        search: str | None = None,
    ) -> Select[tuple[TarTabela]]:
        stmt = self._base_query().order_by(
            TarTabela.prioridade.desc(), TarTabela.vigencia_inicio.desc()
        )
        if canal:
            stmt = stmt.where(
                or_(TarTabela.canal == canal, TarTabela.canal == TarifarioCanal.TODOS)
            )
        if filial_id:
            stmt = stmt.where(
                or_(TarTabela.filial_id == filial_id, TarTabela.filial_id.is_(None))
            )
        if status:
            stmt = stmt.where(TarTabela.status == status)
        if search:
            term = f"%{search.strip().lower()}%"
            stmt = stmt.where(func.lower(TarTabela.nome).like(term))
        return stmt


class TabelaItemRepository(BaseRepository[TarTabelaItem]):
    model = TarTabelaItem

    async def get_by_tabela_categoria(
        self, tabela_id: uuid.UUID, categoria_id: uuid.UUID
    ) -> TarTabelaItem | None:
        stmt = (
            self._base_query()
            .where(
                TarTabelaItem.tabela_id == tabela_id,
                TarTabelaItem.categoria_id == categoria_id,
            )
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    def list_by_tabela(self, tabela_id: uuid.UUID) -> Select[tuple[TarTabelaItem]]:
        return (
            self._base_query()
            .where(TarTabelaItem.tabela_id == tabela_id)
            .order_by(TarTabelaItem.created_at.asc())
        )


class TemporadaRepository(BaseRepository[TarTemporada]):
    model = TarTemporada

    def list_query(
        self,
        *,
        filial_id: uuid.UUID | None = None,
        categoria_id: uuid.UUID | None = None,
        status: CadastroStatus | None = None,
        search: str | None = None,
    ) -> Select[tuple[TarTemporada]]:
        stmt = self._base_query().order_by(
            TarTemporada.prioridade.desc(), TarTemporada.data_inicio.desc()
        )
        if filial_id:
            stmt = stmt.where(
                or_(TarTemporada.filial_id == filial_id, TarTemporada.filial_id.is_(None))
            )
        if categoria_id:
            stmt = stmt.where(
                or_(
                    TarTemporada.categoria_id == categoria_id,
                    TarTemporada.categoria_id.is_(None),
                )
            )
        if status:
            stmt = stmt.where(TarTemporada.status == status)
        if search:
            term = f"%{search.strip().lower()}%"
            stmt = stmt.where(func.lower(TarTemporada.nome).like(term))
        return stmt


class TaxaRepository(BaseRepository[TarTaxa]):
    model = TarTaxa

    def list_query(
        self,
        *,
        aplicacao: TaxaAplicacao | None = None,
        status: CadastroStatus | None = None,
        search: str | None = None,
    ) -> Select[tuple[TarTaxa]]:
        stmt = self._base_query().order_by(TarTaxa.nome.asc())
        if aplicacao:
            stmt = stmt.where(TarTaxa.aplicacao == aplicacao)
        if status:
            stmt = stmt.where(TarTaxa.status == status)
        if search:
            term = f"%{search.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(TarTaxa.nome).like(term),
                    func.lower(TarTaxa.regra_codigo).like(term),
                )
            )
        return stmt

    async def get_by_regra(self, regra_codigo: str) -> TarTaxa | None:
        stmt = (
            self._base_query()
            .where(
                TarTaxa.regra_codigo == regra_codigo,
                TarTaxa.status == CadastroStatus.ACTIVE,
            )
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()


class ProtecaoRepository(BaseRepository[TarProtecao]):
    model = TarProtecao

    def list_query(
        self,
        *,
        status: CadastroStatus | None = None,
        search: str | None = None,
    ) -> Select[tuple[TarProtecao]]:
        stmt = self._base_query().order_by(TarProtecao.nome.asc())
        if status:
            stmt = stmt.where(TarProtecao.status == status)
        if search:
            term = f"%{search.strip().lower()}%"
            stmt = stmt.where(func.lower(TarProtecao.nome).like(term))
        return stmt


class ProtecaoCategoriaRepository(BaseRepository[TarProtecaoCategoria]):
    model = TarProtecaoCategoria

    async def delete_by_protecao(self, protecao_id: uuid.UUID) -> None:
        stmt = select(TarProtecaoCategoria).where(
            TarProtecaoCategoria.protecao_id == protecao_id,
            TarProtecaoCategoria.deleted_at.is_(None),
        )
        for row in (await self.session.execute(stmt)).scalars().all():
            await self.delete(row)

    def list_by_protecao(self, protecao_id: uuid.UUID) -> Select[tuple[TarProtecaoCategoria]]:
        return self._base_query().where(TarProtecaoCategoria.protecao_id == protecao_id)

    async def list_obrigatorias_por_categoria(
        self, categoria_id: uuid.UUID
    ) -> list[TarProtecao]:
        stmt = (
            select(TarProtecao)
            .join(
                TarProtecaoCategoria,
                TarProtecaoCategoria.protecao_id == TarProtecao.id,
            )
            .where(
                TarProtecao.deleted_at.is_(None),
                TarProtecao.status == CadastroStatus.ACTIVE,
                TarProtecao.obrigatoria.is_(True),
                TarProtecaoCategoria.deleted_at.is_(None),
                TarProtecaoCategoria.categoria_id == categoria_id,
            )
        )
        return list((await self.session.execute(stmt)).scalars().all())


class PoliticaRepository(BaseRepository[TarPoliticaCancelamento]):
    model = TarPoliticaCancelamento

    def list_query(
        self,
        *,
        canal: TarifarioCanal | None = None,
        status: CadastroStatus | None = None,
        search: str | None = None,
    ) -> Select[tuple[TarPoliticaCancelamento]]:
        stmt = self._base_query().order_by(TarPoliticaCancelamento.nome.asc())
        if canal:
            stmt = stmt.where(
                or_(
                    TarPoliticaCancelamento.canal == canal,
                    TarPoliticaCancelamento.canal == TarifarioCanal.TODOS,
                )
            )
        if status:
            stmt = stmt.where(TarPoliticaCancelamento.status == status)
        if search:
            term = f"%{search.strip().lower()}%"
            stmt = stmt.where(func.lower(TarPoliticaCancelamento.nome).like(term))
        return stmt


class PoliticaFaixaRepository(BaseRepository[TarPoliticaFaixa]):
    model = TarPoliticaFaixa

    async def delete_by_politica(self, politica_id: uuid.UUID) -> None:
        stmt = select(TarPoliticaFaixa).where(
            TarPoliticaFaixa.politica_id == politica_id,
            TarPoliticaFaixa.deleted_at.is_(None),
        )
        for row in (await self.session.execute(stmt)).scalars().all():
            await self.delete(row)

    def list_by_politica(self, politica_id: uuid.UUID) -> Select[tuple[TarPoliticaFaixa]]:
        return (
            self._base_query()
            .where(TarPoliticaFaixa.politica_id == politica_id)
            .order_by(TarPoliticaFaixa.ordem.asc(), TarPoliticaFaixa.horas_antes_min.desc())
        )


# --------------------------------------------------------------------- Helpers
def _calc_dias(retirada_em, devolucao_em) -> int:
    delta = devolucao_em - retirada_em
    horas = max(delta.total_seconds() / 3600, 0)
    return max(1, math.ceil(horas / 24))


def _pick_daily_rate(dias: int, item: TarTabelaItem) -> Decimal:
    if dias <= 3:
        return item.valor_1_3
    if dias <= 7:
        return item.valor_4_7
    if dias <= 15:
        return item.valor_8_15
    if dias <= 30:
        return item.valor_16_30
    return item.valor_mensal


def _money(value: Decimal) -> Decimal:
    return value.quantize(_MONEY)


def _canal_matches(tabela_canal: TarifarioCanal, canal: TarifarioCanal) -> bool:
    return tabela_canal == TarifarioCanal.TODOS or tabela_canal == canal


def _vigencia_matches(tabela: TarTabela, ref_date: date) -> bool:
    if tabela.vigencia_inicio > ref_date:
        return False
    if tabela.vigencia_fim is not None and tabela.vigencia_fim < ref_date:
        return False
    return True


def _periodo_intersecta(inicio: date, fim: date, retirada: date, devolucao: date) -> bool:
    return inicio <= devolucao and fim >= retirada


def _temporada_especificidade(temp: TarTemporada, filial_id: uuid.UUID, categoria_id: uuid.UUID) -> int:
    score = 0
    if temp.filial_id == filial_id:
        score += 2
    if temp.categoria_id == categoria_id:
        score += 1
    return score


def _calc_taxa_valor(
    taxa: TarTaxa,
    *,
    dias: int,
    base_diarias: Decimal,
    total_parcial: Decimal,
) -> Decimal:
    if taxa.tipo_calculo == TaxaCalculoTipo.FIXO:
        return taxa.valor
    if taxa.tipo_calculo == TaxaCalculoTipo.PERCENTUAL:
        return _money(base_diarias * taxa.valor / Decimal("100"))
    if taxa.tipo_calculo == TaxaCalculoTipo.POR_DIA:
        return _money(taxa.valor * dias)
    if taxa.tipo_calculo == TaxaCalculoTipo.POR_OCORRENCIA:
        return taxa.valor
    return _ZERO


def _regra_automatica_aplica(regra_codigo: str | None, *, one_way: bool) -> bool:
    if not regra_codigo:
        return False
    if regra_codigo == "one_way":
        return one_way
    return False


def _retencao_valor(
    faixa: TarPoliticaFaixa,
    *,
    valor_reserva: Decimal,
    diaria_unitaria: Decimal | None = None,
    dias_locacao: int = 1,
) -> Decimal:
    if faixa.tipo_retencao == PoliticaRetencaoTipo.PERCENTUAL:
        return _money(valor_reserva * faixa.valor_retencao / Decimal("100"))
    if faixa.tipo_retencao == PoliticaRetencaoTipo.VALOR_FIXO:
        return _money(min(valor_reserva, faixa.valor_retencao))
    diaria = diaria_unitaria or _money(valor_reserva / max(dias_locacao, 1))
    return _money(min(valor_reserva, faixa.valor_retencao * diaria))


# --------------------------------------------------------------------- Services
class TabelaTarifaService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = TabelaRepository(session)
        self.item_repo = TabelaItemRepository(session)

    async def list_items(
        self,
        params: PageParams,
        *,
        canal: TarifarioCanal | None = None,
        filial_id: uuid.UUID | None = None,
        status: CadastroStatus | None = None,
        search: str | None = None,
    ) -> Page[TarTabela]:
        return await self.repo.paginate(
            params,
            stmt=self.repo.list_query(
                canal=canal, filial_id=filial_id, status=status, search=search
            ),
        )

    async def get(self, tabela_id: uuid.UUID) -> TarTabela:
        item = await self.repo.get(tabela_id)
        if item is None:
            raise NotFoundError("Tabela de tarifas não encontrada.")
        return item

    async def list_itens(self, tabela_id: uuid.UUID) -> list[TarTabelaItem]:
        await self.get(tabela_id)
        stmt = self.item_repo.list_by_tabela(tabela_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def create(self, tenant_id: uuid.UUID, data: TabelaCreate) -> TarTabela:
        payload = data.model_dump(exclude={"itens"})
        item = TarTabela(tenant_id=tenant_id, **payload)
        self.repo.add(item)
        await self.repo.flush()
        for entry in data.itens:
            await self.add_item(tenant_id, item.id, entry)
        await audit_service.record(
            AuditAction.CREATE,
            entity="tar_tabela",
            entity_id=item.id,
            description=f"Tabela de tarifas criada: {item.nome}",
        )
        return item

    async def update(self, tabela_id: uuid.UUID, data: TabelaUpdate) -> TarTabela:
        item = await self.get(tabela_id)
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(item, k, v)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="tar_tabela",
            entity_id=item.id,
            description=f"Tabela de tarifas atualizada: {item.nome}",
        )
        return item

    async def delete(self, tabela_id: uuid.UUID) -> None:
        item = await self.get(tabela_id)
        await self.repo.delete(item)
        await audit_service.record(
            AuditAction.DELETE,
            entity="tar_tabela",
            entity_id=item.id,
            description=f"Tabela de tarifas excluída: {item.nome}",
        )

    async def add_item(
        self, tenant_id: uuid.UUID, tabela_id: uuid.UUID, data: TabelaItemCreate
    ) -> TarTabelaItem:
        await self.get(tabela_id)
        if await self.item_repo.get_by_tabela_categoria(tabela_id, data.categoria_id):
            raise ConflictError(
                "Categoria já cadastrada nesta tabela.", code="categoria_duplicada"
            )
        row = TarTabelaItem(tenant_id=tenant_id, tabela_id=tabela_id, **data.model_dump())
        self.item_repo.add(row)
        await self.item_repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="tar_tabela_item",
            entity_id=row.id,
            description=f"Item adicionado à tabela {tabela_id}",
        )
        return row

    async def update_item(
        self, tabela_id: uuid.UUID, item_id: uuid.UUID, data: TabelaItemUpdate
    ) -> TarTabelaItem:
        await self.get(tabela_id)
        row = await self.item_repo.get(item_id)
        if row is None or row.tabela_id != tabela_id:
            raise NotFoundError("Item da tabela não encontrado.")
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(row, k, v)
        await self.item_repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="tar_tabela_item",
            entity_id=row.id,
            description=f"Item atualizado na tabela {tabela_id}",
        )
        return row

    async def remove_item(self, tabela_id: uuid.UUID, item_id: uuid.UUID) -> None:
        await self.get(tabela_id)
        row = await self.item_repo.get(item_id)
        if row is None or row.tabela_id != tabela_id:
            raise NotFoundError("Item da tabela não encontrado.")
        await self.item_repo.delete(row)
        await audit_service.record(
            AuditAction.DELETE,
            entity="tar_tabela_item",
            entity_id=row.id,
            description=f"Item removido da tabela {tabela_id}",
        )


class TemporadaService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = TemporadaRepository(session)

    async def list_items(
        self,
        params: PageParams,
        *,
        filial_id: uuid.UUID | None = None,
        categoria_id: uuid.UUID | None = None,
        status: CadastroStatus | None = None,
        search: str | None = None,
    ) -> Page[TarTemporada]:
        return await self.repo.paginate(
            params,
            stmt=self.repo.list_query(
                filial_id=filial_id,
                categoria_id=categoria_id,
                status=status,
                search=search,
            ),
        )

    async def get(self, temporada_id: uuid.UUID) -> TarTemporada:
        item = await self.repo.get(temporada_id)
        if item is None:
            raise NotFoundError("Temporada não encontrada.")
        return item

    async def create(self, tenant_id: uuid.UUID, data: TemporadaCreate) -> TarTemporada:
        if data.data_fim < data.data_inicio:
            raise ValidationError("Data fim deve ser posterior à data início.")
        item = TarTemporada(tenant_id=tenant_id, **data.model_dump())
        self.repo.add(item)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="tar_temporada",
            entity_id=item.id,
            description=f"Temporada criada: {item.nome}",
        )
        return item

    async def update(self, temporada_id: uuid.UUID, data: TemporadaUpdate) -> TarTemporada:
        item = await self.get(temporada_id)
        payload = data.model_dump(exclude_unset=True)
        inicio = payload.get("data_inicio", item.data_inicio)
        fim = payload.get("data_fim", item.data_fim)
        if fim < inicio:
            raise ValidationError("Data fim deve ser posterior à data início.")
        for k, v in payload.items():
            setattr(item, k, v)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="tar_temporada",
            entity_id=item.id,
            description=f"Temporada atualizada: {item.nome}",
        )
        return item

    async def delete(self, temporada_id: uuid.UUID) -> None:
        item = await self.get(temporada_id)
        await self.repo.delete(item)
        await audit_service.record(
            AuditAction.DELETE,
            entity="tar_temporada",
            entity_id=item.id,
            description=f"Temporada excluída: {item.nome}",
        )


class TaxaService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = TaxaRepository(session)

    async def list_items(
        self,
        params: PageParams,
        *,
        aplicacao: TaxaAplicacao | None = None,
        status: CadastroStatus | None = None,
        search: str | None = None,
    ) -> Page[TarTaxa]:
        return await self.repo.paginate(
            params,
            stmt=self.repo.list_query(aplicacao=aplicacao, status=status, search=search),
        )

    async def get(self, taxa_id: uuid.UUID) -> TarTaxa:
        item = await self.repo.get(taxa_id)
        if item is None:
            raise NotFoundError("Taxa não encontrada.")
        return item

    async def create(self, tenant_id: uuid.UUID, data: TaxaCreate) -> TarTaxa:
        item = TarTaxa(tenant_id=tenant_id, **data.model_dump())
        self.repo.add(item)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="tar_taxa",
            entity_id=item.id,
            description=f"Taxa criada: {item.nome}",
        )
        return item

    async def update(self, taxa_id: uuid.UUID, data: TaxaUpdate) -> TarTaxa:
        item = await self.get(taxa_id)
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(item, k, v)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="tar_taxa",
            entity_id=item.id,
            description=f"Taxa atualizada: {item.nome}",
        )
        return item

    async def delete(self, taxa_id: uuid.UUID) -> None:
        item = await self.get(taxa_id)
        await self.repo.delete(item)
        await audit_service.record(
            AuditAction.DELETE,
            entity="tar_taxa",
            entity_id=item.id,
            description=f"Taxa excluída: {item.nome}",
        )


class ProtecaoService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ProtecaoRepository(session)
        self.cat_repo = ProtecaoCategoriaRepository(session)

    async def list_items(
        self,
        params: PageParams,
        *,
        status: CadastroStatus | None = None,
        search: str | None = None,
    ) -> Page[TarProtecao]:
        return await self.repo.paginate(
            params, stmt=self.repo.list_query(status=status, search=search)
        )

    async def get(self, protecao_id: uuid.UUID) -> TarProtecao:
        item = await self.repo.get(protecao_id)
        if item is None:
            raise NotFoundError("Proteção não encontrada.")
        return item

    async def list_categorias(self, protecao_id: uuid.UUID) -> list[TarProtecaoCategoria]:
        await self.get(protecao_id)
        stmt = self.cat_repo.list_by_protecao(protecao_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def create(self, tenant_id: uuid.UUID, data: ProtecaoCreate) -> TarProtecao:
        payload = data.model_dump(exclude={"categorias_obrigatorias"})
        item = TarProtecao(tenant_id=tenant_id, **payload)
        self.repo.add(item)
        await self.repo.flush()
        await self._sync_categorias(tenant_id, item.id, data.categorias_obrigatorias)
        await audit_service.record(
            AuditAction.CREATE,
            entity="tar_protecao",
            entity_id=item.id,
            description=f"Proteção criada: {item.nome}",
        )
        return item

    async def update(self, protecao_id: uuid.UUID, data: ProtecaoUpdate) -> TarProtecao:
        item = await self.get(protecao_id)
        payload = data.model_dump(exclude_unset=True, exclude={"categorias_obrigatorias"})
        for k, v in payload.items():
            setattr(item, k, v)
        await self.repo.flush()
        if data.categorias_obrigatorias is not None:
            await self._sync_categorias(
                item.tenant_id, item.id, data.categorias_obrigatorias
            )
        await audit_service.record(
            AuditAction.UPDATE,
            entity="tar_protecao",
            entity_id=item.id,
            description=f"Proteção atualizada: {item.nome}",
        )
        return item

    async def delete(self, protecao_id: uuid.UUID) -> None:
        item = await self.get(protecao_id)
        await self.cat_repo.delete_by_protecao(protecao_id)
        await self.repo.delete(item)
        await audit_service.record(
            AuditAction.DELETE,
            entity="tar_protecao",
            entity_id=item.id,
            description=f"Proteção excluída: {item.nome}",
        )

    async def link_categoria(
        self, tenant_id: uuid.UUID, protecao_id: uuid.UUID, categoria_id: uuid.UUID
    ) -> TarProtecaoCategoria:
        await self.get(protecao_id)
        stmt = (
            self.cat_repo._base_query()
            .where(
                TarProtecaoCategoria.protecao_id == protecao_id,
                TarProtecaoCategoria.categoria_id == categoria_id,
            )
            .limit(1)
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing:
            return existing
        row = TarProtecaoCategoria(
            tenant_id=tenant_id,
            protecao_id=protecao_id,
            categoria_id=categoria_id,
        )
        self.cat_repo.add(row)
        await self.cat_repo.flush()
        return row

    async def _sync_categorias(
        self, tenant_id: uuid.UUID, protecao_id: uuid.UUID, categoria_ids: list[uuid.UUID]
    ) -> None:
        await self.cat_repo.delete_by_protecao(protecao_id)
        for cat_id in categoria_ids:
            row = TarProtecaoCategoria(
                tenant_id=tenant_id,
                protecao_id=protecao_id,
                categoria_id=cat_id,
            )
            self.cat_repo.add(row)
        await self.cat_repo.flush()


class PoliticaCancelamentoService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PoliticaRepository(session)
        self.faixa_repo = PoliticaFaixaRepository(session)

    async def list_items(
        self,
        params: PageParams,
        *,
        canal: TarifarioCanal | None = None,
        status: CadastroStatus | None = None,
        search: str | None = None,
    ) -> Page[TarPoliticaCancelamento]:
        return await self.repo.paginate(
            params,
            stmt=self.repo.list_query(canal=canal, status=status, search=search),
        )

    async def get(self, politica_id: uuid.UUID) -> TarPoliticaCancelamento:
        item = await self.repo.get(politica_id)
        if item is None:
            raise NotFoundError("Política de cancelamento não encontrada.")
        return item

    async def list_faixas(self, politica_id: uuid.UUID) -> list[TarPoliticaFaixa]:
        await self.get(politica_id)
        stmt = self.faixa_repo.list_by_politica(politica_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def create(self, tenant_id: uuid.UUID, data: PoliticaCreate) -> TarPoliticaCancelamento:
        payload = data.model_dump(exclude={"faixas"})
        item = TarPoliticaCancelamento(tenant_id=tenant_id, **payload)
        self.repo.add(item)
        await self.repo.flush()
        for faixa in data.faixas:
            await self.add_faixa(tenant_id, item.id, faixa)
        await audit_service.record(
            AuditAction.CREATE,
            entity="tar_politica_cancelamento",
            entity_id=item.id,
            description=f"Política de cancelamento criada: {item.nome}",
        )
        return item

    async def update(
        self, politica_id: uuid.UUID, data: PoliticaUpdate
    ) -> TarPoliticaCancelamento:
        item = await self.get(politica_id)
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(item, k, v)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="tar_politica_cancelamento",
            entity_id=item.id,
            description=f"Política de cancelamento atualizada: {item.nome}",
        )
        return item

    async def delete(self, politica_id: uuid.UUID) -> None:
        item = await self.get(politica_id)
        await self.faixa_repo.delete_by_politica(politica_id)
        await self.repo.delete(item)
        await audit_service.record(
            AuditAction.DELETE,
            entity="tar_politica_cancelamento",
            entity_id=item.id,
            description=f"Política de cancelamento excluída: {item.nome}",
        )

    async def add_faixa(
        self, tenant_id: uuid.UUID, politica_id: uuid.UUID, data: PoliticaFaixaCreate
    ) -> TarPoliticaFaixa:
        await self.get(politica_id)
        row = TarPoliticaFaixa(tenant_id=tenant_id, politica_id=politica_id, **data.model_dump())
        self.faixa_repo.add(row)
        await self.faixa_repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="tar_politica_faixa",
            entity_id=row.id,
            description=f"Faixa adicionada à política {politica_id}",
        )
        return row

    async def update_faixa(
        self, politica_id: uuid.UUID, faixa_id: uuid.UUID, data: PoliticaFaixaUpdate
    ) -> TarPoliticaFaixa:
        await self.get(politica_id)
        row = await self.faixa_repo.get(faixa_id)
        if row is None or row.politica_id != politica_id:
            raise NotFoundError("Faixa da política não encontrada.")
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(row, k, v)
        await self.faixa_repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="tar_politica_faixa",
            entity_id=row.id,
            description=f"Faixa atualizada na política {politica_id}",
        )
        return row

    async def remove_faixa(self, politica_id: uuid.UUID, faixa_id: uuid.UUID) -> None:
        await self.get(politica_id)
        row = await self.faixa_repo.get(faixa_id)
        if row is None or row.politica_id != politica_id:
            raise NotFoundError("Faixa da política não encontrada.")
        await self.faixa_repo.delete(row)
        await audit_service.record(
            AuditAction.DELETE,
            entity="tar_politica_faixa",
            entity_id=row.id,
            description=f"Faixa removida da política {politica_id}",
        )


class PricingService:
    """Motor único de precificação consumido por reservas, cotações e API."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.tabela_repo = TabelaRepository(session)
        self.item_repo = TabelaItemRepository(session)
        self.temporada_repo = TemporadaRepository(session)
        self.taxa_repo = TaxaRepository(session)
        self.protecao_repo = ProtecaoRepository(session)
        self.protecao_cat_repo = ProtecaoCategoriaRepository(session)
        self.politica_repo = PoliticaRepository(session)
        self.faixa_repo = PoliticaFaixaRepository(session)

    async def calcular(self, input: PricingQuoteInput) -> PricingQuoteResult:
        if input.devolucao_em <= input.retirada_em:
            raise ValidationError("Data de devolução deve ser posterior à retirada.")

        dias = _calc_dias(input.retirada_em, input.devolucao_em)
        retirada_date = input.retirada_em.date()
        devolucao_date = input.devolucao_em.date()

        tabela = await self._resolver_tabela(input, retirada_date)
        tabela_item = await self._resolver_item_tabela(tabela.id, input.categoria_id)

        temporada = await self._resolver_temporada(
            input.tenant_id,
            filial_id=input.filial_id,
            categoria_id=input.categoria_id,
            retirada=retirada_date,
            devolucao=devolucao_date,
        )

        estadia_minima = temporada.estadia_minima if temporada else 1
        dias_cobrados = max(dias, estadia_minima)

        if (
            temporada
            and temporada.tipo_ajuste == TemporadaAjusteTipo.TABELA_ALTERNATIVA
            and temporada.tabela_alternativa_id
        ):
            alt_tabela = await self.tabela_repo.get(temporada.tabela_alternativa_id)
            if alt_tabela and alt_tabela.status == CadastroStatus.ACTIVE:
                alt_item = await self._resolver_item_tabela(
                    alt_tabela.id, input.categoria_id
                )
                tabela = alt_tabela
                tabela_item = alt_item

        diaria_unitaria = _pick_daily_rate(dias_cobrados, tabela_item)
        subtotal_diarias = _money(diaria_unitaria * dias_cobrados)
        temporada_ajuste = _ZERO

        if temporada and temporada.tipo_ajuste != TemporadaAjusteTipo.TABELA_ALTERNATIVA:
            if temporada.tipo_ajuste == TemporadaAjusteTipo.PERCENTUAL:
                temporada_ajuste = _money(
                    subtotal_diarias * temporada.valor_ajuste / Decimal("100")
                )
            elif temporada.tipo_ajuste == TemporadaAjusteTipo.VALOR_FIXO:
                temporada_ajuste = _money(temporada.valor_ajuste * dias_cobrados)

        base_com_temporada = subtotal_diarias + temporada_ajuste

        taxas_lines: list[PricingLineItem] = []
        protecoes_lines: list[PricingLineItem] = []
        acessorios_lines: list[PricingLineItem] = []

        taxas_auto_stmt = self.taxa_repo.list_query(
            aplicacao=TaxaAplicacao.AUTOMATICA, status=CadastroStatus.ACTIVE
        )
        taxas_auto = list((await self.session.execute(taxas_auto_stmt)).scalars().all())
        taxas_aplicadas: dict[uuid.UUID, TarTaxa] = {}

        for taxa in taxas_auto:
            if _regra_automatica_aplica(taxa.regra_codigo, one_way=input.one_way):
                taxas_aplicadas[taxa.id] = taxa

        for taxa_id in input.taxa_ids:
            taxa = await self.taxa_repo.get(taxa_id)
            if taxa and taxa.status == CadastroStatus.ACTIVE:
                taxas_aplicadas[taxa.id] = taxa

        for taxa in taxas_aplicadas.values():
            valor = _calc_taxa_valor(
                taxa,
                dias=dias_cobrados,
                base_diarias=base_com_temporada,
                total_parcial=base_com_temporada,
            )
            taxas_lines.append(
                PricingLineItem(
                    tipo="taxa",
                    referencia_id=taxa.id,
                    nome=taxa.nome,
                    quantidade=Decimal("1"),
                    valor_unitario=valor,
                    valor_total=valor,
                    automatica=taxa.aplicacao == TaxaAplicacao.AUTOMATICA,
                )
            )

        protecao_ids = set(input.protecao_ids)
        obrigatorias = await self.protecao_cat_repo.list_obrigatorias_por_categoria(
            input.categoria_id
        )
        for prot in obrigatorias:
            protecao_ids.add(prot.id)

        for protecao_id in protecao_ids:
            protecao = await self.protecao_repo.get(protecao_id)
            if protecao is None or protecao.status != CadastroStatus.ACTIVE:
                continue
            valor_total = _money(protecao.valor_diaria * dias_cobrados)
            protecoes_lines.append(
                PricingLineItem(
                    tipo="protecao",
                    referencia_id=protecao.id,
                    nome=protecao.nome,
                    quantidade=Decimal(str(dias_cobrados)),
                    valor_unitario=protecao.valor_diaria,
                    valor_total=valor_total,
                    automatica=protecao.obrigatoria,
                )
            )

        for acc_input in input.acessorio_ids:
            acessorio = await self._get_acessorio(acc_input.id)
            if acessorio is None:
                continue
            valor_total = _money(
                acessorio.valor_diaria * acc_input.qtd * dias_cobrados
            )
            acessorios_lines.append(
                PricingLineItem(
                    tipo="acessorio",
                    referencia_id=acessorio.id,
                    nome=acessorio.nome,
                    quantidade=Decimal(str(acc_input.qtd * dias_cobrados)),
                    valor_unitario=acessorio.valor_diaria,
                    valor_total=valor_total,
                )
            )

        subtotal_taxas = _money(sum((t.valor_total for t in taxas_lines), _ZERO))
        subtotal_protecoes = _money(sum((p.valor_total for p in protecoes_lines), _ZERO))
        subtotal_acessorios = _money(sum((a.valor_total for a in acessorios_lines), _ZERO))
        total = _money(
            base_com_temporada + subtotal_taxas + subtotal_protecoes + subtotal_acessorios
        )

        politica = await self._resolver_politica(input.tenant_id, input.canal)

        breakdown = {
            "dias": dias,
            "dias_cobrados": dias_cobrados,
            "diaria_unitaria": str(diaria_unitaria),
            "subtotal_diarias": str(subtotal_diarias),
            "temporada_ajuste": str(temporada_ajuste),
            "subtotal_taxas": str(subtotal_taxas),
            "subtotal_protecoes": str(subtotal_protecoes),
            "subtotal_acessorios": str(subtotal_acessorios),
            "total": str(total),
        }

        snapshot = {
            "input": input.model_dump(mode="json"),
            "tabela_id": str(tabela.id),
            "tabela_nome": tabela.nome,
            "temporada_id": str(temporada.id) if temporada else None,
            "politica_id": str(politica.id) if politica else None,
            "breakdown": breakdown,
            "taxas": [t.model_dump(mode="json") for t in taxas_lines],
            "protecoes": [p.model_dump(mode="json") for p in protecoes_lines],
            "acessorios": [a.model_dump(mode="json") for a in acessorios_lines],
        }

        return PricingQuoteResult(
            diaria_unitaria=diaria_unitaria,
            dias=dias,
            dias_cobrados=dias_cobrados,
            subtotal_diarias=subtotal_diarias,
            temporada_id=temporada.id if temporada else None,
            temporada_nome=temporada.nome if temporada else None,
            temporada_ajuste=temporada_ajuste,
            estadia_minima=estadia_minima,
            taxas=taxas_lines,
            protecoes=protecoes_lines,
            acessorios=acessorios_lines,
            subtotal_taxas=subtotal_taxas,
            subtotal_protecoes=subtotal_protecoes,
            subtotal_acessorios=subtotal_acessorios,
            total=total,
            tabela_id=tabela.id,
            tabela_nome=tabela.nome,
            politica_sugerida_id=politica.id if politica else None,
            km_livre=tabela_item.km_livre,
            km_incluido=tabela_item.km_incluido,
            valor_km_excedente=tabela_item.valor_km_excedente,
            breakdown=breakdown,
            snapshot=snapshot,
        )

    async def simular_cancelamento(
        self,
        politica_id: uuid.UUID,
        valor_reserva: Decimal,
        horas_antes_retirada: int,
        *,
        diaria_unitaria: Decimal | None = None,
        dias_locacao: int = 1,
    ) -> CancelamentoSimulacao:
        politica = await self.politica_repo.get(politica_id)
        if politica is None:
            raise NotFoundError("Política de cancelamento não encontrada.")

        faixas = await PoliticaCancelamentoService(self.session).list_faixas(politica_id)
        faixa_match: TarPoliticaFaixa | None = None
        for faixa in faixas:
            if horas_antes_retirada < faixa.horas_antes_min:
                continue
            if faixa.horas_antes_max is not None and horas_antes_retirada >= faixa.horas_antes_max:
                continue
            faixa_match = faixa
            break

        if faixa_match is None:
            return CancelamentoSimulacao(
                politica_id=politica_id,
                faixa_id=None,
                horas_antes_retirada=horas_antes_retirada,
                valor_reserva=valor_reserva,
                valor_retencao=_ZERO,
                valor_estorno=valor_reserva,
                descricao_faixa="Sem penalidade (faixa não encontrada)",
            )

        retencao = _retencao_valor(
            faixa_match,
            valor_reserva=valor_reserva,
            diaria_unitaria=diaria_unitaria,
            dias_locacao=dias_locacao,
        )
        estorno = _money(max(_ZERO, valor_reserva - retencao))

        max_desc = (
            f"{faixa_match.horas_antes_min}h"
            if faixa_match.horas_antes_max is None
            else f"{faixa_match.horas_antes_min}-{faixa_match.horas_antes_max}h"
        )

        return CancelamentoSimulacao(
            politica_id=politica_id,
            faixa_id=faixa_match.id,
            horas_antes_retirada=horas_antes_retirada,
            valor_reserva=valor_reserva,
            valor_retencao=retencao,
            valor_estorno=estorno,
            tipo_retencao=faixa_match.tipo_retencao,
            descricao_faixa=max_desc,
        )

    async def ensure_defaults(self, tenant_id: uuid.UUID) -> None:
        taxa_stmt = select(func.count()).select_from(TarTaxa).where(
            TarTaxa.tenant_id == tenant_id,
            TarTaxa.deleted_at.is_(None),
        )
        if (await self.session.execute(taxa_stmt)).scalar_one() == 0:
            defaults_taxas = [
                TaxaCreate(
                    nome="Taxa One-Way",
                    descricao="Retirada e devolução em filiais diferentes",
                    tipo_calculo=TaxaCalculoTipo.FIXO,
                    valor=Decimal("150.00"),
                    aplicacao=TaxaAplicacao.AUTOMATICA,
                    regra_codigo="one_way",
                ),
                TaxaCreate(
                    nome="Condutor Adicional",
                    descricao="Taxa por condutor extra",
                    tipo_calculo=TaxaCalculoTipo.POR_OCORRENCIA,
                    valor=Decimal("25.00"),
                    aplicacao=TaxaAplicacao.OPCIONAL,
                    regra_codigo="condutor_adicional",
                ),
                TaxaCreate(
                    nome="Taxa de Limpeza",
                    descricao="Limpeza extraordinária",
                    tipo_calculo=TaxaCalculoTipo.FIXO,
                    valor=Decimal("80.00"),
                    aplicacao=TaxaAplicacao.OPCIONAL,
                    regra_codigo="limpeza",
                ),
            ]
            taxa_svc = TaxaService(self.session)
            for entry in defaults_taxas:
                await taxa_svc.create(tenant_id, entry)

        prot_stmt = select(func.count()).select_from(TarProtecao).where(
            TarProtecao.tenant_id == tenant_id,
            TarProtecao.deleted_at.is_(None),
        )
        if (await self.session.execute(prot_stmt)).scalar_one() == 0:
            prot_svc = ProtecaoService(self.session)
            await prot_svc.create(
                tenant_id,
                ProtecaoCreate(
                    nome="LDW — Isenção de Danos",
                    descricao="Proteção contra danos ao veículo locado",
                    valor_diaria=Decimal("35.00"),
                    franquia=Decimal("1500.00"),
                ),
            )
            await prot_svc.create(
                tenant_id,
                ProtecaoCreate(
                    nome="TP — Proteção a Terceiros",
                    descricao="Cobertura de danos a terceiros",
                    valor_diaria=Decimal("20.00"),
                    franquia=Decimal("0.00"),
                ),
            )

        pol_stmt = select(func.count()).select_from(TarPoliticaCancelamento).where(
            TarPoliticaCancelamento.tenant_id == tenant_id,
            TarPoliticaCancelamento.deleted_at.is_(None),
        )
        if (await self.session.execute(pol_stmt)).scalar_one() == 0:
            pol_svc = PoliticaCancelamentoService(self.session)
            await pol_svc.create(
                tenant_id,
                PoliticaCreate(
                    nome="Política Padrão",
                    descricao="Cancelamento flexível com retenção progressiva",
                    faixas=[
                        PoliticaFaixaCreate(
                            horas_antes_min=72,
                            horas_antes_max=None,
                            tipo_retencao=PoliticaRetencaoTipo.PERCENTUAL,
                            valor_retencao=Decimal("0"),
                            ordem=1,
                        ),
                        PoliticaFaixaCreate(
                            horas_antes_min=24,
                            horas_antes_max=72,
                            tipo_retencao=PoliticaRetencaoTipo.PERCENTUAL,
                            valor_retencao=Decimal("20"),
                            ordem=2,
                        ),
                        PoliticaFaixaCreate(
                            horas_antes_min=0,
                            horas_antes_max=24,
                            tipo_retencao=PoliticaRetencaoTipo.DIARIAS,
                            valor_retencao=Decimal("1"),
                            ordem=3,
                        ),
                    ],
                ),
            )

    async def _resolver_tabela(
        self, input: PricingQuoteInput, ref_date: date
    ) -> TarTabela:
        stmt = (
            self.tabela_repo._base_query()
            .where(
                TarTabela.tenant_id == input.tenant_id,
                TarTabela.status == CadastroStatus.ACTIVE,
            )
            .order_by(TarTabela.prioridade.desc(), TarTabela.vigencia_inicio.desc())
        )
        candidatas = list((await self.session.execute(stmt)).scalars().all())

        def _score(t: TarTabela) -> tuple[int, int, int]:
            tier = 0
            if input.cliente_id and t.cliente_id == input.cliente_id:
                tier = 3
            elif input.parceiro_id and t.parceiro_id == input.parceiro_id:
                tier = 2
            elif t.cliente_id is None and t.parceiro_id is None:
                tier = 1
            else:
                tier = 0
            filial_match = 1 if (t.filial_id is None or t.filial_id == input.filial_id) else 0
            canal_match = 1 if _canal_matches(t.canal, input.canal) else 0
            vigente = 1 if _vigencia_matches(t, ref_date) else 0
            return (tier, filial_match * canal_match * vigente, t.prioridade)

        elegiveis = [
            t
            for t in candidatas
            if _score(t)[0] > 0
            and (t.filial_id is None or t.filial_id == input.filial_id)
            and _canal_matches(t.canal, input.canal)
            and _vigencia_matches(t, ref_date)
        ]

        if not elegiveis:
            raise NotFoundError(
                "Nenhuma tabela de tarifas vigente encontrada para os critérios informados."
            )

        elegiveis.sort(key=_score, reverse=True)
        return elegiveis[0]

    async def _resolver_item_tabela(
        self, tabela_id: uuid.UUID, categoria_id: uuid.UUID
    ) -> TarTabelaItem:
        item = await self.item_repo.get_by_tabela_categoria(tabela_id, categoria_id)
        if item is None:
            raise NotFoundError(
                "Categoria sem valores cadastrados na tabela de tarifas selecionada."
            )
        return item

    async def _resolver_temporada(
        self,
        tenant_id: uuid.UUID,
        *,
        filial_id: uuid.UUID,
        categoria_id: uuid.UUID,
        retirada: date,
        devolucao: date,
    ) -> TarTemporada | None:
        stmt = (
            self.temporada_repo._base_query()
            .where(
                TarTemporada.tenant_id == tenant_id,
                TarTemporada.status == CadastroStatus.ACTIVE,
            )
        )
        temporadas = list((await self.session.execute(stmt)).scalars().all())
        candidatas = [
            t
            for t in temporadas
            if _periodo_intersecta(t.data_inicio, t.data_fim, retirada, devolucao)
            and (t.filial_id is None or t.filial_id == filial_id)
            and (t.categoria_id is None or t.categoria_id == categoria_id)
        ]
        if not candidatas:
            return None
        candidatas.sort(
            key=lambda t: (
                _temporada_especificidade(t, filial_id, categoria_id),
                t.prioridade,
            ),
            reverse=True,
        )
        return candidatas[0]

    async def _resolver_politica(
        self, tenant_id: uuid.UUID, canal: TarifarioCanal
    ) -> TarPoliticaCancelamento | None:
        stmt = (
            self.politica_repo._base_query()
            .where(
                TarPoliticaCancelamento.tenant_id == tenant_id,
                TarPoliticaCancelamento.status == CadastroStatus.ACTIVE,
                or_(
                    TarPoliticaCancelamento.canal == canal,
                    TarPoliticaCancelamento.canal == TarifarioCanal.TODOS,
                ),
            )
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _get_acessorio(self, acessorio_id: uuid.UUID) -> FrotaAcessorio | None:
        stmt = select(FrotaAcessorio).where(
            FrotaAcessorio.id == acessorio_id,
            FrotaAcessorio.deleted_at.is_(None),
            FrotaAcessorio.status == CadastroStatus.ACTIVE,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()
