"""Seed inicial da plataforma (idempotente).

Cria/atualiza:
    * Catálogo global de permissões (a partir de ``app.core.rbac``).
    * Empresa (tenant) padrão + filial matriz.
    * Papéis-modelo do sistema, com suas permissões.
    * Usuário administrador inicial.

Uso:
    python -m scripts.seed
"""

from __future__ import annotations

import asyncio
import os

from app.core.config import settings
from app.core.database import UnitOfWork, dispose_engine
from app.core.logging import configure_logging, get_logger
from app.core.rbac import SYSTEM_PERMISSIONS, SYSTEM_ROLE_TEMPLATES, expand_permissions
from app.core.security import hash_password
from app.modules.identity.models import Permission, Role, User, UserFilial, UserRole
from app.modules.identity.repository import (
    PermissionRepository,
    RolePermissionRepository,
    RoleRepository,
    UserRepository,
)
from app.modules.tenants.models import Filial, Tenant
from app.modules.tenants.repository import FilialRepository, TenantRepository
from app.shared.enums import TenantStatus

logger = get_logger("seed")

ADMIN_EMAIL = os.getenv("SEED_ADMIN_EMAIL", "admin@locadora.local")
ADMIN_PASSWORD = os.getenv("SEED_ADMIN_PASSWORD", "Admin@123")
ADMIN_NAME = os.getenv("SEED_ADMIN_NAME", "Administrador do Sistema")
TENANT_NAME = os.getenv("SEED_TENANT_NAME", "Locadora Matriz LTDA")

_WEAK_PASSWORDS = {"Admin@123", "admin", "password", "123456", "changeme"}


def _validate_seed_credentials() -> None:
    """Bloqueia senha padrão fraca fora do ambiente de desenvolvimento."""
    if settings.environment == "development":
        if ADMIN_PASSWORD in _WEAK_PASSWORDS:
            logger.warning(
                "Usando senha padrão de desenvolvimento (%s). "
                "Defina SEED_ADMIN_PASSWORD em qualquer outro ambiente.",
                ADMIN_EMAIL,
            )
        return

    if "SEED_ADMIN_PASSWORD" not in os.environ:
        raise SystemExit(
            "SEED_ADMIN_PASSWORD é obrigatório fora de development. "
            "Defina uma senha forte via variável de ambiente."
        )
    if ADMIN_PASSWORD in _WEAK_PASSWORDS or len(ADMIN_PASSWORD) < settings.password_min_length:
        raise SystemExit(
            "SEED_ADMIN_PASSWORD insegura. Use senha forte (mínimo "
            f"{settings.password_min_length} caracteres) diferente das padrões."
        )


async def _seed_permissions() -> None:
    """Garante que todo o catálogo de permissões exista (global)."""
    async with UnitOfWork(tenant_id=None) as uow:
        repo = PermissionRepository(uow.session)
        created = 0
        for perm in SYSTEM_PERMISSIONS:
            if await repo.get_by_code(perm.code) is None:
                repo.add(
                    Permission(
                        code=perm.code,
                        module=perm.module,
                        resource=perm.resource,
                        action=perm.action,
                        description=perm.description,
                    )
                )
                created += 1
        logger.info("Permissões: %d criada(s), %d no total.", created, len(SYSTEM_PERMISSIONS))


async def _seed_tenant() -> Tenant:
    """Garante a existência da empresa (tenant) padrão."""
    async with UnitOfWork(tenant_id=None) as uow:
        repo = TenantRepository(uow.session)
        tenant = await repo.get_by_slug(settings.default_tenant_slug)
        if tenant is None:
            tenant = Tenant(
                slug=settings.default_tenant_slug,
                legal_name=TENANT_NAME,
                trade_name="Locadora Matriz",
                status=TenantStatus.ACTIVE,
                plan="enterprise",
            )
            repo.add(tenant)
            await uow.session.flush()
            logger.info("Empresa criada: %s (%s)", tenant.legal_name, tenant.slug)
        else:
            logger.info("Empresa já existente: %s", tenant.slug)
        return tenant


async def _seed_roles(tenant_id) -> None:
    """Cria/atualiza os papéis-modelo do sistema e suas permissões."""
    async with UnitOfWork(tenant_id=tenant_id) as uow:
        role_repo = RoleRepository(uow.session)
        perm_repo = PermissionRepository(uow.session)
        rp_repo = RolePermissionRepository(uow.session)

        all_permissions = await perm_repo.list_all()
        perm_by_code = {p.code: p for p in all_permissions}

        for template in SYSTEM_ROLE_TEMPLATES:
            role = await role_repo.get_by_slug(tenant_id, template.slug)
            if role is None:
                role = Role(
                    tenant_id=tenant_id,
                    slug=template.slug,
                    name=template.name,
                    description=template.description,
                    is_system=True,
                )
                role_repo.add(role)
                await uow.session.flush()

            # Resolve os códigos de permissão do template.
            codes = expand_permissions(set(template.permissions))
            await rp_repo.clear(role.id)
            await uow.session.flush()
            for code in codes:
                perm = perm_by_code.get(code)
                if perm is not None:
                    rp_repo.link(tenant_id, role.id, perm.id)
        logger.info("Papéis-modelo semeados (%d).", len(SYSTEM_ROLE_TEMPLATES))


async def _seed_filial(tenant_id) -> Filial:
    """Garante a filial matriz."""
    async with UnitOfWork(tenant_id=tenant_id) as uow:
        repo = FilialRepository(uow.session)
        filial = await repo.get_by_code(tenant_id, "0001")
        if filial is None:
            filial = Filial(
                tenant_id=tenant_id,
                code="0001",
                name="Matriz",
                is_headquarters=True,
                city="São Paulo",
                state="SP",
            )
            repo.add(filial)
            await uow.session.flush()
            logger.info("Filial matriz criada (0001).")
        return filial


async def _seed_admin(tenant_id, filial_id) -> None:
    """Cria o usuário administrador inicial e seus vínculos."""
    async with UnitOfWork(tenant_id=tenant_id) as uow:
        user_repo = UserRepository(uow.session)
        role_repo = RoleRepository(uow.session)

        user = await user_repo.get_by_email(tenant_id, ADMIN_EMAIL)
        if user is None:
            user = User(
                tenant_id=tenant_id,
                email=ADMIN_EMAIL.lower(),
                full_name=ADMIN_NAME,
                hashed_password=hash_password(ADMIN_PASSWORD),
                is_active=True,
                is_superuser=True,
            )
            user_repo.add(user)
            await uow.session.flush()
            logger.info("Usuário administrador criado: %s", ADMIN_EMAIL)
        else:
            # Re-seed em produção (Easypanel): alinha senha/nome com o .env atual.
            user.full_name = ADMIN_NAME
            user.hashed_password = hash_password(ADMIN_PASSWORD)
            user.is_active = True
            user.is_superuser = True
            user.failed_login_attempts = 0
            user.locked_until = None
            logger.info("Usuário administrador atualizado: %s", ADMIN_EMAIL)

        admin_role = await role_repo.get_by_slug(tenant_id, "admin-empresa")
        existing_roles = set(await user_repo.get_role_ids(user.id))
        if admin_role and admin_role.id not in existing_roles:
            uow.session.add(UserRole(tenant_id=tenant_id, user_id=user.id, role_id=admin_role.id))

        existing_filiais = set(await user_repo.get_filial_ids(user.id))
        if filial_id not in existing_filiais:
            uow.session.add(UserFilial(tenant_id=tenant_id, user_id=user.id, filial_id=filial_id))


async def _seed_cadastros_defaults(tenant_id) -> None:
    """Semeia tabelas auxiliares padrão (categorias de cliente)."""
    from app.modules.cadastros.service import TabelaAuxiliarService

    async with UnitOfWork(tenant_id=tenant_id) as uow:
        await TabelaAuxiliarService(uow.session).ensure_defaults(tenant_id)
    logger.info("Cadastros: categorias padrão de cliente garantidas.")


async def main() -> None:
    """Executa a sequência completa de seed."""
    configure_logging()
    _validate_seed_credentials()
    logger.info("Iniciando seed da plataforma...")
    await _seed_permissions()
    tenant = await _seed_tenant()
    await _seed_roles(tenant.id)
    filial = await _seed_filial(tenant.id)
    await _seed_admin(tenant.id, filial.id)
    await _seed_cadastros_defaults(tenant.id)
    await dispose_engine()

    logger.info("Seed concluído com sucesso.")
    print("\n" + "=" * 60)
    print(" SEED CONCLUÍDO")
    print("=" * 60)
    print(f" Empresa (tenant): {settings.default_tenant_slug}")
    print(f" Login .........: {ADMIN_EMAIL}")
    if settings.environment == "development":
        print(f" Senha .........: {ADMIN_PASSWORD}")
    else:
        print(" Senha .........: (definida via SEED_ADMIN_PASSWORD — não exibida)")
    print(" Acesse ........: http://localhost:8000/login")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
