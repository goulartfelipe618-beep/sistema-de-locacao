"""Serviço de auditoria.

Grava eventos auditáveis em uma **transação independente** da transação de
negócio, garantindo que a trilha persista mesmo quando a operação principal é
desfeita (essencial para eventos de segurança: acessos negados, falhas de login).
"""

from __future__ import annotations

import uuid

from app.core.context import current_context
from app.core.database import UnitOfWork
from app.core.logging import get_logger
from app.modules.audit.models import AuditLog
from app.modules.audit.repository import AuditRepository
from app.shared.enums import AuditAction

logger = get_logger(__name__)


class AuditService:
    """Registro de eventos na trilha de auditoria."""

    async def record(
        self,
        action: AuditAction | str,
        *,
        entity: str | None = None,
        entity_id: uuid.UUID | None = None,
        description: str | None = None,
        changes: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        tenant_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
    ) -> None:
        """Registra um evento auditável de forma durável e isolada.

        Os campos de contexto (tenant, usuário, correlação) são preenchidos
        automaticamente a partir do contexto atual quando não informados.
        """
        ctx = current_context()
        action_value = action.value if isinstance(action, AuditAction) else str(action)

        log = AuditLog(
            tenant_id=tenant_id if tenant_id is not None else ctx.tenant_id,
            user_id=user_id if user_id is not None else ctx.user_id,
            action=action_value,
            entity=entity,
            entity_id=entity_id,
            description=description,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=ctx.correlation_id,
        )

        try:
            async with UnitOfWork(tenant_id=log.tenant_id) as uow:
                AuditRepository(uow.session).add(log)
        except Exception:
            # A auditoria nunca deve derrubar o fluxo principal; apenas logamos.
            logger.exception("Falha ao registrar evento de auditoria: %s", action_value)


# Instância única do serviço de auditoria.
audit_service = AuditService()
