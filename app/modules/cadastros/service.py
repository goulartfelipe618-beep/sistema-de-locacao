"""Serviços de Cadastros (regras de negócio)."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.pagination import Page, PageParams
from app.modules.audit.service import audit_service
from app.modules.cadastros.models import Cliente, TabelaAuxiliar
from app.modules.cadastros.repository import ClienteRepository, TabelaAuxiliarRepository
from app.modules.cadastros.schemas import (
    ClienteCreate,
    ClienteUpdate,
    TabelaAuxiliarCreate,
    TabelaAuxiliarUpdate,
)
from app.shared.enums import AuditAction, ClienteStatus

# Itens padrão semeados por tenant (grupo de categorias de cliente).
DEFAULT_CATEGORIAS_CLIENTE: tuple[tuple[str, str, int], ...] = (
    ("varejo", "Varejo", 10),
    ("corporativo", "Corporativo", 20),
    ("frota", "Frota", 30),
    ("turismo", "Turismo", 40),
)


class TabelaAuxiliarService:
    """CRUD de tabelas auxiliares."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = TabelaAuxiliarRepository(session)

    async def ensure_defaults(self, tenant_id: uuid.UUID) -> None:
        """Garante categorias padrão de cliente (idempotente)."""
        for codigo, descricao, ordem in DEFAULT_CATEGORIAS_CLIENTE:
            existing = await self.repo.get_by_grupo_codigo("categoria_cliente", codigo)
            if existing is None:
                self.repo.add(
                    TabelaAuxiliar(
                        tenant_id=tenant_id,
                        grupo="categoria_cliente",
                        codigo=codigo,
                        descricao=descricao,
                        ordem=ordem,
                        ativo=True,
                        sistema=True,
                    )
                )
        await self.repo.flush()

    async def list_by_grupo(
        self,
        grupo: str,
        params: PageParams,
        *,
        apenas_ativos: bool = False,
    ) -> Page[TabelaAuxiliar]:
        """Lista itens de um grupo com paginação."""
        stmt = self.repo.query_by_grupo(grupo, apenas_ativos=apenas_ativos)
        return await self.repo.paginate(params, stmt=stmt)

    async def list_grupos(self) -> list[str]:
        """Grupos existentes no tenant."""
        return await self.repo.list_grupos()

    async def create(self, tenant_id: uuid.UUID, data: TabelaAuxiliarCreate) -> TabelaAuxiliar:
        """Cria item auxiliar."""
        grupo = data.grupo.strip().lower()
        codigo = data.codigo.strip().lower()
        if await self.repo.get_by_grupo_codigo(grupo, codigo):
            raise ConflictError("Já existe um item com este código no grupo.", code="codigo_taken")
        item = TabelaAuxiliar(
            tenant_id=tenant_id,
            grupo=grupo,
            codigo=codigo,
            descricao=data.descricao.strip(),
            ativo=data.ativo,
            ordem=data.ordem,
            sistema=False,
        )
        self.repo.add(item)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="tabela_auxiliar",
            entity_id=item.id,
            description=f"Item auxiliar criado: {grupo}/{codigo}",
        )
        return item

    async def update(self, item_id: uuid.UUID, data: TabelaAuxiliarUpdate) -> TabelaAuxiliar:
        """Atualiza item auxiliar."""
        item = await self.repo.get(item_id)
        if item is None:
            raise NotFoundError("Item auxiliar não encontrado.")
        payload = data.model_dump(exclude_unset=True)
        for field, value in payload.items():
            setattr(item, field, value.strip() if isinstance(value, str) else value)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="tabela_auxiliar",
            entity_id=item.id,
            description=f"Item auxiliar atualizado: {item.grupo}/{item.codigo}",
            changes=payload,
        )
        return item

    async def delete(self, item_id: uuid.UUID) -> None:
        """Inativa/exclui logicamente item auxiliar (protegidos não podem)."""
        item = await self.repo.get(item_id)
        if item is None:
            raise NotFoundError("Item auxiliar não encontrado.")
        if item.sistema:
            raise ValidationError("Itens de sistema não podem ser excluídos.")
        await self.repo.delete(item)
        await audit_service.record(
            AuditAction.DELETE,
            entity="tabela_auxiliar",
            entity_id=item.id,
            description=f"Item auxiliar excluído: {item.grupo}/{item.codigo}",
        )


class ClienteService:
    """CRUD e regras de clientes."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ClienteRepository(session)
        self.aux = TabelaAuxiliarRepository(session)

    async def list_clientes(
        self,
        params: PageParams,
        *,
        search: str | None = None,
    ) -> Page[Cliente]:
        """Lista clientes com busca opcional."""
        return await self.repo.paginate(params, stmt=self.repo.search_query(search))

    async def get(self, cliente_id: uuid.UUID) -> Cliente:
        """Retorna cliente ou 404."""
        cliente = await self.repo.get(cliente_id)
        if cliente is None:
            raise NotFoundError("Cliente não encontrado.")
        return cliente

    async def create(self, tenant_id: uuid.UUID, data: ClienteCreate) -> Cliente:
        """Cria cliente validando duplicidade de documento."""
        await self._assert_unique_document(cpf=data.cpf, cnpj=data.cnpj)
        await self._assert_categoria(data.categoria_codigo)

        cliente = Cliente(
            tenant_id=tenant_id,
            **data.model_dump(),
        )
        self.repo.add(cliente)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="cliente",
            entity_id=cliente.id,
            description=f"Cliente criado: {cliente.nome}",
        )
        return cliente

    async def update(self, cliente_id: uuid.UUID, data: ClienteUpdate) -> Cliente:
        """Atualiza cliente."""
        cliente = await self.get(cliente_id)
        payload = data.model_dump(exclude_unset=True)
        if "categoria_codigo" in payload:
            await self._assert_categoria(payload.get("categoria_codigo"))

        if payload.get("blacklist") is True and not payload.get("motivo_bloqueio"):
            if not cliente.motivo_bloqueio:
                raise ValidationError("Informe o motivo do bloqueio/blacklist.")
            payload["status"] = ClienteStatus.BLOCKED

        for field, value in payload.items():
            setattr(cliente, field, value)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="cliente",
            entity_id=cliente.id,
            description=f"Cliente atualizado: {cliente.nome}",
            changes={k: str(v) for k, v in payload.items()},
        )
        return cliente

    async def delete(self, cliente_id: uuid.UUID) -> None:
        """Soft delete do cliente."""
        cliente = await self.get(cliente_id)
        await self.repo.delete(cliente)
        await audit_service.record(
            AuditAction.DELETE,
            entity="cliente",
            entity_id=cliente.id,
            description=f"Cliente excluído: {cliente.nome}",
        )

    async def bloquear(self, cliente_id: uuid.UUID, motivo: str) -> Cliente:
        """Bloqueia cliente impedindo novas locações."""
        if not motivo.strip():
            raise ValidationError("Motivo do bloqueio é obrigatório.")
        cliente = await self.get(cliente_id)
        cliente.status = ClienteStatus.BLOCKED
        cliente.blacklist = True
        cliente.motivo_bloqueio = motivo.strip()
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="cliente",
            entity_id=cliente.id,
            description=f"Cliente bloqueado: {cliente.nome}",
            changes={"status": ClienteStatus.BLOCKED.value, "motivo": motivo.strip()},
        )
        return cliente

    async def _assert_unique_document(
        self,
        *,
        cpf: str | None,
        cnpj: str | None,
        exclude_id: uuid.UUID | None = None,
    ) -> None:
        if cpf:
            existing = await self.repo.get_by_cpf(cpf)
            if existing and existing.id != exclude_id:
                raise ConflictError("Já existe um cliente com este CPF.", code="cpf_taken")
        if cnpj:
            existing = await self.repo.get_by_cnpj(cnpj)
            if existing and existing.id != exclude_id:
                raise ConflictError("Já existe um cliente com este CNPJ.", code="cnpj_taken")

    async def _assert_categoria(self, codigo: str | None) -> None:
        if not codigo:
            return
        item = await self.aux.get_by_grupo_codigo("categoria_cliente", codigo.strip().lower())
        if item is None or not item.ativo:
            raise ValidationError("Categoria de cliente inválida ou inativa.")
