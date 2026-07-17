"""Serviço de autenticação em dois fatores (TOTP opcional, §14.3)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_secret, encrypt_secret
from app.core.exceptions import AuthenticationError, NotFoundError, ValidationError
from app.core.security import verify_password
from app.modules.audit.service import audit_service
from app.modules.identity.models import User
from app.modules.identity.repository import UserRepository
from app.modules.identity.totp import (
    build_provisioning_uri,
    decrypt_recovery_codes,
    encrypt_recovery_codes,
    generate_recovery_codes,
    generate_totp_secret,
    normalize_recovery_code,
    qr_data_uri,
    verify_totp_code,
)
from app.shared.enums import AuditAction


def _now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(slots=True)
class TwoFactorSetupData:
    """Dados para configurar 2FA (QR + URI)."""

    provisioning_uri: str
    qr_data_uri: str


class TwoFactorService:
    """Configuração, verificação e desativação de 2FA TOTP."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)

    async def get_user(self, user_id: uuid.UUID) -> User:
        user = await self.users.get(user_id)
        if user is None:
            raise NotFoundError("Usuário não encontrado.")
        return user

    def _secret_plain(self, user: User) -> str | None:
        if not user.totp_secret_encrypted:
            return None
        return decrypt_secret(user.totp_secret_encrypted)

    async def begin_setup(self, user_id: uuid.UUID) -> TwoFactorSetupData:
        """Gera novo segredo TOTP e retorna QR (ainda não ativa até confirmar)."""
        user = await self.get_user(user_id)
        secret = generate_totp_secret()
        user.totp_secret_encrypted = encrypt_secret(secret)
        user.totp_enabled = False
        user.totp_enabled_at = None
        user.recovery_codes_encrypted = None
        await self.session.flush()
        uri = build_provisioning_uri(secret, user.email)
        return TwoFactorSetupData(provisioning_uri=uri, qr_data_uri=qr_data_uri(uri))

    async def confirm_setup(self, user_id: uuid.UUID, code: str) -> list[str]:
        """Confirma 2FA com código TOTP e devolve códigos de recuperação (única exibição)."""
        user = await self.get_user(user_id)
        secret = self._secret_plain(user)
        if not secret:
            raise ValidationError("Inicie a configuração de 2FA antes de confirmar.")
        if not verify_totp_code(secret, code):
            raise ValidationError("Código TOTP inválido. Verifique o aplicativo autenticador.")

        recovery = generate_recovery_codes()
        user.totp_enabled = True
        user.totp_enabled_at = _now()
        user.recovery_codes_encrypted = encrypt_recovery_codes(recovery)
        await audit_service.record(
            AuditAction.UPDATE,
            entity="user",
            entity_id=user.id,
            description=f"2FA ativado: {user.email}",
        )
        return recovery

    async def disable(
        self,
        user_id: uuid.UUID,
        *,
        password: str,
        code: str,
    ) -> None:
        """Desativa 2FA após validar senha e código TOTP/recuperação."""
        user = await self.get_user(user_id)
        if not user.totp_enabled:
            raise ValidationError("2FA não está ativo para este usuário.")
        if not verify_password(password, user.hashed_password):
            raise AuthenticationError("Senha incorreta.", code="invalid_credentials")
        if not await self._verify_login_code(user, code):
            raise ValidationError("Código 2FA inválido.")

        user.totp_enabled = False
        user.totp_secret_encrypted = None
        user.totp_enabled_at = None
        user.recovery_codes_encrypted = None
        await audit_service.record(
            AuditAction.UPDATE,
            entity="user",
            entity_id=user.id,
            description=f"2FA desativado: {user.email}",
        )

    async def admin_reset(self, user_id: uuid.UUID) -> None:
        """Remove 2FA de um usuário (ação administrativa)."""
        user = await self.get_user(user_id)
        user.totp_enabled = False
        user.totp_secret_encrypted = None
        user.totp_enabled_at = None
        user.recovery_codes_encrypted = None
        await audit_service.record(
            AuditAction.UPDATE,
            entity="user",
            entity_id=user.id,
            description=f"2FA resetado pelo administrador: {user.email}",
        )

    async def _verify_login_code(self, user: User, code: str) -> bool:
        """Valida TOTP ou consome um código de recuperação."""
        secret = self._secret_plain(user)
        if secret and verify_totp_code(secret, code):
            return True

        normalized = normalize_recovery_code(code)
        if len(normalized) != 8:
            return False
        stored = decrypt_recovery_codes(user.recovery_codes_encrypted)
        if normalized in stored:
            stored.remove(normalized)
            user.recovery_codes_encrypted = encrypt_recovery_codes(stored) if stored else None
            await self.session.flush()
            return True
        return False

    async def verify_login(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        code: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> User:
        """Valida segundo fator no login e registra falha em caso de erro."""
        user = await self.get_user(user_id)
        if user.tenant_id != tenant_id:
            raise AuthenticationError("Credenciais inválidas.", code="invalid_credentials")
        if not user.is_active:
            raise AuthenticationError("Conta inativa.", code="account_inactive")
        if not user.totp_enabled or not user.totp_secret_encrypted:
            raise AuthenticationError("2FA não configurado.", code="2fa_not_enabled")

        if not await self._verify_login_code(user, code):
            await audit_service.record(
                AuditAction.LOGIN_FAILED,
                entity="user",
                entity_id=user.id,
                description=f"Falha 2FA: {user.email}",
                ip_address=ip_address,
                user_agent=user_agent,
                tenant_id=tenant_id,
                user_id=user.id,
            )
            raise AuthenticationError("Código 2FA inválido.", code="invalid_2fa_code")

        return user
