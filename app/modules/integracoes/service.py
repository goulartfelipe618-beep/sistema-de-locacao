"""Serviços do módulo Integrações (§12)."""

from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_secret, encrypt_secret
from app.core.exceptions import BusinessRuleError, NotFoundError, ValidationError
from app.core.pagination import Page, PageParams
from app.core.security import hash_password, verify_password
from app.modules.audit.service import audit_service
from app.modules.cadastros.service_extra import MotoristaService
from app.modules.financeiro.models import FinPixCobranca
from app.modules.financeiro.service import CartaoService, ContaReceberService, PixService
from app.modules.frota.models import FrotaTelemetriaDispositivo, FrotaVeiculo
from app.modules.frota.schemas import TelemetriaDispositivoUpsert, TelemetriaEventoCreate
from app.modules.frota.service import TelemetriaService, VeiculoService
from app.modules.integracoes.adapters.registry import get_adapter, get_payment_adapter
from app.modules.integracoes.models import IntApiKey, IntConsulta, IntProvedorConfig, IntWebhookEvento
from app.modules.integracoes.schemas import (
    ApiKeyCreate,
    CreditoConsultaInput,
    ProvedorConfigCreate,
    ProvedorConfigUpdate,
    TransitoCnhInput,
    TransitoDebitosInput,
    TransitoMultasInput,
)
from app.modules.locacoes.schemas import MultaCreate
from app.modules.locacoes.service import MultaService
from app.shared.enums import (
    AuditAction,
    IntegracaoConsultaStatus,
    IntegracaoConsultaTipo,
    IntegracaoProvedorStatus,
    IntegracaoTipo,
    PagamentoWebhookEvento,
    PixCobrancaStatus,
    TelemetriaConnStatus,
    TelemetriaEventoTipo,
    WebhookEventoStatus,
)
from app.shared.repository import BaseRepository


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def _json_loads(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _credenciais_from_form(
    client_id: str | None,
    client_secret: str | None,
    api_key: str | None,
    base_url: str | None = None,
) -> dict[str, str]:
    cred: dict[str, str] = {}
    if client_id:
        cred["client_id"] = client_id
    if client_secret:
        cred["client_secret"] = client_secret
    if api_key:
        cred["api_key"] = api_key
    if base_url:
        cred["base_url"] = base_url
    return cred


def _get_adapter(tipo: IntegracaoTipo, provedor: str):
    return get_adapter(tipo, provedor)


class ProvedorConfigRepository(BaseRepository[IntProvedorConfig]):
    model = IntProvedorConfig

    def list_query(self, *, tipo: IntegracaoTipo | None = None):
        stmt = select(IntProvedorConfig).where(IntProvedorConfig.deleted_at.is_(None))
        if tipo:
            stmt = stmt.where(IntProvedorConfig.tipo == tipo)
        return stmt.order_by(IntProvedorConfig.nome)


class ApiKeyRepository(BaseRepository[IntApiKey]):
    model = IntApiKey

    def list_query(self):
        return select(IntApiKey).where(IntApiKey.deleted_at.is_(None)).order_by(IntApiKey.nome)

    async def get_by_prefix(self, prefix: str) -> IntApiKey | None:
        stmt = select(IntApiKey).where(
            IntApiKey.key_prefix == prefix,
            IntApiKey.deleted_at.is_(None),
            IntApiKey.ativo.is_(True),
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()


class WebhookRepository(BaseRepository[IntWebhookEvento]):
    model = IntWebhookEvento

    def list_query(self):
        return (
            select(IntWebhookEvento)
            .where(IntWebhookEvento.deleted_at.is_(None))
            .order_by(IntWebhookEvento.created_at.desc())
        )


class ConsultaRepository(BaseRepository[IntConsulta]):
    model = IntConsulta

    def list_query(self, *, tipo: IntegracaoConsultaTipo | None = None):
        stmt = select(IntConsulta).where(IntConsulta.deleted_at.is_(None))
        if tipo:
            stmt = stmt.where(IntConsulta.tipo == tipo)
        return stmt.order_by(IntConsulta.created_at.desc())


class ProvedorConfigService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ProvedorConfigRepository(session)

    async def list_items(
        self, params: PageParams, *, tipo: IntegracaoTipo | None = None
    ) -> Page[IntProvedorConfig]:
        return await self.repo.paginate(params, stmt=self.repo.list_query(tipo=tipo))

    async def get(self, config_id: uuid.UUID) -> IntProvedorConfig:
        item = await self.repo.get(config_id)
        if item is None:
            raise NotFoundError("Configuração de integração não encontrada.")
        return item

    async def get_by_webhook_token(self, token: str) -> IntProvedorConfig | None:
        stmt = select(IntProvedorConfig).where(
            IntProvedorConfig.webhook_token == token,
            IntProvedorConfig.deleted_at.is_(None),
            IntProvedorConfig.status == IntegracaoProvedorStatus.ATIVO,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    def _encrypt_creds(self, data: ProvedorConfigCreate | ProvedorConfigUpdate, existing: IntProvedorConfig | None = None) -> str | None:
        cred = _credenciais_from_form(
            getattr(data, "client_id", None),
            getattr(data, "client_secret", None),
            getattr(data, "api_key", None),
            getattr(data, "base_url", None),
        )
        if not cred and existing:
            return existing.credenciais_cripto
        if not cred:
            return None
        return encrypt_secret(_json_dumps(cred))

    async def create(self, tenant_id: uuid.UUID, data: ProvedorConfigCreate) -> IntProvedorConfig:
        item = IntProvedorConfig(
            tenant_id=tenant_id,
            filial_id=data.filial_id,
            tipo=data.tipo,
            provedor=data.provedor,
            nome=data.nome,
            credenciais_cripto=self._encrypt_creds(data),
            webhook_secret_cripto=encrypt_secret(data.webhook_secret) if data.webhook_secret else None,
            webhook_token=secrets.token_urlsafe(24),
            config_json=_json_dumps(data.config_json or {}),
        )
        self.repo.add(item)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="int_provedor_config",
            entity_id=item.id,
            description=f"Integração {data.tipo.value}/{data.provedor} criada.",
        )
        return item

    async def update(self, config_id: uuid.UUID, data: ProvedorConfigUpdate) -> IntProvedorConfig:
        item = await self.get(config_id)
        if data.nome is not None:
            item.nome = data.nome
        if data.status is not None:
            item.status = data.status
        if data.config_json is not None:
            item.config_json = _json_dumps(data.config_json)
        cred = self._encrypt_creds(data, existing=item)
        if cred is not None:
            item.credenciais_cripto = cred
        if data.webhook_secret:
            item.webhook_secret_cripto = encrypt_secret(data.webhook_secret)
        await self.repo.flush()
        return item

    def credenciais(self, config: IntProvedorConfig) -> dict[str, str]:
        if not config.credenciais_cripto:
            return {}
        return _json_loads(decrypt_secret(config.credenciais_cripto))

    def webhook_secret(self, config: IntProvedorConfig) -> str:
        if not config.webhook_secret_cripto:
            return ""
        return decrypt_secret(config.webhook_secret_cripto)

    async def testar(self, config_id: uuid.UUID) -> bool:
        config = await self.get(config_id)
        adapter = _get_adapter(config.tipo, config.provedor)
        if config.tipo == IntegracaoTipo.PAGAMENTOS:
            ok = adapter.testar_conexao(credenciais=self.credenciais(config))
        elif config.tipo == IntegracaoTipo.TELEMETRIA:
            ok = bool(adapter.sincronizar(credenciais=self.credenciais(config), equipamentos=[])[0] is not None)
        elif config.tipo == IntegracaoTipo.TRANSITO:
            adapter = get_adapter(config.tipo, config.provedor)
            testar = getattr(adapter, "testar_conexao", None)
            ok = testar(credenciais=self.credenciais(config)) if callable(testar) else True
        elif config.tipo == IntegracaoTipo.CREDITO:
            adapter = get_adapter(config.tipo, config.provedor)
            testar = getattr(adapter, "testar_conexao", None)
            ok = testar(credenciais=self.credenciais(config)) if callable(testar) else True
        else:
            ok = True
        config.ultimo_sync_em = _now() if ok else config.ultimo_sync_em
        config.ultimo_erro = None if ok else "Falha no teste de conexão"
        config.status = IntegracaoProvedorStatus.ATIVO if ok else IntegracaoProvedorStatus.ERRO
        await self.repo.flush()
        return ok


class PagamentoWebhookService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.config_svc = ProvedorConfigService(session)
        self.webhook_repo = WebhookRepository(session)

    async def processar(
        self,
        *,
        provider: str,
        token: str,
        body: bytes,
        signature: str,
    ) -> IntWebhookEvento:
        config = await self.config_svc.get_by_webhook_token(token)
        if config is None or config.tipo != IntegracaoTipo.PAGAMENTOS:
            raise NotFoundError("Configuração de webhook não encontrada.")
        if config.provedor != provider:
            raise ValidationError("Provedor do webhook não confere.")

        secret = self.config_svc.webhook_secret(config)
        gateway = get_payment_adapter(config.provedor)
        assinatura_ok = gateway.validar_assinatura(body=body, signature=signature, secret=secret)
        payload = gateway.parse_webhook(body=body)

        evento = IntWebhookEvento(
            tenant_id=config.tenant_id,
            config_id=config.id,
            provedor=provider,
            evento_tipo=payload.evento.value,
            payload_json=_json_dumps(payload.raw or {}),
            assinatura_valida=assinatura_ok,
            status=WebhookEventoStatus.RECEBIDO,
        )
        self.webhook_repo.add(evento)
        await self.webhook_repo.flush()

        if not assinatura_ok:
            evento.status = WebhookEventoStatus.ERRO
            evento.erro_mensagem = "Assinatura inválida"
            await self.webhook_repo.flush()
            return evento

        try:
            await self._aplicar_evento(config.tenant_id, payload)
            evento.status = WebhookEventoStatus.PROCESSADO
            evento.processado_em = _now()
        except Exception as exc:  # noqa: BLE001
            evento.status = WebhookEventoStatus.ERRO
            evento.erro_mensagem = str(exc)[:2000]
            evento.processado_em = _now()

        await self.webhook_repo.flush()
        return evento

    async def _aplicar_evento(self, tenant_id: uuid.UUID, payload) -> None:
        ref = payload.referencia_externa
        if payload.evento == PagamentoWebhookEvento.PAGO:
            stmt = select(FinPixCobranca).where(
                FinPixCobranca.tenant_id == tenant_id,
                FinPixCobranca.txid == ref,
                FinPixCobranca.deleted_at.is_(None),
            )
            cobranca = (await self.session.execute(stmt)).scalar_one_or_none()
            if cobranca:
                await PixService(self.session).confirmar_pagamento(cobranca.id)
        elif payload.evento in {PagamentoWebhookEvento.CAPTURADO, PagamentoWebhookEvento.AUTORIZADO}:
            # Referência externa pode ser UUID da transação de cartão.
            try:
                transacao_id = uuid.UUID(ref)
                await CartaoService(self.session).capturar(transacao_id)
            except ValueError:
                pass
        elif payload.evento in {PagamentoWebhookEvento.ESTORNADO, PagamentoWebhookEvento.CHARGEBACK}:
            stmt = select(FinPixCobranca).where(
                FinPixCobranca.tenant_id == tenant_id,
                FinPixCobranca.txid == ref,
                FinPixCobranca.deleted_at.is_(None),
            )
            cobranca = (await self.session.execute(stmt)).scalar_one_or_none()
            if cobranca:
                if cobranca.titulo_receber_id:
                    await ContaReceberService(self.session).estornar(cobranca.titulo_receber_id)
                cobranca.status = PixCobrancaStatus.CANCELADO
                await self.session.flush()
            try:
                transacao_id = uuid.UUID(ref)
                await CartaoService(self.session).estornar(transacao_id)
            except ValueError:
                pass


class TransitoService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.config_svc = ProvedorConfigService(session)
        self.consulta_repo = ConsultaRepository(session)

    async def _resolve_config(
        self, tenant_id: uuid.UUID, config_id: uuid.UUID | None
    ) -> IntProvedorConfig:
        if config_id:
            config = await self.config_svc.get(config_id)
            if config.tipo != IntegracaoTipo.TRANSITO:
                raise ValidationError("Configuração não é de trânsito.")
            return config
        stmt = (
            select(IntProvedorConfig)
            .where(
                IntProvedorConfig.tenant_id == tenant_id,
                IntProvedorConfig.tipo == IntegracaoTipo.TRANSITO,
                IntProvedorConfig.status == IntegracaoProvedorStatus.ATIVO,
                IntProvedorConfig.deleted_at.is_(None),
            )
            .limit(1)
        )
        config = (await self.session.execute(stmt)).scalar_one_or_none()
        if config is None:
            raise BusinessRuleError("Nenhum provedor de trânsito configurado.")
        return config

    async def consultar_multas(
        self, tenant_id: uuid.UUID, data: TransitoMultasInput
    ) -> IntConsulta:
        veiculo = await VeiculoService(self.session).get(data.veiculo_id)
        config = await self._resolve_config(tenant_id, data.config_id)
        cred = self.config_svc.credenciais(config)
        req = {"placa": veiculo.placa, "renavam": veiculo.renavam}
        consulta = IntConsulta(
            tenant_id=tenant_id,
            config_id=config.id,
            tipo=IntegracaoConsultaTipo.TRANSITO_MULTAS,
            referencia_tipo="veiculo",
            referencia_id=veiculo.id,
            request_json=_json_dumps(req),
        )
        self.consulta_repo.add(consulta)
        try:
            adapter = get_adapter(IntegracaoTipo.TRANSITO, config.provedor)
            multas = adapter.consultar_multas_veiculo(
                placa=veiculo.placa, renavam=veiculo.renavam, credenciais=cred
            )
            imported: list[str] = []
            if data.importar:
                multa_svc = MultaService(self.session)
                for m in multas:
                    created = await multa_svc.create(
                        tenant_id,
                        MultaCreate(
                            veiculo_id=veiculo.id,
                            ocorrido_em=m.ocorrido_em,
                            orgao=m.orgao,
                            codigo_infracao=m.codigo_infracao,
                            valor=m.valor,
                            pontuacao=m.pontuacao,
                            ait=m.ait,
                            observacoes="Importado via integração trânsito",
                        ),
                    )
                    imported.append(str(created.id))
            consulta.response_json = _json_dumps(
                {"multas": [m.__dict__ for m in multas], "importados": imported}
            )
            consulta.status = IntegracaoConsultaStatus.SUCESSO
            config.ultimo_sync_em = _now()
        except Exception as exc:  # noqa: BLE001
            consulta.status = IntegracaoConsultaStatus.ERRO
            consulta.erro_mensagem = str(exc)[:2000]
            config.ultimo_erro = consulta.erro_mensagem
        await self.consulta_repo.flush()
        return consulta

    async def consultar_cnh(self, tenant_id: uuid.UUID, data: TransitoCnhInput) -> IntConsulta:
        motorista = await MotoristaService(self.session).get(data.motorista_id)
        config = await self._resolve_config(tenant_id, data.config_id)
        cred = self.config_svc.credenciais(config)
        consulta = IntConsulta(
            tenant_id=tenant_id,
            config_id=config.id,
            tipo=IntegracaoConsultaTipo.TRANSITO_CNH,
            referencia_tipo="motorista",
            referencia_id=motorista.id,
            request_json=_json_dumps({"cnh": motorista.cnh_numero}),
        )
        self.consulta_repo.add(consulta)
        try:
            if not motorista.cnh_numero:
                raise ValidationError("Motorista sem número de CNH.")
            cnh = get_adapter(IntegracaoTipo.TRANSITO, config.provedor).consultar_cnh(
                cnh_numero=motorista.cnh_numero, cpf=motorista.cpf, credenciais=cred
            )
            if data.atualizar_pontuacao:
                motorista.cnh_pontuacao = cnh.pontuacao
                await self.session.flush()
            consulta.response_json = _json_dumps(cnh.__dict__)
            consulta.status = IntegracaoConsultaStatus.SUCESSO
            config.ultimo_sync_em = _now()
        except Exception as exc:  # noqa: BLE001
            consulta.status = IntegracaoConsultaStatus.ERRO
            consulta.erro_mensagem = str(exc)[:2000]
        await self.consulta_repo.flush()
        return consulta

    async def consultar_debitos(
        self, tenant_id: uuid.UUID, data: TransitoDebitosInput
    ) -> IntConsulta:
        veiculo = await VeiculoService(self.session).get(data.veiculo_id)
        config = await self._resolve_config(tenant_id, data.config_id)
        cred = self.config_svc.credenciais(config)
        req = {"placa": veiculo.placa, "renavam": veiculo.renavam}
        consulta = IntConsulta(
            tenant_id=tenant_id,
            config_id=config.id,
            tipo=IntegracaoConsultaTipo.TRANSITO_DEBITOS,
            referencia_tipo="veiculo",
            referencia_id=veiculo.id,
            request_json=_json_dumps(req),
        )
        self.consulta_repo.add(consulta)
        try:
            debitos = get_adapter(IntegracaoTipo.TRANSITO, config.provedor).consultar_debitos_veiculo(
                placa=veiculo.placa, renavam=veiculo.renavam, credenciais=cred
            )
            consulta.response_json = _json_dumps({"debitos": [d.__dict__ for d in debitos]})
            consulta.status = IntegracaoConsultaStatus.SUCESSO
            config.ultimo_sync_em = _now()
        except Exception as exc:  # noqa: BLE001
            consulta.status = IntegracaoConsultaStatus.ERRO
            consulta.erro_mensagem = str(exc)[:2000]
            config.ultimo_erro = consulta.erro_mensagem
        await self.consulta_repo.flush()
        return consulta

    async def list_consultas(
        self, params: PageParams, *, tipo: IntegracaoConsultaTipo | None = None
    ) -> Page[IntConsulta]:
        return await self.consulta_repo.paginate(params, stmt=self.consulta_repo.list_query(tipo=tipo))


class CreditoService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.config_svc = ProvedorConfigService(session)
        self.consulta_repo = ConsultaRepository(session)

    async def consultar(self, tenant_id: uuid.UUID, data: CreditoConsultaInput) -> IntConsulta:
        from app.modules.cadastros.service import ClienteService

        cliente = await ClienteService(self.session).get(data.cliente_id)
        stmt = (
            select(IntProvedorConfig)
            .where(
                IntProvedorConfig.tenant_id == tenant_id,
                IntProvedorConfig.tipo == IntegracaoTipo.CREDITO,
                IntProvedorConfig.deleted_at.is_(None),
            )
            .limit(1)
        )
        config = (await self.session.execute(stmt)).scalar_one_or_none()
        if config is None:
            raise BusinessRuleError("Nenhum provedor de crédito configurado.")
        doc = cliente.cpf or cliente.cnpj or ""
        if not doc:
            raise ValidationError("Cliente sem documento para consulta de crédito.")
        tipo_pessoa = "pj" if cliente.cnpj else "pf"
        consulta = IntConsulta(
            tenant_id=tenant_id,
            config_id=config.id,
            tipo=IntegracaoConsultaTipo.CREDITO_SCORE,
            referencia_tipo="cliente",
            referencia_id=cliente.id,
            request_json=_json_dumps({"documento": doc, "tipo": tipo_pessoa}),
        )
        self.consulta_repo.add(consulta)
        try:
            result = get_adapter(IntegracaoTipo.CREDITO, config.provedor).consultar_score(
                documento=doc, tipo_pessoa=tipo_pessoa, credenciais=self.config_svc.credenciais(config)
            )
            if result.restricao and not cliente.blacklist:
                cliente.blacklist = True
                cliente.motivo_bloqueio = result.motivo or "Restrição de crédito (integração)"
                await self.session.flush()
            consulta.response_json = _json_dumps(result.__dict__)
            consulta.status = IntegracaoConsultaStatus.SUCESSO
        except Exception as exc:  # noqa: BLE001
            consulta.status = IntegracaoConsultaStatus.ERRO
            consulta.erro_mensagem = str(exc)[:2000]
        await self.consulta_repo.flush()
        return consulta


class TelemetriaIntegracaoService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.config_svc = ProvedorConfigService(session)
        self.telemetria = TelemetriaService(session)

    async def sincronizar(self, tenant_id: uuid.UUID, config_id: uuid.UUID | None = None) -> dict:
        if config_id:
            config = await self.config_svc.get(config_id)
        else:
            stmt = (
                select(IntProvedorConfig)
                .where(
                    IntProvedorConfig.tenant_id == tenant_id,
                    IntProvedorConfig.tipo == IntegracaoTipo.TELEMETRIA,
                    IntProvedorConfig.status == IntegracaoProvedorStatus.ATIVO,
                    IntProvedorConfig.deleted_at.is_(None),
                )
                .limit(1)
            )
            config = (await self.session.execute(stmt)).scalar_one_or_none()
            if config is None:
                raise BusinessRuleError("Nenhum provedor de telemetria configurado.")

        stmt = select(FrotaTelemetriaDispositivo).where(
            FrotaTelemetriaDispositivo.tenant_id == tenant_id,
            FrotaTelemetriaDispositivo.deleted_at.is_(None),
        )
        dispositivos = list((await self.session.execute(stmt)).scalars().all())
        equipamentos = [d.equipamento_id for d in dispositivos] or ["SIM-001"]

        posicoes, eventos = get_adapter(IntegracaoTipo.TELEMETRIA, config.provedor).sincronizar(
            credenciais=self.config_svc.credenciais(config),
            equipamentos=equipamentos,
        )
        map_eq_veiculo = {d.equipamento_id: d for d in dispositivos}
        atualizados = 0
        eventos_reg = 0
        for pos in posicoes:
            disp = map_eq_veiculo.get(pos.equipamento_id)
            if disp is None:
                veiculo_stmt = select(FrotaVeiculo).where(
                    FrotaVeiculo.tenant_id == tenant_id,
                    FrotaVeiculo.deleted_at.is_(None),
                ).limit(1)
                veiculo = (await self.session.execute(veiculo_stmt)).scalar_one_or_none()
                if veiculo is None:
                    continue
                disp_obj = await self.telemetria.upsert_dispositivo(
                    tenant_id,
                    TelemetriaDispositivoUpsert(
                        veiculo_id=veiculo.id,
                        provedor=config.provedor,
                        equipamento_id=pos.equipamento_id,
                        conn_status=TelemetriaConnStatus.ONLINE,
                        lat=pos.lat,
                        lng=pos.lng,
                        ultima_posicao_em=pos.atualizado_em,
                        km_telemetria=pos.km,
                    ),
                )
                map_eq_veiculo[pos.equipamento_id] = disp_obj
                disp = disp_obj
            else:
                await self.telemetria.upsert_dispositivo(
                    tenant_id,
                    TelemetriaDispositivoUpsert(
                        veiculo_id=disp.veiculo_id,
                        provedor=config.provedor,
                        equipamento_id=pos.equipamento_id,
                        conn_status=TelemetriaConnStatus.ONLINE,
                        lat=pos.lat,
                        lng=pos.lng,
                        ultima_posicao_em=pos.atualizado_em,
                        km_telemetria=pos.km,
                    ),
                )
            atualizados += 1

        for ev in eventos:
            disp = map_eq_veiculo.get(ev.equipamento_id)
            if disp is None:
                continue
            tipo_map = {
                "excesso_velocidade": TelemetriaEventoTipo.EXCESSO_VELOCIDADE,
                "geofence": TelemetriaEventoTipo.GEOFENCE,
                "colisao": TelemetriaEventoTipo.COLISAO,
            }
            tipo = tipo_map.get(ev.tipo, TelemetriaEventoTipo.OUTRO)
            await self.telemetria.register_evento(
                tenant_id,
                TelemetriaEventoCreate(
                    dispositivo_id=disp.id,
                    veiculo_id=disp.veiculo_id,
                    tipo=tipo,
                    descricao=ev.descricao,
                    lat=ev.lat,
                    lng=ev.lng,
                    velocidade=ev.velocidade,
                    ocorrido_em=ev.ocorrido_em,
                    payload_json=_json_dumps(ev.payload or {}),
                ),
            )
            eventos_reg += 1

        config.ultimo_sync_em = _now()
        config.ultimo_erro = None
        await self.session.flush()
        return {"posicoes": atualizados, "eventos": eventos_reg}


class ApiKeyService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ApiKeyRepository(session)

    async def list_items(self, params: PageParams) -> Page[IntApiKey]:
        return await self.repo.paginate(params, stmt=self.repo.list_query())

    async def get(self, key_id: uuid.UUID) -> IntApiKey:
        item = await self.repo.get(key_id)
        if item is None:
            raise NotFoundError("API Key não encontrada.")
        return item

    async def get_for_tenant(self, tenant_id: uuid.UUID, key_id: uuid.UUID) -> IntApiKey:
        item = await self.get(key_id)
        if item.tenant_id != tenant_id:
            raise NotFoundError("API Key não encontrada.")
        return item

    async def create(
        self, tenant_id: uuid.UUID, data: ApiKeyCreate, *, user_id: uuid.UUID | None
    ) -> tuple[IntApiKey, str]:
        raw = f"erp_{secrets.token_urlsafe(32)}"
        prefix = raw[:12]
        item = IntApiKey(
            tenant_id=tenant_id,
            nome=data.nome,
            key_prefix=prefix,
            key_hash=hash_password(raw),
            scopes_json=_json_dumps(data.scopes),
            rate_limit_por_minuto=data.rate_limit_por_minuto,
            expires_at=data.expires_at,
            criado_por_id=user_id,
        )
        self.repo.add(item)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="int_api_key",
            entity_id=item.id,
            description=f"API Key criada: {item.nome}",
        )
        return item, raw

    async def revoke(self, key_id: uuid.UUID) -> IntApiKey:
        item = await self.get(key_id)
        item.ativo = False
        await self.repo.flush()
        return item

    async def delete(self, tenant_id: uuid.UUID, key_id: uuid.UUID) -> None:
        """Remove a chave da listagem (soft delete) e invalida uso imediato."""
        item = await self.get_for_tenant(tenant_id, key_id)
        item.ativo = False
        await self.repo.delete(item)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.DELETE,
            entity="int_api_key",
            entity_id=item.id,
            description=f"API Key excluída: {item.nome}",
        )

    async def authenticate(self, raw_key: str) -> IntApiKey:
        if not raw_key or len(raw_key) < 16:
            raise ValidationError("API Key inválida.")
        prefix = raw_key[:12]
        item = await self.repo.get_by_prefix(prefix)
        if item is None or not verify_password(raw_key, item.key_hash):
            raise ValidationError("API Key inválida.")
        if item.expires_at and item.expires_at < _now():
            raise ValidationError("API Key expirada.")
        item.ultimo_uso_em = _now()
        await self.repo.flush()
        return item

    def scopes(self, item: IntApiKey) -> set[str]:
        try:
            return set(json.loads(item.scopes_json or "[]"))
        except json.JSONDecodeError:
            return set()

    def has_scope(self, item: IntApiKey, scope: str) -> bool:
        scopes = self.scopes(item)
        return "*" in scopes or scope in scopes


class WebhookLogService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = WebhookRepository(session)

    async def list_items(self, params: PageParams) -> Page[IntWebhookEvento]:
        return await self.repo.paginate(params, stmt=self.repo.list_query())
