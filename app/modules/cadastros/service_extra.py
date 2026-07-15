"""Serviços dos cadastros complementares."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Generic, TypeVar

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.pagination import Page, PageParams
from app.modules.audit.service import audit_service
from app.modules.cadastros.models_extra import Fornecedor, Motorista, Parceiro, Vendedor
from app.modules.cadastros.repository import TabelaAuxiliarRepository
from app.modules.cadastros.schemas_extra import (
    FornecedorCreate,
    FornecedorUpdate,
    MotoristaCreate,
    MotoristaUpdate,
    ParceiroCreate,
    ParceiroUpdate,
    VendedorCreate,
    VendedorUpdate,
)
from app.shared.base_model import TenantBaseModel
from app.shared.enums import AuditAction, CadastroStatus, MotoristaCnhStatus
from app.shared.repository import BaseRepository

ModelT = TypeVar("ModelT", bound=TenantBaseModel)


class _NamedRepo(BaseRepository[ModelT], Generic[ModelT]):
    def search_by_nome(self, search: str | None = None) -> Select[tuple[ModelT]]:
        stmt = self._base_query().order_by(self.model.nome.asc())  # type: ignore[attr-defined]
        if search:
            term = f"%{search.strip().lower()}%"
            stmt = stmt.where(func.lower(self.model.nome).like(term))  # type: ignore[attr-defined]
        return stmt


class MotoristaRepository(_NamedRepo[Motorista]):
    model = Motorista

    async def get_by_cpf(self, cpf: str) -> Motorista | None:
        stmt = self._base_query().where(Motorista.cpf == cpf).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_cnh(self, cnh: str) -> Motorista | None:
        stmt = self._base_query().where(Motorista.cnh_numero == cnh).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    def search_query(self, search: str | None = None) -> Select[tuple[Motorista]]:
        stmt = self._base_query().order_by(Motorista.nome.asc())
        if search:
            term = f"%{search.strip().lower()}%"
            digits = "".join(ch for ch in search if ch.isdigit())
            filters = [
                func.lower(Motorista.nome).like(term),
                func.lower(func.coalesce(Motorista.email, "")).like(term),
                func.lower(func.coalesce(Motorista.cnh_numero, "")).like(term),
            ]
            if digits:
                filters.append(Motorista.cpf.like(f"%{digits}%"))
            stmt = stmt.where(or_(*filters))
        return stmt


class ParceiroRepository(_NamedRepo[Parceiro]):
    model = Parceiro

    async def get_by_cpf(self, cpf: str) -> Parceiro | None:
        return (
            await self.session.execute(self._base_query().where(Parceiro.cpf == cpf).limit(1))
        ).scalar_one_or_none()

    async def get_by_cnpj(self, cnpj: str) -> Parceiro | None:
        return (
            await self.session.execute(self._base_query().where(Parceiro.cnpj == cnpj).limit(1))
        ).scalar_one_or_none()


class FornecedorRepository(_NamedRepo[Fornecedor]):
    model = Fornecedor

    async def get_by_cnpj(self, cnpj: str) -> Fornecedor | None:
        return (
            await self.session.execute(
                self._base_query().where(Fornecedor.cnpj == cnpj).limit(1)
            )
        ).scalar_one_or_none()


class VendedorRepository(_NamedRepo[Vendedor]):
    model = Vendedor

    async def get_by_usuario(self, usuario_id: uuid.UUID) -> Vendedor | None:
        return (
            await self.session.execute(
                self._base_query().where(Vendedor.usuario_id == usuario_id).limit(1)
            )
        ).scalar_one_or_none()


def _derive_cnh_status(validade: date | None, current: MotoristaCnhStatus) -> MotoristaCnhStatus:
    if current in {MotoristaCnhStatus.SUSPENSA, MotoristaCnhStatus.CASSADA}:
        return current
    if validade and validade < date.today():
        return MotoristaCnhStatus.VENCIDA
    return MotoristaCnhStatus.REGULAR if current == MotoristaCnhStatus.VENCIDA else current


class MotoristaService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = MotoristaRepository(session)

    async def list_items(self, params: PageParams, *, search: str | None = None) -> Page[Motorista]:
        return await self.repo.paginate(params, stmt=self.repo.search_query(search))

    async def get(self, item_id: uuid.UUID) -> Motorista:
        item = await self.repo.get(item_id)
        if item is None:
            raise NotFoundError("Motorista não encontrado.")
        return item

    async def create(self, tenant_id: uuid.UUID, data: MotoristaCreate) -> Motorista:
        if data.cpf and await self.repo.get_by_cpf(data.cpf):
            raise ConflictError("Já existe motorista com este CPF.", code="cpf_taken")
        if data.cnh_numero and await self.repo.get_by_cnh(data.cnh_numero):
            raise ConflictError("Já existe motorista com esta CNH.", code="cnh_taken")
        payload = data.model_dump()
        payload["cnh_status"] = _derive_cnh_status(data.cnh_validade, data.cnh_status)
        item = Motorista(tenant_id=tenant_id, **payload)
        self.repo.add(item)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.CREATE, entity="motorista", entity_id=item.id,
            description=f"Motorista criado: {item.nome}",
        )
        return item

    async def update(self, item_id: uuid.UUID, data: MotoristaUpdate) -> Motorista:
        item = await self.get(item_id)
        payload = data.model_dump(exclude_unset=True)
        if "cnh_validade" in payload or "cnh_status" in payload:
            validade = payload.get("cnh_validade", item.cnh_validade)
            status = payload.get("cnh_status", item.cnh_status)
            payload["cnh_status"] = _derive_cnh_status(validade, status)
        for k, v in payload.items():
            setattr(item, k, v)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE, entity="motorista", entity_id=item.id,
            description=f"Motorista atualizado: {item.nome}",
        )
        return item

    async def delete(self, item_id: uuid.UUID) -> None:
        item = await self.get(item_id)
        await self.repo.delete(item)
        await audit_service.record(
            AuditAction.DELETE, entity="motorista", entity_id=item.id,
            description=f"Motorista excluído: {item.nome}",
        )


class ParceiroService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ParceiroRepository(session)

    async def list_items(self, params: PageParams, *, search: str | None = None) -> Page[Parceiro]:
        return await self.repo.paginate(params, stmt=self.repo.search_by_nome(search))

    async def get(self, item_id: uuid.UUID) -> Parceiro:
        item = await self.repo.get(item_id)
        if item is None:
            raise NotFoundError("Parceiro não encontrado.")
        return item

    async def create(self, tenant_id: uuid.UUID, data: ParceiroCreate) -> Parceiro:
        if data.cpf and await self.repo.get_by_cpf(data.cpf):
            raise ConflictError("Já existe parceiro com este CPF.", code="cpf_taken")
        if data.cnpj and await self.repo.get_by_cnpj(data.cnpj):
            raise ConflictError("Já existe parceiro com este CNPJ.", code="cnpj_taken")
        item = Parceiro(tenant_id=tenant_id, **data.model_dump())
        self.repo.add(item)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.CREATE, entity="parceiro", entity_id=item.id,
            description=f"Parceiro criado: {item.nome}",
        )
        return item

    async def update(self, item_id: uuid.UUID, data: ParceiroUpdate) -> Parceiro:
        item = await self.get(item_id)
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(item, k, v)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE, entity="parceiro", entity_id=item.id,
            description=f"Parceiro atualizado: {item.nome}",
        )
        return item

    async def delete(self, item_id: uuid.UUID) -> None:
        item = await self.get(item_id)
        await self.repo.delete(item)
        await audit_service.record(
            AuditAction.DELETE, entity="parceiro", entity_id=item.id,
            description=f"Parceiro excluído: {item.nome}",
        )


class FornecedorService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = FornecedorRepository(session)
        self.aux = TabelaAuxiliarRepository(session)

    async def list_items(self, params: PageParams, *, search: str | None = None) -> Page[Fornecedor]:
        return await self.repo.paginate(params, stmt=self.repo.search_by_nome(search))

    async def get(self, item_id: uuid.UUID) -> Fornecedor:
        item = await self.repo.get(item_id)
        if item is None:
            raise NotFoundError("Fornecedor não encontrado.")
        return item

    async def create(self, tenant_id: uuid.UUID, data: FornecedorCreate) -> Fornecedor:
        if data.cnpj and await self.repo.get_by_cnpj(data.cnpj):
            raise ConflictError("Já existe fornecedor com este CNPJ.", code="cnpj_taken")
        await self._assert_categoria(data.categoria_codigo)
        item = Fornecedor(tenant_id=tenant_id, **data.model_dump())
        self.repo.add(item)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.CREATE, entity="fornecedor", entity_id=item.id,
            description=f"Fornecedor criado: {item.nome}",
        )
        return item

    async def update(self, item_id: uuid.UUID, data: FornecedorUpdate) -> Fornecedor:
        item = await self.get(item_id)
        payload = data.model_dump(exclude_unset=True)
        if "categoria_codigo" in payload:
            await self._assert_categoria(payload.get("categoria_codigo"))
        if payload.get("bloqueado") is True:
            if not (payload.get("motivo_bloqueio") or item.motivo_bloqueio):
                raise ValidationError("Informe o motivo do bloqueio.")
            payload["status"] = CadastroStatus.INACTIVE
        for k, v in payload.items():
            setattr(item, k, v)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE, entity="fornecedor", entity_id=item.id,
            description=f"Fornecedor atualizado: {item.nome}",
        )
        return item

    async def delete(self, item_id: uuid.UUID) -> None:
        item = await self.get(item_id)
        await self.repo.delete(item)
        await audit_service.record(
            AuditAction.DELETE, entity="fornecedor", entity_id=item.id,
            description=f"Fornecedor excluído: {item.nome}",
        )

    async def _assert_categoria(self, codigo: str | None) -> None:
        if not codigo:
            return
        item = await self.aux.get_by_grupo_codigo("categoria_fornecedor", codigo.strip().lower())
        if item is None or not item.ativo:
            raise ValidationError("Categoria de fornecedor inválida.")


class VendedorService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = VendedorRepository(session)

    async def list_items(self, params: PageParams, *, search: str | None = None) -> Page[Vendedor]:
        return await self.repo.paginate(params, stmt=self.repo.search_by_nome(search))

    async def get(self, item_id: uuid.UUID) -> Vendedor:
        item = await self.repo.get(item_id)
        if item is None:
            raise NotFoundError("Vendedor não encontrado.")
        return item

    async def create(self, tenant_id: uuid.UUID, data: VendedorCreate) -> Vendedor:
        if data.usuario_id and await self.repo.get_by_usuario(data.usuario_id):
            raise ConflictError("Já existe vendedor vinculado a este usuário.", code="usuario_taken")
        item = Vendedor(tenant_id=tenant_id, **data.model_dump())
        self.repo.add(item)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.CREATE, entity="vendedor", entity_id=item.id,
            description=f"Vendedor criado: {item.nome}",
        )
        return item

    async def update(self, item_id: uuid.UUID, data: VendedorUpdate) -> Vendedor:
        item = await self.get(item_id)
        payload = data.model_dump(exclude_unset=True)
        usuario_id = payload.get("usuario_id")
        if usuario_id:
            existing = await self.repo.get_by_usuario(usuario_id)
            if existing and existing.id != item.id:
                raise ConflictError("Usuário já vinculado a outro vendedor.", code="usuario_taken")
        for k, v in payload.items():
            setattr(item, k, v)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE, entity="vendedor", entity_id=item.id,
            description=f"Vendedor atualizado: {item.nome}",
        )
        return item

    async def delete(self, item_id: uuid.UUID) -> None:
        item = await self.get(item_id)
        await self.repo.delete(item)
        await audit_service.record(
            AuditAction.DELETE, entity="vendedor", entity_id=item.id,
            description=f"Vendedor excluído: {item.nome}",
        )
