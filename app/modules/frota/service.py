"""Serviços de negócio do módulo Frota."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Generic, TypeVar

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.pagination import Page, PageParams
from app.modules.audit.service import audit_service
from app.modules.frota.models import (
    FrotaAcessorio,
    FrotaCategoria,
    FrotaCombustivel,
    FrotaDocumento,
    FrotaMarca,
    FrotaModelo,
    FrotaTelemetriaDispositivo,
    FrotaTelemetriaEvento,
    FrotaVeiculo,
    FrotaVeiculoAcessorio,
    FrotaVeiculoFoto,
)
from app.modules.frota.schemas import (
    AcessorioCreate,
    AcessorioUpdate,
    CategoriaCreate,
    CategoriaUpdate,
    CombustivelCreate,
    CombustivelUpdate,
    DocumentoCreate,
    DocumentoUpdate,
    MarcaCreate,
    MarcaUpdate,
    ModeloCreate,
    ModeloUpdate,
    TelemetriaDispositivoUpsert,
    TelemetriaEventoCreate,
    VeiculoAcessorioLink,
    VeiculoCreate,
    VeiculoFotoCreate,
    VeiculoFotoUpdate,
    VeiculoUpdate,
)
from app.shared.base_model import TenantBaseModel
from app.shared.enums import (
    AuditAction,
    CadastroStatus,
    CombustivelUnidade,
    DocumentoVeiculoStatus,
    DocumentoVeiculoTipo,
    VeiculoStatus,
)
from app.shared.repository import BaseRepository

ModelT = TypeVar("ModelT", bound=TenantBaseModel)

# ------------------------------------------------------------------ Defaults
DEFAULT_CATEGORIAS: tuple[tuple[str, int], ...] = (
    ("Economico", 10),
    ("Compacto", 20),
    ("Sedan", 30),
    ("SUV", 40),
    ("Executivo", 50),
    ("Utilitario", 60),
    ("Blindado", 70),
)

DEFAULT_COMBUSTIVEIS: tuple[tuple[str, CombustivelUnidade, Decimal], ...] = (
    ("Gasolina", CombustivelUnidade.LITRO, Decimal("5.89")),
    ("Etanol", CombustivelUnidade.LITRO, Decimal("3.79")),
    ("Flex", CombustivelUnidade.LITRO, Decimal("5.89")),
    ("Diesel", CombustivelUnidade.LITRO, Decimal("6.19")),
    ("GNV", CombustivelUnidade.M3, Decimal("4.50")),
    ("Eletrico", CombustivelUnidade.KWH, Decimal("0.85")),
    ("Hibrido", CombustivelUnidade.LITRO, Decimal("5.89")),
)

DEFAULT_MARCAS: tuple[str, ...] = (
    "Fiat",
    "Chevrolet",
    "Volkswagen",
    "Toyota",
    "Hyundai",
    "Renault",
    "Honda",
    "Jeep",
)

VEICULO_TRANSITIONS: dict[VeiculoStatus, set[VeiculoStatus]] = {
    VeiculoStatus.DISPONIVEL: {
        VeiculoStatus.RESERVADO,
        VeiculoStatus.LOCADO,
        VeiculoStatus.MANUTENCAO,
        VeiculoStatus.BLOQUEADO,
        VeiculoStatus.RESTRITO,
        VeiculoStatus.BAIXADO,
    },
    VeiculoStatus.RESERVADO: {
        VeiculoStatus.DISPONIVEL,
        VeiculoStatus.LOCADO,
        VeiculoStatus.BLOQUEADO,
        VeiculoStatus.RESTRITO,
        VeiculoStatus.BAIXADO,
    },
    VeiculoStatus.LOCADO: {
        VeiculoStatus.DISPONIVEL,
        VeiculoStatus.MANUTENCAO,
        VeiculoStatus.BLOQUEADO,
        VeiculoStatus.BAIXADO,
    },
    VeiculoStatus.MANUTENCAO: {
        VeiculoStatus.DISPONIVEL,
        VeiculoStatus.BLOQUEADO,
        VeiculoStatus.RESTRITO,
        VeiculoStatus.BAIXADO,
    },
    VeiculoStatus.BLOQUEADO: {
        VeiculoStatus.DISPONIVEL,
        VeiculoStatus.RESTRITO,
        VeiculoStatus.BAIXADO,
    },
    VeiculoStatus.RESTRITO: {
        VeiculoStatus.DISPONIVEL,
        VeiculoStatus.BLOQUEADO,
        VeiculoStatus.BAIXADO,
    },
    VeiculoStatus.BAIXADO: set(),
}

_SYNC_RESTRITO_FROM = {
    VeiculoStatus.DISPONIVEL,
    VeiculoStatus.RESERVADO,
    VeiculoStatus.RESTRITO,
}


class _NamedRepo(BaseRepository[ModelT], Generic[ModelT]):
    def search_by_nome(self, search: str | None = None) -> Select[tuple[ModelT]]:
        stmt = self._base_query().order_by(self.model.nome.asc())  # type: ignore[attr-defined]
        if search:
            term = f"%{search.strip().lower()}%"
            stmt = stmt.where(func.lower(self.model.nome).like(term))  # type: ignore[attr-defined]
        return stmt


async def ensure_frota_defaults(session: AsyncSession, tenant_id: uuid.UUID) -> None:
    """Garante categorias, combustíveis e marcas padrão (idempotente)."""
    for nome, ordem in DEFAULT_CATEGORIAS:
        exists = (
            await session.execute(
                select(FrotaCategoria.id)
                .where(
                    FrotaCategoria.tenant_id == tenant_id,
                    FrotaCategoria.nome == nome,
                    FrotaCategoria.deleted_at.is_(None),
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if exists is None:
            session.add(
                FrotaCategoria(
                    tenant_id=tenant_id,
                    nome=nome,
                    ordem=ordem,
                    status=CadastroStatus.ACTIVE,
                )
            )

    for nome, unidade, preco in DEFAULT_COMBUSTIVEIS:
        exists = (
            await session.execute(
                select(FrotaCombustivel.id)
                .where(
                    FrotaCombustivel.tenant_id == tenant_id,
                    FrotaCombustivel.nome == nome,
                    FrotaCombustivel.deleted_at.is_(None),
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if exists is None:
            session.add(
                FrotaCombustivel(
                    tenant_id=tenant_id,
                    nome=nome,
                    unidade=unidade,
                    preco_referencia=preco,
                    status=CadastroStatus.ACTIVE,
                )
            )

    for nome in DEFAULT_MARCAS:
        exists = (
            await session.execute(
                select(FrotaMarca.id)
                .where(
                    FrotaMarca.tenant_id == tenant_id,
                    FrotaMarca.nome == nome,
                    FrotaMarca.deleted_at.is_(None),
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if exists is None:
            session.add(
                FrotaMarca(tenant_id=tenant_id, nome=nome, status=CadastroStatus.ACTIVE)
            )

    await session.flush()


def _derive_documento_status(validade: date | None) -> DocumentoVeiculoStatus:
    if validade is None:
        return DocumentoVeiculoStatus.REGULAR
    today = date.today()
    if validade < today:
        return DocumentoVeiculoStatus.VENCIDO
    if validade <= today + timedelta(days=30):
        return DocumentoVeiculoStatus.A_VENCER
    return DocumentoVeiculoStatus.REGULAR


# ---------------------------------------------------------------- Repositories
class CategoriaRepository(_NamedRepo[FrotaCategoria]):
    model = FrotaCategoria

    async def count_veiculos(self, categoria_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(FrotaVeiculo)
            .where(
                FrotaVeiculo.categoria_id == categoria_id,
                FrotaVeiculo.deleted_at.is_(None),
            )
        )
        return (await self.session.execute(stmt)).scalar_one()


class MarcaRepository(_NamedRepo[FrotaMarca]):
    model = FrotaMarca

    async def count_modelos(self, marca_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(FrotaModelo)
            .where(FrotaModelo.marca_id == marca_id, FrotaModelo.deleted_at.is_(None))
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def count_veiculos(self, marca_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(FrotaVeiculo)
            .where(FrotaVeiculo.marca_id == marca_id, FrotaVeiculo.deleted_at.is_(None))
        )
        return (await self.session.execute(stmt)).scalar_one()


class CombustivelRepository(_NamedRepo[FrotaCombustivel]):
    model = FrotaCombustivel

    async def count_veiculos(self, combustivel_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(FrotaVeiculo)
            .where(
                FrotaVeiculo.combustivel_id == combustivel_id,
                FrotaVeiculo.deleted_at.is_(None),
            )
        )
        return (await self.session.execute(stmt)).scalar_one()


class ModeloRepository(_NamedRepo[FrotaModelo]):
    model = FrotaModelo

    def query_by_marca(self, marca_id: uuid.UUID | None = None) -> Select[tuple[FrotaModelo]]:
        stmt = self._base_query().order_by(FrotaModelo.nome.asc())
        if marca_id:
            stmt = stmt.where(FrotaModelo.marca_id == marca_id)
        return stmt

    async def count_veiculos(self, modelo_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(FrotaVeiculo)
            .where(FrotaVeiculo.modelo_id == modelo_id, FrotaVeiculo.deleted_at.is_(None))
        )
        return (await self.session.execute(stmt)).scalar_one()


class AcessorioRepository(_NamedRepo[FrotaAcessorio]):
    model = FrotaAcessorio

    async def count_vinculos(self, acessorio_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(FrotaVeiculoAcessorio)
            .where(
                FrotaVeiculoAcessorio.acessorio_id == acessorio_id,
                FrotaVeiculoAcessorio.deleted_at.is_(None),
            )
        )
        return (await self.session.execute(stmt)).scalar_one()


class VeiculoRepository(BaseRepository[FrotaVeiculo]):
    model = FrotaVeiculo

    async def get_by_placa(self, placa: str) -> FrotaVeiculo | None:
        stmt = self._base_query().where(FrotaVeiculo.placa == placa).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_renavam(self, renavam: str) -> FrotaVeiculo | None:
        stmt = self._base_query().where(FrotaVeiculo.renavam == renavam).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_chassi(self, chassi: str) -> FrotaVeiculo | None:
        stmt = self._base_query().where(FrotaVeiculo.chassi == chassi).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    def search_query(
        self,
        *,
        search: str | None = None,
        status: VeiculoStatus | None = None,
        categoria_id: uuid.UUID | None = None,
        filial_id: uuid.UUID | None = None,
    ) -> Select[tuple[FrotaVeiculo]]:
        stmt = self._base_query().order_by(FrotaVeiculo.placa.asc())
        if status:
            stmt = stmt.where(FrotaVeiculo.status == status)
        if categoria_id:
            stmt = stmt.where(FrotaVeiculo.categoria_id == categoria_id)
        if filial_id:
            stmt = stmt.where(FrotaVeiculo.filial_id == filial_id)
        if search:
            term = f"%{search.strip().lower()}%"
            filters = [func.lower(FrotaVeiculo.placa).like(term)]
            if search.strip():
                filters.append(func.lower(func.coalesce(FrotaVeiculo.chassi, "")).like(term))
            stmt = stmt.where(or_(*filters))
        return stmt


class VeiculoAcessorioRepository(BaseRepository[FrotaVeiculoAcessorio]):
    model = FrotaVeiculoAcessorio

    async def get_vinculo(
        self, veiculo_id: uuid.UUID, acessorio_id: uuid.UUID
    ) -> FrotaVeiculoAcessorio | None:
        stmt = (
            self._base_query()
            .where(
                FrotaVeiculoAcessorio.veiculo_id == veiculo_id,
                FrotaVeiculoAcessorio.acessorio_id == acessorio_id,
            )
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    def list_by_veiculo(self, veiculo_id: uuid.UUID) -> Select[tuple[FrotaVeiculoAcessorio]]:
        return (
            self._base_query()
            .where(FrotaVeiculoAcessorio.veiculo_id == veiculo_id)
            .order_by(FrotaVeiculoAcessorio.created_at.asc())
        )


class FotoRepository(BaseRepository[FrotaVeiculoFoto]):
    model = FrotaVeiculoFoto

    def list_by_veiculo(self, veiculo_id: uuid.UUID) -> Select[tuple[FrotaVeiculoFoto]]:
        return (
            self._base_query()
            .where(FrotaVeiculoFoto.veiculo_id == veiculo_id)
            .order_by(FrotaVeiculoFoto.ordem.asc(), FrotaVeiculoFoto.created_at.asc())
        )


class DocumentoRepository(BaseRepository[FrotaDocumento]):
    model = FrotaDocumento

    def list_query(
        self,
        *,
        veiculo_id: uuid.UUID | None = None,
        status: DocumentoVeiculoStatus | None = None,
        tipo: DocumentoVeiculoTipo | None = None,
    ) -> Select[tuple[FrotaDocumento]]:
        stmt = self._base_query().order_by(FrotaDocumento.data_validade.asc().nullslast())
        if veiculo_id:
            stmt = stmt.where(FrotaDocumento.veiculo_id == veiculo_id)
        if status:
            stmt = stmt.where(FrotaDocumento.status == status)
        if tipo:
            stmt = stmt.where(FrotaDocumento.tipo == tipo)
        return stmt

    async def has_vencidos(self, veiculo_id: uuid.UUID) -> bool:
        stmt = (
            select(func.count())
            .select_from(FrotaDocumento)
            .where(
                FrotaDocumento.veiculo_id == veiculo_id,
                FrotaDocumento.deleted_at.is_(None),
                FrotaDocumento.status == DocumentoVeiculoStatus.VENCIDO,
            )
        )
        return (await self.session.execute(stmt)).scalar_one() > 0

    def vencimentos_query(self, days: int) -> Select[tuple[FrotaDocumento]]:
        today = date.today()
        deadline = today + timedelta(days=days)
        return (
            self._base_query()
            .where(
                FrotaDocumento.data_validade.is_not(None),
                FrotaDocumento.data_validade <= deadline,
            )
            .order_by(FrotaDocumento.data_validade.asc())
        )


class TelemetriaDispositivoRepository(BaseRepository[FrotaTelemetriaDispositivo]):
    model = FrotaTelemetriaDispositivo

    async def get_by_veiculo(self, veiculo_id: uuid.UUID) -> FrotaTelemetriaDispositivo | None:
        stmt = (
            self._base_query()
            .where(FrotaTelemetriaDispositivo.veiculo_id == veiculo_id)
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    def list_query(self) -> Select[tuple[FrotaTelemetriaDispositivo]]:
        return self._base_query().order_by(FrotaTelemetriaDispositivo.created_at.desc())


class TelemetriaEventoRepository(BaseRepository[FrotaTelemetriaEvento]):
    model = FrotaTelemetriaEvento

    def list_by_veiculo(self, veiculo_id: uuid.UUID) -> Select[tuple[FrotaTelemetriaEvento]]:
        return (
            self._base_query()
            .where(FrotaTelemetriaEvento.veiculo_id == veiculo_id)
            .order_by(FrotaTelemetriaEvento.ocorrido_em.desc())
        )


# --------------------------------------------------------------------- Services
class CategoriasService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CategoriaRepository(session)

    async def ensure_defaults(self, tenant_id: uuid.UUID) -> None:
        await ensure_frota_defaults(self.session, tenant_id)

    async def list_items(
        self, params: PageParams, *, search: str | None = None
    ) -> Page[FrotaCategoria]:
        return await self.repo.paginate(params, stmt=self.repo.search_by_nome(search))

    async def get(self, item_id: uuid.UUID) -> FrotaCategoria:
        item = await self.repo.get(item_id)
        if item is None:
            raise NotFoundError("Categoria não encontrada.")
        return item

    async def create(self, tenant_id: uuid.UUID, data: CategoriaCreate) -> FrotaCategoria:
        item = FrotaCategoria(tenant_id=tenant_id, **data.model_dump())
        self.repo.add(item)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.CREATE, entity="frota_categoria", entity_id=item.id,
            description=f"Categoria criada: {item.nome}",
        )
        return item

    async def update(self, item_id: uuid.UUID, data: CategoriaUpdate) -> FrotaCategoria:
        item = await self.get(item_id)
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(item, k, v)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE, entity="frota_categoria", entity_id=item.id,
            description=f"Categoria atualizada: {item.nome}",
        )
        return item

    async def delete(self, item_id: uuid.UUID) -> None:
        item = await self.get(item_id)
        if await self.repo.count_veiculos(item.id):
            raise ConflictError(
                "Categoria possui veículos vinculados.", code="categoria_em_uso"
            )
        await self.repo.delete(item)
        await audit_service.record(
            AuditAction.DELETE, entity="frota_categoria", entity_id=item.id,
            description=f"Categoria excluída: {item.nome}",
        )


class MarcasService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = MarcaRepository(session)

    async def ensure_defaults(self, tenant_id: uuid.UUID) -> None:
        await ensure_frota_defaults(self.session, tenant_id)

    async def list_items(self, params: PageParams, *, search: str | None = None) -> Page[FrotaMarca]:
        return await self.repo.paginate(params, stmt=self.repo.search_by_nome(search))

    async def get(self, item_id: uuid.UUID) -> FrotaMarca:
        item = await self.repo.get(item_id)
        if item is None:
            raise NotFoundError("Marca não encontrada.")
        return item

    async def create(self, tenant_id: uuid.UUID, data: MarcaCreate) -> FrotaMarca:
        item = FrotaMarca(tenant_id=tenant_id, **data.model_dump())
        self.repo.add(item)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.CREATE, entity="frota_marca", entity_id=item.id,
            description=f"Marca criada: {item.nome}",
        )
        return item

    async def update(self, item_id: uuid.UUID, data: MarcaUpdate) -> FrotaMarca:
        item = await self.get(item_id)
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(item, k, v)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE, entity="frota_marca", entity_id=item.id,
            description=f"Marca atualizada: {item.nome}",
        )
        return item

    async def delete(self, item_id: uuid.UUID) -> None:
        item = await self.get(item_id)
        if await self.repo.count_modelos(item.id):
            raise ConflictError("Marca possui modelos vinculados.", code="marca_em_uso")
        if await self.repo.count_veiculos(item.id):
            raise ConflictError("Marca possui veículos vinculados.", code="marca_em_uso")
        await self.repo.delete(item)
        await audit_service.record(
            AuditAction.DELETE, entity="frota_marca", entity_id=item.id,
            description=f"Marca excluída: {item.nome}",
        )


class CombustiveisService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CombustivelRepository(session)

    async def ensure_defaults(self, tenant_id: uuid.UUID) -> None:
        await ensure_frota_defaults(self.session, tenant_id)

    async def list_items(
        self, params: PageParams, *, search: str | None = None
    ) -> Page[FrotaCombustivel]:
        return await self.repo.paginate(params, stmt=self.repo.search_by_nome(search))

    async def get(self, item_id: uuid.UUID) -> FrotaCombustivel:
        item = await self.repo.get(item_id)
        if item is None:
            raise NotFoundError("Combustível não encontrado.")
        return item

    async def create(self, tenant_id: uuid.UUID, data: CombustivelCreate) -> FrotaCombustivel:
        item = FrotaCombustivel(tenant_id=tenant_id, **data.model_dump())
        self.repo.add(item)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.CREATE, entity="frota_combustivel", entity_id=item.id,
            description=f"Combustível criado: {item.nome}",
        )
        return item

    async def update(self, item_id: uuid.UUID, data: CombustivelUpdate) -> FrotaCombustivel:
        item = await self.get(item_id)
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(item, k, v)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE, entity="frota_combustivel", entity_id=item.id,
            description=f"Combustível atualizado: {item.nome}",
        )
        return item

    async def delete(self, item_id: uuid.UUID) -> None:
        item = await self.get(item_id)
        if await self.repo.count_veiculos(item.id):
            raise ConflictError(
                "Combustível possui veículos vinculados.", code="combustivel_em_uso"
            )
        await self.repo.delete(item)
        await audit_service.record(
            AuditAction.DELETE, entity="frota_combustivel", entity_id=item.id,
            description=f"Combustível excluído: {item.nome}",
        )


class ModelosService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ModeloRepository(session)
        self.marcas = MarcaRepository(session)
        self.categorias = CategoriaRepository(session)

    async def list_items(
        self,
        params: PageParams,
        *,
        search: str | None = None,
        marca_id: uuid.UUID | None = None,
    ) -> Page[FrotaModelo]:
        stmt = self.repo.query_by_marca(marca_id)
        if search:
            term = f"%{search.strip().lower()}%"
            stmt = stmt.where(func.lower(FrotaModelo.nome).like(term))
        return await self.repo.paginate(params, stmt=stmt)

    async def get(self, item_id: uuid.UUID) -> FrotaModelo:
        item = await self.repo.get(item_id)
        if item is None:
            raise NotFoundError("Modelo não encontrado.")
        return item

    async def create(self, tenant_id: uuid.UUID, data: ModeloCreate) -> FrotaModelo:
        await self._assert_marca(data.marca_id)
        if data.categoria_padrao_id:
            await self._assert_categoria(data.categoria_padrao_id)
        item = FrotaModelo(tenant_id=tenant_id, **data.model_dump())
        self.repo.add(item)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.CREATE, entity="frota_modelo", entity_id=item.id,
            description=f"Modelo criado: {item.nome}",
        )
        return item

    async def update(self, item_id: uuid.UUID, data: ModeloUpdate) -> FrotaModelo:
        item = await self.get(item_id)
        payload = data.model_dump(exclude_unset=True)
        if "marca_id" in payload:
            await self._assert_marca(payload["marca_id"])
        if payload.get("categoria_padrao_id"):
            await self._assert_categoria(payload["categoria_padrao_id"])
        for k, v in payload.items():
            setattr(item, k, v)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE, entity="frota_modelo", entity_id=item.id,
            description=f"Modelo atualizado: {item.nome}",
        )
        return item

    async def delete(self, item_id: uuid.UUID) -> None:
        item = await self.get(item_id)
        if await self.repo.count_veiculos(item.id):
            raise ConflictError("Modelo possui veículos vinculados.", code="modelo_em_uso")
        await self.repo.delete(item)
        await audit_service.record(
            AuditAction.DELETE, entity="frota_modelo", entity_id=item.id,
            description=f"Modelo excluído: {item.nome}",
        )

    async def _assert_marca(self, marca_id: uuid.UUID) -> None:
        if await self.marcas.get(marca_id) is None:
            raise ValidationError("Marca inválida.")

    async def _assert_categoria(self, categoria_id: uuid.UUID) -> None:
        if await self.categorias.get(categoria_id) is None:
            raise ValidationError("Categoria inválida.")


class AcessoriosService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AcessorioRepository(session)

    async def list_items(
        self, params: PageParams, *, search: str | None = None
    ) -> Page[FrotaAcessorio]:
        return await self.repo.paginate(params, stmt=self.repo.search_by_nome(search))

    async def get(self, item_id: uuid.UUID) -> FrotaAcessorio:
        item = await self.repo.get(item_id)
        if item is None:
            raise NotFoundError("Acessório não encontrado.")
        return item

    async def create(self, tenant_id: uuid.UUID, data: AcessorioCreate) -> FrotaAcessorio:
        item = FrotaAcessorio(tenant_id=tenant_id, **data.model_dump())
        self.repo.add(item)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.CREATE, entity="frota_acessorio", entity_id=item.id,
            description=f"Acessório criado: {item.nome}",
        )
        return item

    async def update(self, item_id: uuid.UUID, data: AcessorioUpdate) -> FrotaAcessorio:
        item = await self.get(item_id)
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(item, k, v)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE, entity="frota_acessorio", entity_id=item.id,
            description=f"Acessório atualizado: {item.nome}",
        )
        return item

    async def delete(self, item_id: uuid.UUID) -> None:
        item = await self.get(item_id)
        if await self.repo.count_vinculos(item.id):
            raise ConflictError(
                "Acessório possui veículos vinculados.", code="acessorio_em_uso"
            )
        await self.repo.delete(item)
        await audit_service.record(
            AuditAction.DELETE, entity="frota_acessorio", entity_id=item.id,
            description=f"Acessório excluído: {item.nome}",
        )


class VeiculoService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = VeiculoRepository(session)
        self.modelos = ModeloRepository(session)
        self.categorias = CategoriaRepository(session)
        self.marcas = MarcaRepository(session)
        self.combustiveis = CombustivelRepository(session)
        self.acessorio_repo = VeiculoAcessorioRepository(session)
        self.acessorios = AcessorioRepository(session)

    async def list_items(
        self,
        params: PageParams,
        *,
        search: str | None = None,
        status: VeiculoStatus | None = None,
        categoria_id: uuid.UUID | None = None,
        filial_id: uuid.UUID | None = None,
    ) -> Page[FrotaVeiculo]:
        stmt = self.repo.search_query(
            search=search, status=status, categoria_id=categoria_id, filial_id=filial_id
        )
        return await self.repo.paginate(params, stmt=stmt)

    async def get(self, item_id: uuid.UUID) -> FrotaVeiculo:
        item = await self.repo.get(item_id)
        if item is None:
            raise NotFoundError("Veículo não encontrado.")
        return item

    async def create(self, tenant_id: uuid.UUID, data: VeiculoCreate) -> FrotaVeiculo:
        await self._assert_unique(data.placa, data.renavam, data.chassi)
        await self._assert_refs(data.categoria_id, data.marca_id, data.modelo_id, data.combustivel_id)
        await self._assert_modelo_marca(data.modelo_id, data.marca_id)
        payload = data.model_dump()
        payload["status"] = VeiculoStatus.DISPONIVEL
        item = FrotaVeiculo(tenant_id=tenant_id, **payload)
        from app.modules.intermediacao.service import IntermediacaoService

        await IntermediacaoService(self.session).vincular_veiculo_terceirizado(item)
        self.repo.add(item)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.CREATE, entity="frota_veiculo", entity_id=item.id,
            description=f"Veículo criado: {item.placa}",
        )
        return item

    async def update(self, item_id: uuid.UUID, data: VeiculoUpdate) -> FrotaVeiculo:
        item = await self.get(item_id)
        if item.status == VeiculoStatus.BAIXADO:
            raise ConflictError("Veículo baixado não pode ser alterado.", code="veiculo_baixado")
        payload = data.model_dump(exclude_unset=True)
        placa = payload.get("placa", item.placa)
        renavam = payload.get("renavam", item.renavam)
        chassi = payload.get("chassi", item.chassi)
        await self._assert_unique(placa, renavam, chassi, exclude_id=item.id)
        categoria_id = payload.get("categoria_id", item.categoria_id)
        marca_id = payload.get("marca_id", item.marca_id)
        modelo_id = payload.get("modelo_id", item.modelo_id)
        combustivel_id = payload.get("combustivel_id", item.combustivel_id)
        await self._assert_refs(categoria_id, marca_id, modelo_id, combustivel_id)
        await self._assert_modelo_marca(modelo_id, marca_id)
        for k, v in payload.items():
            setattr(item, k, v)
        from app.modules.intermediacao.service import IntermediacaoService

        await IntermediacaoService(self.session).vincular_veiculo_terceirizado(item)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE, entity="frota_veiculo", entity_id=item.id,
            description=f"Veículo atualizado: {item.placa}",
        )
        return item

    async def delete(self, item_id: uuid.UUID) -> None:
        item = await self.get(item_id)
        if item.status == VeiculoStatus.LOCADO:
            raise ConflictError("Veículo locado não pode ser excluído.", code="veiculo_locado")
        await self.repo.delete(item)
        await audit_service.record(
            AuditAction.DELETE, entity="frota_veiculo", entity_id=item.id,
            description=f"Veículo excluído: {item.placa}",
        )

    async def change_status(
        self,
        item_id: uuid.UUID,
        new_status: VeiculoStatus,
        motivo: str | None = None,
        *,
        force_baixado: bool = False,
    ) -> FrotaVeiculo:
        item = await self.get(item_id)
        current = item.status

        if current == VeiculoStatus.BAIXADO and new_status != VeiculoStatus.BAIXADO:
            if not force_baixado:
                raise ConflictError(
                    "Veículo baixado é estado terminal.", code="baixado_terminal"
                )
            if not motivo:
                raise ValidationError("Informe o motivo para reverter a baixa.")
            item.data_baixa = None
            item.motivo_baixa = None

        if new_status == VeiculoStatus.BAIXADO and current != VeiculoStatus.BAIXADO:
            if not motivo:
                raise ValidationError("Informe o motivo da baixa.")
            item.data_baixa = date.today()
            item.motivo_baixa = motivo

        if new_status == VeiculoStatus.BLOQUEADO:
            if not motivo:
                raise ValidationError("Informe o motivo do bloqueio.")
            item.motivo_bloqueio = motivo
        elif current == VeiculoStatus.BLOQUEADO and new_status == VeiculoStatus.DISPONIVEL:
            item.motivo_bloqueio = None

        if new_status != VeiculoStatus.RESTRITO:
            allowed = VEICULO_TRANSITIONS.get(current, set())
            if new_status not in allowed and not (
                current == VeiculoStatus.BAIXADO and force_baixado
            ):
                raise ValidationError(
                    f"Transição inválida: {current.value} → {new_status.value}."
                )

        item.status = new_status
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="frota_veiculo",
            entity_id=item.id,
            description=f"Status do veículo {item.placa}: {current.value} → {new_status.value}",
        )
        return item

    async def bloquear(self, item_id: uuid.UUID, motivo: str) -> FrotaVeiculo:
        return await self.change_status(item_id, VeiculoStatus.BLOQUEADO, motivo)

    async def baixar(self, item_id: uuid.UUID, motivo: str) -> FrotaVeiculo:
        return await self.change_status(item_id, VeiculoStatus.BAIXADO, motivo)

    async def liberar(self, item_id: uuid.UUID, motivo: str | None = None) -> FrotaVeiculo:
        item = await self.get(item_id)
        if item.status != VeiculoStatus.BLOQUEADO:
            raise ValidationError("Veículo não está bloqueado.")
        return await self.change_status(item_id, VeiculoStatus.DISPONIVEL, motivo)

    async def sync_restrito_from_documentos(self, veiculo_id: uuid.UUID) -> FrotaVeiculo | None:
        item = await self.get(veiculo_id)
        if item.status not in _SYNC_RESTRITO_FROM:
            return None
        doc_repo = DocumentoRepository(self.session)
        has_vencidos = await doc_repo.has_vencidos(veiculo_id)
        if has_vencidos and item.status in {
            VeiculoStatus.DISPONIVEL,
            VeiculoStatus.RESERVADO,
        }:
            item.status = VeiculoStatus.RESTRITO
            await self.repo.flush()
            await audit_service.record(
                AuditAction.UPDATE,
                entity="frota_veiculo",
                entity_id=item.id,
                description=f"Veículo {item.placa} restrito por documentação vencida.",
            )
            return item
        if not has_vencidos and item.status == VeiculoStatus.RESTRITO:
            item.status = VeiculoStatus.DISPONIVEL
            await self.repo.flush()
            await audit_service.record(
                AuditAction.UPDATE,
                entity="frota_veiculo",
                entity_id=item.id,
                description=f"Veículo {item.placa} liberado após regularização documental.",
            )
            return item
        return None

    async def link_acessorio(
        self, tenant_id: uuid.UUID, veiculo_id: uuid.UUID, data: VeiculoAcessorioLink
    ) -> FrotaVeiculoAcessorio:
        await self.get(veiculo_id)
        if await self.acessorios.get(data.acessorio_id) is None:
            raise ValidationError("Acessório inválido.")
        if await self.acessorio_repo.get_vinculo(veiculo_id, data.acessorio_id):
            raise ConflictError("Acessório já vinculado ao veículo.", code="acessorio_vinculado")
        vinculo = FrotaVeiculoAcessorio(
            tenant_id=tenant_id,
            veiculo_id=veiculo_id,
            acessorio_id=data.acessorio_id,
            data_instalacao=data.data_instalacao,
            observacoes=data.observacoes,
        )
        self.acessorio_repo.add(vinculo)
        await self.acessorio_repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="frota_veiculo_acessorio",
            entity_id=vinculo.id,
            description=f"Acessório vinculado ao veículo {veiculo_id}.",
        )
        return vinculo

    async def unlink_acessorio(self, veiculo_id: uuid.UUID, acessorio_id: uuid.UUID) -> None:
        vinculo = await self.acessorio_repo.get_vinculo(veiculo_id, acessorio_id)
        if vinculo is None:
            raise NotFoundError("Vínculo de acessório não encontrado.")
        await self.acessorio_repo.delete(vinculo)
        await audit_service.record(
            AuditAction.DELETE,
            entity="frota_veiculo_acessorio",
            entity_id=vinculo.id,
            description=f"Acessório desvinculado do veículo {veiculo_id}.",
        )

    async def list_acessorios(
        self, params: PageParams, veiculo_id: uuid.UUID
    ) -> Page[FrotaVeiculoAcessorio]:
        await self.get(veiculo_id)
        return await self.acessorio_repo.paginate(
            params, stmt=self.acessorio_repo.list_by_veiculo(veiculo_id)
        )

    async def _assert_unique(
        self,
        placa: str,
        renavam: str | None,
        chassi: str | None,
        *,
        exclude_id: uuid.UUID | None = None,
    ) -> None:
        existing = await self.repo.get_by_placa(placa)
        if existing and existing.id != exclude_id:
            raise ConflictError("Já existe veículo com esta placa.", code="placa_taken")
        if renavam:
            existing = await self.repo.get_by_renavam(renavam)
            if existing and existing.id != exclude_id:
                raise ConflictError("Já existe veículo com este RENAVAM.", code="renavam_taken")
        if chassi:
            existing = await self.repo.get_by_chassi(chassi)
            if existing and existing.id != exclude_id:
                raise ConflictError("Já existe veículo com este chassi.", code="chassi_taken")

    async def _assert_refs(
        self,
        categoria_id: uuid.UUID,
        marca_id: uuid.UUID,
        modelo_id: uuid.UUID,
        combustivel_id: uuid.UUID,
    ) -> None:
        if await self.categorias.get(categoria_id) is None:
            raise ValidationError("Categoria inválida.")
        if await self.marcas.get(marca_id) is None:
            raise ValidationError("Marca inválida.")
        if await self.combustiveis.get(combustivel_id) is None:
            raise ValidationError("Combustível inválido.")
        if await self.modelos.get(modelo_id) is None:
            raise ValidationError("Modelo inválido.")

    async def _assert_modelo_marca(self, modelo_id: uuid.UUID, marca_id: uuid.UUID) -> None:
        modelo = await self.modelos.get(modelo_id)
        if modelo is None:
            raise ValidationError("Modelo inválido.")
        if modelo.marca_id != marca_id:
            raise ValidationError("Modelo não pertence à marca informada.")


class FotoService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = FotoRepository(session)
        self.veiculos = VeiculoRepository(session)

    async def list_by_veiculo(
        self, params: PageParams, veiculo_id: uuid.UUID
    ) -> Page[FrotaVeiculoFoto]:
        if await self.veiculos.get(veiculo_id) is None:
            raise NotFoundError("Veículo não encontrado.")
        return await self.repo.paginate(params, stmt=self.repo.list_by_veiculo(veiculo_id))

    async def get(self, foto_id: uuid.UUID) -> FrotaVeiculoFoto:
        item = await self.repo.get(foto_id)
        if item is None:
            raise NotFoundError("Foto não encontrada.")
        return item

    async def add(
        self, tenant_id: uuid.UUID, veiculo_id: uuid.UUID, data: VeiculoFotoCreate
    ) -> FrotaVeiculoFoto:
        if await self.veiculos.get(veiculo_id) is None:
            raise NotFoundError("Veículo não encontrado.")
        item = FrotaVeiculoFoto(tenant_id=tenant_id, veiculo_id=veiculo_id, **data.model_dump())
        self.repo.add(item)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.CREATE, entity="frota_veiculo_foto", entity_id=item.id,
            description=f"Foto adicionada ao veículo {veiculo_id}.",
        )
        return item

    async def update(self, foto_id: uuid.UUID, data: VeiculoFotoUpdate) -> FrotaVeiculoFoto:
        item = await self.get(foto_id)
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(item, k, v)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE, entity="frota_veiculo_foto", entity_id=item.id,
            description="Foto do veículo atualizada.",
        )
        return item

    async def remove(self, foto_id: uuid.UUID) -> None:
        item = await self.get(foto_id)
        await self.repo.delete(item)
        await audit_service.record(
            AuditAction.DELETE, entity="frota_veiculo_foto", entity_id=item.id,
            description=f"Foto removida do veículo {item.veiculo_id}.",
        )


class DocumentoService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = DocumentoRepository(session)
        self.veiculo_svc = VeiculoService(session)

    async def list_items(
        self,
        params: PageParams,
        *,
        veiculo_id: uuid.UUID | None = None,
        status: DocumentoVeiculoStatus | None = None,
        tipo: DocumentoVeiculoTipo | None = None,
    ) -> Page[FrotaDocumento]:
        stmt = self.repo.list_query(veiculo_id=veiculo_id, status=status, tipo=tipo)
        return await self.repo.paginate(params, stmt=stmt)

    async def list_vencimentos(
        self, params: PageParams, *, days: int = 30
    ) -> Page[FrotaDocumento]:
        if days not in {30, 60, 90}:
            raise ValidationError("Período de vencimentos deve ser 30, 60 ou 90 dias.")
        return await self.repo.paginate(params, stmt=self.repo.vencimentos_query(days))

    async def get(self, item_id: uuid.UUID) -> FrotaDocumento:
        item = await self.repo.get(item_id)
        if item is None:
            raise NotFoundError("Documento não encontrado.")
        return item

    async def create(self, tenant_id: uuid.UUID, data: DocumentoCreate) -> FrotaDocumento:
        await self.veiculo_svc.get(data.veiculo_id)
        payload = data.model_dump()
        payload["status"] = _derive_documento_status(data.data_validade)
        item = FrotaDocumento(tenant_id=tenant_id, **payload)
        self.repo.add(item)
        await self.repo.flush()
        await self.veiculo_svc.sync_restrito_from_documentos(data.veiculo_id)
        await audit_service.record(
            AuditAction.CREATE, entity="frota_documento", entity_id=item.id,
            description=f"Documento {item.tipo.value} criado para veículo {item.veiculo_id}.",
        )
        return item

    async def update(self, item_id: uuid.UUID, data: DocumentoUpdate) -> FrotaDocumento:
        item = await self.get(item_id)
        payload = data.model_dump(exclude_unset=True)
        validade = payload.get("data_validade", item.data_validade)
        if "data_validade" in payload or payload:
            payload["status"] = _derive_documento_status(validade)
        for k, v in payload.items():
            setattr(item, k, v)
        await self.repo.flush()
        await self.veiculo_svc.sync_restrito_from_documentos(item.veiculo_id)
        await audit_service.record(
            AuditAction.UPDATE, entity="frota_documento", entity_id=item.id,
            description=f"Documento {item.tipo.value} atualizado.",
        )
        return item

    async def delete(self, item_id: uuid.UUID) -> None:
        item = await self.get(item_id)
        veiculo_id = item.veiculo_id
        await self.repo.delete(item)
        await self.veiculo_svc.sync_restrito_from_documentos(veiculo_id)
        await audit_service.record(
            AuditAction.DELETE, entity="frota_documento", entity_id=item.id,
            description=f"Documento {item.tipo.value} excluído.",
        )


class TelemetriaService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.dispositivo_repo = TelemetriaDispositivoRepository(session)
        self.evento_repo = TelemetriaEventoRepository(session)
        self.veiculos = VeiculoRepository(session)

    async def list_dispositivos(self, params: PageParams) -> Page[FrotaTelemetriaDispositivo]:
        return await self.dispositivo_repo.paginate(
            params, stmt=self.dispositivo_repo.list_query()
        )

    async def get_dispositivo(self, dispositivo_id: uuid.UUID) -> FrotaTelemetriaDispositivo:
        item = await self.dispositivo_repo.get(dispositivo_id)
        if item is None:
            raise NotFoundError("Dispositivo de telemetria não encontrado.")
        return item

    async def upsert_dispositivo(
        self, tenant_id: uuid.UUID, data: TelemetriaDispositivoUpsert
    ) -> FrotaTelemetriaDispositivo:
        if await self.veiculos.get(data.veiculo_id) is None:
            raise NotFoundError("Veículo não encontrado.")
        existing = await self.dispositivo_repo.get_by_veiculo(data.veiculo_id)
        payload = data.model_dump()
        veiculo_id = payload.pop("veiculo_id")
        if existing:
            for k, v in payload.items():
                setattr(existing, k, v)
            await self.dispositivo_repo.flush()
            await audit_service.record(
                AuditAction.UPDATE,
                entity="frota_telemetria_dispositivo",
                entity_id=existing.id,
                description=f"Dispositivo de telemetria atualizado (veículo {veiculo_id}).",
            )
            return existing
        item = FrotaTelemetriaDispositivo(
            tenant_id=tenant_id, veiculo_id=veiculo_id, **payload
        )
        self.dispositivo_repo.add(item)
        await self.dispositivo_repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="frota_telemetria_dispositivo",
            entity_id=item.id,
            description=f"Dispositivo de telemetria registrado (veículo {veiculo_id}).",
        )
        return item

    async def register_evento(
        self, tenant_id: uuid.UUID, data: TelemetriaEventoCreate
    ) -> FrotaTelemetriaEvento:
        dispositivo = await self.dispositivo_repo.get(data.dispositivo_id)
        if dispositivo is None:
            raise NotFoundError("Dispositivo de telemetria não encontrado.")
        if dispositivo.veiculo_id != data.veiculo_id:
            raise ValidationError("Dispositivo não pertence ao veículo informado.")
        item = FrotaTelemetriaEvento(tenant_id=tenant_id, **data.model_dump())
        self.evento_repo.add(item)
        await self.evento_repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="frota_telemetria_evento",
            entity_id=item.id,
            description=f"Evento de telemetria {item.tipo.value} registrado.",
        )
        return item

    async def list_eventos(
        self, params: PageParams, veiculo_id: uuid.UUID
    ) -> Page[FrotaTelemetriaEvento]:
        if await self.veiculos.get(veiculo_id) is None:
            raise NotFoundError("Veículo não encontrado.")
        return await self.evento_repo.paginate(
            params, stmt=self.evento_repo.list_by_veiculo(veiculo_id)
        )
