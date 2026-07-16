"""Repositórios do módulo de Identidade (Repository Pattern)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import (
    Permission,
    Role,
    RolePermission,
    User,
    UserFilial,
    UserRole,
)
from app.shared.repository import BaseRepository


class PermissionRepository(BaseRepository[Permission]):
    """Acesso ao catálogo global de permissões."""

    model = Permission

    async def get_by_code(self, code: str) -> Permission | None:
        stmt = select(Permission).where(Permission.code == code)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_codes(self, codes: list[str]) -> list[Permission]:
        if not codes:
            return []
        stmt = select(Permission).where(Permission.code.in_(codes))
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_by_ids(self, permission_ids: list[uuid.UUID]) -> list[Permission]:
        if not permission_ids:
            return []
        stmt = select(Permission).where(
            Permission.id.in_(permission_ids),
            Permission.deleted_at.is_(None),
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_ordered(self) -> list[Permission]:
        stmt = (
            select(Permission)
            .where(Permission.deleted_at.is_(None))
            .order_by(Permission.module, Permission.resource, Permission.action)
        )
        return list((await self.session.execute(stmt)).scalars().all())


class RoleRepository(BaseRepository[Role]):
    """Acesso a papéis (roles) do tenant."""

    model = Role

    async def get_by_slug(self, tenant_id: uuid.UUID, slug: str) -> Role | None:
        stmt = select(Role).where(
            Role.tenant_id == tenant_id,
            Role.slug == slug,
            Role.deleted_at.is_(None),
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_ids(self, role_ids: list[uuid.UUID]) -> list[Role]:
        if not role_ids:
            return []
        stmt = select(Role).where(Role.id.in_(role_ids), Role.deleted_at.is_(None))
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_ordered(self) -> list[Role]:
        stmt = select(Role).where(Role.deleted_at.is_(None)).order_by(Role.name)
        return list((await self.session.execute(stmt)).scalars().all())


class UserRepository(BaseRepository[User]):
    """Acesso a usuários e suas associações (papéis/filiais/permissões)."""

    model = User

    async def get_by_email(
        self,
        tenant_id: uuid.UUID,
        email: str,
        *,
        for_update: bool = False,
    ) -> User | None:
        stmt = select(User).where(
            User.tenant_id == tenant_id,
            User.email == email.lower(),
            User.deleted_at.is_(None),
        )
        if for_update:
            stmt = stmt.with_for_update()
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_permission_codes(self, user_id: uuid.UUID) -> set[str]:
        """Retorna o conjunto de códigos de permissão efetivos do usuário.

        Ignora papéis e permissões com *soft delete*, evitando vazamento de
        privilégios após remoção lógica de um papel.
        """
        stmt = (
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(
                UserRole.user_id == user_id,
                Role.deleted_at.is_(None),
                Permission.deleted_at.is_(None),
            )
        )
        return set((await self.session.execute(stmt)).scalars().all())

    async def get_role_slugs(self, user_id: uuid.UUID) -> list[str]:
        stmt = (
            select(Role.slug)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id, Role.deleted_at.is_(None))
            .order_by(Role.slug)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_role_ids(self, user_id: uuid.UUID) -> list[uuid.UUID]:
        stmt = select(UserRole.role_id).where(UserRole.user_id == user_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_filial_ids(self, user_id: uuid.UUID) -> list[uuid.UUID]:
        stmt = select(UserFilial.filial_id).where(UserFilial.user_id == user_id)
        return list((await self.session.execute(stmt)).scalars().all())

    # ------------------------------------------------------- Associações
    async def clear_roles(self, user_id: uuid.UUID) -> None:
        for link in (await self.session.execute(
            select(UserRole).where(UserRole.user_id == user_id)
        )).scalars().all():
            await self.session.delete(link)

    async def clear_filiais(self, user_id: uuid.UUID) -> None:
        for link in (await self.session.execute(
            select(UserFilial).where(UserFilial.user_id == user_id)
        )).scalars().all():
            await self.session.delete(link)

    def link_role(self, tenant_id: uuid.UUID, user_id: uuid.UUID, role_id: uuid.UUID) -> None:
        self.session.add(UserRole(tenant_id=tenant_id, user_id=user_id, role_id=role_id))

    def link_filial(self, tenant_id: uuid.UUID, user_id: uuid.UUID, filial_id: uuid.UUID) -> None:
        self.session.add(UserFilial(tenant_id=tenant_id, user_id=user_id, filial_id=filial_id))


class RolePermissionRepository:
    """Gestão da associação Papel ↔ Permissão."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_permission_ids(self, role_id: uuid.UUID) -> list[uuid.UUID]:
        stmt = select(RolePermission.permission_id).where(RolePermission.role_id == role_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def clear(self, role_id: uuid.UUID) -> None:
        for link in (await self.session.execute(
            select(RolePermission).where(RolePermission.role_id == role_id)
        )).scalars().all():
            await self.session.delete(link)

    def link(self, tenant_id: uuid.UUID, role_id: uuid.UUID, permission_id: uuid.UUID) -> None:
        self.session.add(
            RolePermission(tenant_id=tenant_id, role_id=role_id, permission_id=permission_id)
        )
