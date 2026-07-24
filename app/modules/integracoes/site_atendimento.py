"""Webhook de atendimento do site — token por tenant e registro no CRM."""

from __future__ import annotations

import secrets
import uuid
from urllib.parse import urlencode, urljoin

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, NotFoundError
from app.modules.cadastros.models import Cliente
from app.modules.comercial.schemas import InteracaoCreate, OportunidadeCreate
from app.modules.comercial.service import FunilService
from app.modules.integracoes.public_schemas import PublicContatoSiteCreate
from app.modules.notificacoes.schemas import NotificacaoSendInput
from app.modules.notificacoes.service import NotificationService
from app.modules.tenants.models import Tenant
from app.shared.enums import CrmEstagio, CrmInteracaoTipo, CrmOrigemLead


def build_atendimento_webhook_url(base_url: str, token: str) -> str:
    """URL completa para colar em SITE_ATENDIMENTO_WEBHOOK_URL (Easypanel site)."""
    root = base_url.rstrip("/") + "/"
    path = urljoin(root, "api/v1/public/webhooks/atendimento")
    return f"{path}?{urlencode({'token': token})}"


class SiteAtendimentoService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_tenant(self, tenant_id: uuid.UUID) -> Tenant:
        tenant = await self.session.get(Tenant, tenant_id)
        if tenant is None:
            raise NotFoundError("Empresa não encontrada.")
        return tenant

    async def ensure_token(self, tenant_id: uuid.UUID) -> str:
        tenant = await self.get_tenant(tenant_id)
        if not tenant.site_atendimento_webhook_token:
            tenant.site_atendimento_webhook_token = secrets.token_urlsafe(32)
            await self.session.flush()
        return tenant.site_atendimento_webhook_token

    async def regenerate_token(self, tenant_id: uuid.UUID) -> str:
        tenant = await self.get_tenant(tenant_id)
        tenant.site_atendimento_webhook_token = secrets.token_urlsafe(32)
        await self.session.flush()
        return tenant.site_atendimento_webhook_token

    async def resolve_tenant_id_by_token(self, token: str) -> uuid.UUID:
        if not token or len(token) < 16:
            raise AuthenticationError("Token de webhook inválido.", code="invalid_webhook_token")
        stmt = (
            select(Tenant.id)
            .where(
                Tenant.site_atendimento_webhook_token == token.strip(),
                Tenant.deleted_at.is_(None),
            )
            .limit(1)
        )
        tenant_id = (await self.session.execute(stmt)).scalar_one_or_none()
        if tenant_id is None:
            raise AuthenticationError("Token de webhook inválido.", code="invalid_webhook_token")
        return tenant_id

    async def _notificar_equipe(
        self,
        tenant_id: uuid.UUID,
        opp: object,
        payload: PublicContatoSiteCreate,
        origem_label: str,
    ) -> None:
        preview = payload.mensagem.strip().replace("\n", " ")
        if len(preview) > 180:
            preview = preview[:177] + "…"
        mensagem = (
            f"{origem_label} de {payload.nome.strip()}.\n"
            f"E-mail: {payload.email}\n"
            f"Telefone: {payload.telefone.strip()}\n\n"
            f"{preview}"
        )
        await NotificationService(self.session).notify_users_with_permission(
            tenant_id,
            "comercial.funil.visualizar",
            NotificacaoSendInput(
                titulo=f"Nova solicitação — {payload.nome.strip()}"[:200],
                mensagem=mensagem,
                link=f"/comercial/funil/{opp.id}",
                evento="contato.site",
                referencia_tipo="crm_oportunidade",
                referencia_id=opp.id,
            ),
        )

    async def _find_cliente_by_email(
        self, tenant_id: uuid.UUID, email: str
    ) -> Cliente | None:
        stmt = (
            select(Cliente)
            .where(
                Cliente.tenant_id == tenant_id,
                Cliente.deleted_at.is_(None),
                func.lower(Cliente.email) == email.strip().lower(),
            )
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def registrar_contato(
        self, tenant_id: uuid.UUID, payload: PublicContatoSiteCreate
    ) -> dict:
        cliente = await self._find_cliente_by_email(tenant_id, str(payload.email))
        if cliente and payload.telefone and not cliente.telefone:
            cliente.telefone = payload.telefone.strip()
            if not cliente.celular:
                cliente.celular = payload.telefone.strip()

        origem_labels = {
            "chat": "Atendimento site (chat)",
            "assinatura": "Assinatura (site)",
            "fidelidade": "Fidelidade (site)",
        }
        origem_label = origem_labels.get(payload.origem, "Contato site")
        titulo = f"{origem_label} — {payload.nome.strip()}"[:200]
        observacoes = (
            f"E-mail: {payload.email}\n"
            f"Telefone: {payload.telefone}\n"
            f"Origem: {payload.origem}"
        )

        funil = FunilService(self.session)
        opp = await funil.create(
            tenant_id,
            OportunidadeCreate(
                titulo=titulo,
                estagio=CrmEstagio.LEAD,
                origem_lead=CrmOrigemLead.SITE,
                cliente_id=cliente.id if cliente else None,
                observacoes=observacoes,
            ),
        )
        await funil.add_interacao(
            opp.id,
            InteracaoCreate(
                tipo=CrmInteracaoTipo.NOTA,
                descricao=f"Mensagem do visitante:\n\n{payload.mensagem.strip()}",
            ),
        )
        await self.session.flush()

        await self._notificar_equipe(tenant_id, opp, payload, origem_label)

        return {
            "ok": True,
            "oportunidade_id": str(opp.id),
            "numero": opp.numero,
            "_outbound_payload": {
                "oportunidade_id": str(opp.id),
                "numero": opp.numero,
                "nome": payload.nome.strip(),
                "email": str(payload.email),
                "telefone": payload.telefone.strip(),
                "mensagem": payload.mensagem.strip(),
                "origem": payload.origem,
                "cliente_id": str(cliente.id) if cliente else None,
            },
        }
