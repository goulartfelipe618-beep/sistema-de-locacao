"""Serviços do módulo de Identidade (regras de negócio de autenticação e RBAC).

Nenhuma regra de negócio vive nas rotas: autenticação, bloqueio por tentativas,
resolução de permissões e CRUD de usuários residem aqui.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import UnitOfWork
from app.core.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.core.logging import get_logger
from app.core.pagination import Page, PageParams
from app.core.security import hash_password, verify_password
from app.modules.audit.service import audit_service
from app.modules.identity.models import User
from app.modules.identity.repository import UserRepository
from app.modules.identity.schemas import UserCreate, UserUpdate
from app.shared.enums import AuditAction

logger = get_logger(__name__)


@dataclass(slots=True)
class AuthenticatedUser:
    """Instantâneo imutável do usuário autenticado, com RBAC resolvido."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    is_superuser: bool
    roles: list[str] = field(default_factory=list)
    permissions: set[str] = field(default_factory=set)
    filial_ids: list[uuid.UUID] = field(default_factory=list)


class AuthService:
    """Autenticação de usuários com política de bloqueio por tentativas."""

    async def authenticate(
        self,
        *,
        tenant_id: uuid.UUID,
        email: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> User:
        """Valida credenciais e aplica a política de segurança de login.

        Usa uma unidade de trabalho própria para garantir a persistência dos
        contadores de tentativa/bloqueio mesmo quando o login falha.

        Raises:
            AuthenticationError: credenciais inválidas, conta inativa ou bloqueada.
        """
        email_norm = email.strip().lower()
        now = datetime.now(tz=UTC)

        async with UnitOfWork(tenant_id=tenant_id) as uow:
            repo = UserRepository(uow.session)
            # Bloqueia a linha para evitar corrida no contador de tentativas.
            user = await repo.get_by_email(tenant_id, email_norm, for_update=True)

            if user is None:
                await self._audit_failure(
                    tenant_id, email_norm, ip_address, user_agent, "inexistente"
                )
                raise AuthenticationError("Credenciais inválidas.", code="invalid_credentials")

            if user.locked_until and user.locked_until > now:
                await self._audit_failure(
                    tenant_id, email_norm, ip_address, user_agent, "bloqueado", user.id
                )
                raise AuthenticationError(
                    "Conta temporariamente bloqueada por excesso de tentativas.",
                    code="account_locked",
                )

            if not user.is_active:
                await self._audit_failure(
                    tenant_id, email_norm, ip_address, user_agent, "inativo", user.id
                )
                raise AuthenticationError("Conta inativa.", code="account_inactive")

            if not verify_password(password, user.hashed_password):
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= settings.login_max_attempts:
                    user.locked_until = now + timedelta(minutes=settings.login_lockout_minutes)
                    user.failed_login_attempts = 0
                await uow.commit()
                await self._audit_failure(
                    tenant_id, email_norm, ip_address, user_agent, "senha", user.id
                )
                raise AuthenticationError("Credenciais inválidas.", code="invalid_credentials")

            # Sucesso: zera contadores e registra o acesso.
            user.failed_login_attempts = 0
            user.locked_until = None
            user.last_login_at = now

        await audit_service.record(
            AuditAction.LOGIN,
            entity="user",
            entity_id=user.id,
            description=f"Login bem-sucedido: {email_norm}",
            ip_address=ip_address,
            user_agent=user_agent,
            tenant_id=tenant_id,
            user_id=user.id,
        )
        return user

    async def _audit_failure(
        self,
        tenant_id: uuid.UUID,
        email: str,
        ip: str | None,
        user_agent: str | None,
        reason: str,
        user_id: uuid.UUID | None = None,
    ) -> None:
        await audit_service.record(
            AuditAction.LOGIN_FAILED,
            entity="user",
            entity_id=user_id,
            description=f"Falha de login ({reason}): {email}",
            ip_address=ip,
            user_agent=user_agent,
            tenant_id=tenant_id,
            user_id=user_id,
        )


class RBACService:
    """Resolução das permissões e do escopo de acesso de um usuário."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)

    async def build_authenticated_user(self, user: User) -> AuthenticatedUser:
        """Compõe o objeto de usuário autenticado com papéis/permissões/filiais."""
        permissions = await self.users.get_permission_codes(user.id)
        roles = await self.users.get_role_slugs(user.id)
        filial_ids = await self.users.get_filial_ids(user.id)
        return AuthenticatedUser(
            id=user.id,
            tenant_id=user.tenant_id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            roles=roles,
            permissions=permissions,
            filial_ids=filial_ids,
        )

    async def load_by_id(self, user_id: uuid.UUID) -> AuthenticatedUser | None:
        """Carrega e resolve um usuário ativo pelo ID (para o contexto da requisição)."""
        user = await self.users.get(user_id)
        if user is None or not user.is_active:
            return None
        return await self.build_authenticated_user(user)


class UserService:
    """CRUD de usuários e vínculos de papéis/filiais."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)

    async def list_users(self, params: PageParams, *, search: str | None = None) -> Page[User]:
        """Lista usuários paginados, com busca opcional por nome/e-mail."""
        stmt = self.users._base_query().order_by(User.full_name)
        if search:
            term = f"%{search.strip().lower()}%"
            stmt = stmt.where(
                func.lower(User.full_name).like(term) | func.lower(User.email).like(term)
            )
        return await self.users.paginate(params, stmt=stmt)

    async def get_user(self, user_id: uuid.UUID) -> User:
        """Retorna um usuário pelo ID ou levanta :class:`NotFoundError`."""
        user = await self.users.get(user_id)
        if user is None:
            raise NotFoundError("Usuário não encontrado.")
        return user

    async def create_user(self, data: UserCreate, *, tenant_id: uuid.UUID) -> User:
        """Cria um usuário, define a senha (hash) e vincula papéis/filiais."""
        email_norm = data.email.strip().lower()
        if await self.users.get_by_email(tenant_id, email_norm):
            raise ConflictError("Já existe um usuário com este e-mail.", code="email_taken")

        user = User(
            tenant_id=tenant_id,
            email=email_norm,
            full_name=data.full_name.strip(),
            hashed_password=hash_password(data.password),
            is_active=data.is_active,
        )
        self.users.add(user)
        await self.users.flush()

        for role_id in dict.fromkeys(data.role_ids):
            self.users.link_role(tenant_id, user.id, role_id)
        for filial_id in dict.fromkeys(data.filial_ids):
            self.users.link_filial(tenant_id, user.id, filial_id)

        await audit_service.record(
            AuditAction.CREATE,
            entity="user",
            entity_id=user.id,
            description=f"Usuário criado: {email_norm}",
        )
        return user

    async def update_user(self, user_id: uuid.UUID, data: UserUpdate) -> User:
        """Atualiza dados, senha e vínculos de um usuário existente."""
        user = await self.get_user(user_id)

        if data.full_name is not None:
            user.full_name = data.full_name.strip()
        if data.is_active is not None:
            user.is_active = data.is_active
        if data.password is not None:
            if len(data.password) < settings.password_min_length:
                raise ValidationError("Senha abaixo do tamanho mínimo.")
            user.hashed_password = hash_password(data.password)

        if data.role_ids is not None:
            await self.users.clear_roles(user.id)
            for role_id in dict.fromkeys(data.role_ids):
                self.users.link_role(user.tenant_id, user.id, role_id)
        if data.filial_ids is not None:
            await self.users.clear_filiais(user.id)
            for filial_id in dict.fromkeys(data.filial_ids):
                self.users.link_filial(user.tenant_id, user.id, filial_id)

        await audit_service.record(
            AuditAction.UPDATE,
            entity="user",
            entity_id=user.id,
            description=f"Usuário atualizado: {user.email}",
        )
        return user
