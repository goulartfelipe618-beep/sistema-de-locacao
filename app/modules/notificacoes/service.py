"""Serviço de notificações multi-canal."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.pagination import Page, PageParams
from app.modules.identity.models import User
from app.modules.notificacoes.adapters.registry import get_email_provider, get_sms_provider
from app.modules.notificacoes.models import Notificacao, NotificacaoEnvio
from app.modules.notificacoes.schemas import NotificacaoSendInput
from app.shared.enums import NotificacaoCanal, NotificacaoEnvioStatus
from app.shared.repository import BaseRepository


def _now() -> datetime:
    return datetime.now(tz=UTC)


class NotificacaoRepository(BaseRepository[Notificacao]):
    model = Notificacao

    def inbox_query(self, user_id: uuid.UUID):
        return (
            select(Notificacao)
            .where(
                Notificacao.deleted_at.is_(None),
                Notificacao.user_id == user_id,
            )
            .order_by(Notificacao.created_at.desc())
        )

    async def count_nao_lidas(self, user_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Notificacao)
            .where(
                Notificacao.deleted_at.is_(None),
                Notificacao.user_id == user_id,
                Notificacao.lida.is_(False),
            )
        )
        return int(result.scalar_one())


class NotificacaoEnvioRepository(BaseRepository[NotificacaoEnvio]):
    model = NotificacaoEnvio

    def list_query(self):
        return (
            select(NotificacaoEnvio)
            .where(NotificacaoEnvio.deleted_at.is_(None))
            .order_by(NotificacaoEnvio.created_at.desc())
        )


class NotificationService:
    """Orquestra notificações in-app e envios externos."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = NotificacaoRepository(session)
        self.envio_repo = NotificacaoEnvioRepository(session)

    async def get(self, notificacao_id: uuid.UUID) -> Notificacao:
        item = await self.repo.get(notificacao_id)
        if item is None:
            raise NotFoundError("Notificação não encontrada.")
        return item

    async def list_inbox(
        self, user_id: uuid.UUID, page: int = 1, size: int = 25
    ) -> Page[Notificacao]:
        return await self.repo.paginate(
            PageParams(page=page, size=size),
            stmt=self.repo.inbox_query(user_id),
        )

    async def count_nao_lidas(self, user_id: uuid.UUID) -> int:
        return await self.repo.count_nao_lidas(user_id)

    async def list_envios(self, page: int = 1, size: int = 25) -> Page[NotificacaoEnvio]:
        return await self.envio_repo.paginate(PageParams(page=page, size=size))

    async def marcar_lida(self, notificacao_id: uuid.UUID, user_id: uuid.UUID) -> Notificacao:
        item = await self.get(notificacao_id)
        if item.user_id != user_id:
            raise NotFoundError("Notificação não encontrada.")
        item.lida = True
        item.lida_em = _now()
        await self.session.flush()
        return item

    async def marcar_todas_lidas(self, user_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(Notificacao).where(
                Notificacao.deleted_at.is_(None),
                Notificacao.user_id == user_id,
                Notificacao.lida.is_(False),
            )
        )
        items = list(result.scalars().all())
        now = _now()
        for item in items:
            item.lida = True
            item.lida_em = now
        await self.session.flush()
        return len(items)

    async def _resolve_user_email(self, user_id: uuid.UUID) -> str | None:
        result = await self.session.execute(
            select(User.email).where(User.id == user_id, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def send(
        self,
        tenant_id: uuid.UUID,
        payload: NotificacaoSendInput,
    ) -> Notificacao | None:
        canais = payload.canais or [NotificacaoCanal.IN_APP]
        notificacao: Notificacao | None = None

        if NotificacaoCanal.IN_APP in canais and payload.user_id:
            notificacao = Notificacao(
                tenant_id=tenant_id,
                user_id=payload.user_id,
                titulo=payload.titulo,
                mensagem=payload.mensagem,
                link=payload.link,
                evento=payload.evento,
                referencia_tipo=payload.referencia_tipo,
                referencia_id=payload.referencia_id,
            )
            self.repo.add(notificacao)
            await self.session.flush()

        email_dest = payload.email
        if not email_dest and payload.user_id and NotificacaoCanal.EMAIL in canais:
            email_dest = await self._resolve_user_email(payload.user_id)

        telefone_dest = payload.telefone
        external_channels: list[tuple[NotificacaoCanal, str]] = []
        if NotificacaoCanal.EMAIL in canais and email_dest:
            external_channels.append((NotificacaoCanal.EMAIL, email_dest))
        sms_canais = {NotificacaoCanal.SMS, NotificacaoCanal.WHATSAPP}
        for canal in canais:
            if canal in sms_canais and telefone_dest:
                external_channels.append((canal, telefone_dest))

        for canal, destino in external_channels:
            envio = NotificacaoEnvio(
                tenant_id=tenant_id,
                notificacao_id=notificacao.id if notificacao else None,
                canal=canal,
                destino=destino,
                assunto=payload.assunto or payload.titulo,
                corpo=payload.mensagem,
                status=NotificacaoEnvioStatus.PENDENTE,
            )
            self.envio_repo.add(envio)
            await self.session.flush()

            if payload.async_send:
                from app.modules.notificacoes.tasks import enviar_notificacao_task

                enviar_notificacao_task.delay(str(envio.id), str(tenant_id))
            else:
                await self._processar_envio(envio.id)

        return notificacao

    async def _processar_envio(self, envio_id: uuid.UUID) -> NotificacaoEnvio:
        envio = await self.envio_repo.get(envio_id)
        if envio is None:
            raise NotFoundError("Envio não encontrado.")
        if envio.status == NotificacaoEnvioStatus.ENVIADO:
            return envio

        try:
            if envio.canal == NotificacaoCanal.EMAIL:
                get_email_provider().send(
                    to=envio.destino,
                    subject=envio.assunto or "Notificação ERP Locadora",
                    body=envio.corpo,
                )
            elif envio.canal in {NotificacaoCanal.SMS, NotificacaoCanal.WHATSAPP}:
                get_sms_provider().send(to=envio.destino, body=envio.corpo)
            envio.status = NotificacaoEnvioStatus.ENVIADO
            envio.enviado_em = _now()
            envio.erro_mensagem = None
        except Exception as exc:  # noqa: BLE001
            envio.status = NotificacaoEnvioStatus.FALHA
            envio.erro_mensagem = str(exc)
            envio.enviado_em = _now()
        await self.session.flush()
        return envio
