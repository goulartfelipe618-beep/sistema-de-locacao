"""Webhooks outbound para consumidores da API pública (§12.5)."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_secret, encrypt_secret
from app.core.logging import get_logger
from app.core.pagination import Page, PageParams
from app.modules.integracoes.models import IntOutboundWebhook
from app.shared.repository import BaseRepository

logger = get_logger(__name__)

OUTBOUND_EVENTOS = (
    "reserva.confirmada",
    "contrato.encerrado",
)


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def _json_loads(raw: str) -> list[str]:
    try:
        data = json.loads(raw or "[]")
        return list(data) if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


class OutboundWebhookRepository(BaseRepository[IntOutboundWebhook]):
    model = IntOutboundWebhook

    def list_query(self):
        return (
            select(IntOutboundWebhook)
            .where(IntOutboundWebhook.deleted_at.is_(None))
            .order_by(IntOutboundWebhook.nome)
        )

    async def list_ativos_por_evento(
        self, tenant_id: uuid.UUID, evento: str
    ) -> list[IntOutboundWebhook]:
        stmt = select(IntOutboundWebhook).where(
            IntOutboundWebhook.tenant_id == tenant_id,
            IntOutboundWebhook.ativo.is_(True),
            IntOutboundWebhook.deleted_at.is_(None),
        )
        items = list((await self.session.execute(stmt)).scalars().all())
        return [w for w in items if evento in _json_loads(w.eventos_json)]


class OutboundWebhookService:
    """Gestão e disparo de webhooks outbound."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = OutboundWebhookRepository(session)

    async def list_items(self, params: PageParams) -> Page[IntOutboundWebhook]:
        return await self.repo.paginate(params, stmt=self.repo.list_query())

    async def get(self, webhook_id: uuid.UUID) -> IntOutboundWebhook:
        item = await self.repo.get(webhook_id)
        if item is None:
            from app.core.exceptions import NotFoundError

            raise NotFoundError("Webhook outbound não encontrado.")
        return item

    async def create(
        self,
        tenant_id: uuid.UUID,
        *,
        nome: str,
        url: str,
        eventos: list[str],
        secret: str | None = None,
    ) -> IntOutboundWebhook:
        invalid = [e for e in eventos if e not in OUTBOUND_EVENTOS]
        if invalid:
            from app.core.exceptions import ValidationError

            raise ValidationError(f"Eventos inválidos: {', '.join(invalid)}")
        item = IntOutboundWebhook(
            tenant_id=tenant_id,
            nome=nome.strip(),
            url=url.strip(),
            eventos_json=_json_dumps(eventos),
            secret_cripto=encrypt_secret(secret) if secret else None,
            ativo=True,
        )
        self.repo.add(item)
        await self.repo.flush()
        return item

    async def delete(self, webhook_id: uuid.UUID) -> None:
        await self.repo.delete(await self.get(webhook_id))

    def _sign(self, body: bytes, secret: str) -> str:
        return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    async def dispatch(
        self,
        tenant_id: uuid.UUID,
        evento: str,
        payload: dict[str, Any],
    ) -> int:
        """Dispara webhooks ativos para o evento. Retorna quantidade enviada."""
        webhooks = await self.repo.list_ativos_por_evento(tenant_id, evento)
        if not webhooks:
            return 0
        body = _json_dumps({"evento": evento, "payload": payload, "timestamp": _now().isoformat()})
        body_bytes = body.encode("utf-8")
        sent = 0
        for hook in webhooks:
            headers = {"Content-Type": "application/json", "X-ERP-Event": evento}
            secret = decrypt_secret(hook.secret_cripto) if hook.secret_cripto else ""
            if secret:
                headers["X-ERP-Signature"] = self._sign(body_bytes, secret)
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(hook.url, content=body_bytes, headers=headers)
                hook.ultimo_disparo_em = _now()
                hook.ultimo_erro = None if resp.is_success else f"HTTP {resp.status_code}"
                if resp.is_success:
                    sent += 1
            except Exception as exc:  # noqa: BLE001
                hook.ultimo_erro = str(exc)[:500]
                logger.warning("Falha webhook outbound %s: %s", hook.url, exc)
        await self.session.flush()
        return sent


async def notify_outbound_event(
    tenant_id: uuid.UUID,
    evento: str,
    payload: dict[str, Any],
) -> None:
    """Dispara webhooks em transação independente (não bloqueia fluxo principal)."""
    from app.core.database import UnitOfWork

    try:
        async with UnitOfWork(tenant_id=tenant_id) as uow:
            await OutboundWebhookService(uow.session).dispatch(tenant_id, evento, payload)
            await uow.commit()
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao disparar webhooks outbound: %s", evento)
