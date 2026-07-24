"""Serviços de negócio do módulo Fiscal (§10.1–10.5)."""

from __future__ import annotations

import hashlib
import io
import uuid
import zipfile
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from xml.etree import ElementTree as ET

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BusinessRuleError,
    NotFoundError,
    ValidationError,
)
from app.core.pagination import Page, PageParams
from app.modules.audit.service import audit_service
from app.modules.fiscal.adapters.factory import get_nfe_provider, get_nfse_provider
from app.modules.fiscal.guards import assert_fiscal_emissao_habilitada, fiscal_emissao_habilitada
from app.modules.fiscal.adapters.nfe_port import NfeItemPayload
from app.modules.fiscal.models import (
    FisAliquota,
    FisCancelamento,
    FisImpostoConfig,
    FisNfe,
    FisNfeItem,
    FisNfse,
    FisPrazoCancelamento,
    FisXmlArquivo,
)
from app.modules.fiscal.schemas import (
    AliquotaCreate,
    CancelamentoCreate,
    ImpostoConfigCreate,
    ImpostoConfigUpdate,
    NfeCreate,
    NfeItemInput,
    NfseCreate,
    PrazoCancelamentoCreate,
)
from app.shared.enums import (
    AuditAction,
    CancelamentoEventoTipo,
    CancelamentoStatus,
    FiscalDocumentoTipo,
    FiscalXmlDirecao,
    FiscalXmlTipo,
    ImpostoTipo,
    NfeOperacao,
    NfeStatus,
    NfseStatus,
)
from app.shared.repository import BaseRepository

_MONEY = Decimal("0.01")
_ZERO = Decimal("0")

# Alíquotas padrão (fallback quando não há parametrização vigente em Impostos).
_DEFAULT_ALIQUOTAS: dict[ImpostoTipo, Decimal] = {
    ImpostoTipo.ISS: Decimal("5"),
    ImpostoTipo.ICMS: Decimal("18"),
    ImpostoTipo.IPI: Decimal("0"),
    ImpostoTipo.PIS: Decimal("0.65"),
    ImpostoTipo.COFINS: Decimal("3"),
    ImpostoTipo.CSLL: Decimal("0"),
    ImpostoTipo.IRRF: Decimal("0"),
}

# Prazo legal (horas) padrão para cancelamento por tipo de documento.
_DEFAULT_PRAZO_HORAS: dict[FiscalDocumentoTipo, int] = {
    FiscalDocumentoTipo.NFSE: 24,
    FiscalDocumentoTipo.NFE: 24,
}

# Máquinas de estado dos documentos fiscais.
NFSE_TRANSITIONS: dict[NfseStatus, set[NfseStatus]] = {
    NfseStatus.A_EMITIR: {
        NfseStatus.ENVIADA_PREFEITURA,
        NfseStatus.AUTORIZADA,
        NfseStatus.REJEITADA,
        NfseStatus.CANCELADA,
    },
    NfseStatus.ENVIADA_PREFEITURA: {NfseStatus.AUTORIZADA, NfseStatus.REJEITADA},
    NfseStatus.AUTORIZADA: {NfseStatus.CANCELADA},
    NfseStatus.REJEITADA: {NfseStatus.A_EMITIR},
    NfseStatus.CANCELADA: set(),
}

NFE_TRANSITIONS: dict[NfeStatus, set[NfeStatus]] = {
    NfeStatus.A_EMITIR: {
        NfeStatus.AUTORIZADA_SEFAZ,
        NfeStatus.REJEITADA,
        NfeStatus.DENEGADA,
        NfeStatus.CANCELADA,
    },
    NfeStatus.AUTORIZADA_SEFAZ: {NfeStatus.CANCELADA},
    NfeStatus.REJEITADA: {NfeStatus.A_EMITIR},
    NfeStatus.DENEGADA: set(),
    NfeStatus.CANCELADA: set(),
}


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(_MONEY)


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _localname(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


# ------------------------------------------------------------- Repositories
class ImpostoConfigRepository(BaseRepository[FisImpostoConfig]):
    model = FisImpostoConfig

    def list_query(self) -> Select[tuple[FisImpostoConfig]]:
        return self._base_query().order_by(FisImpostoConfig.created_at.desc())


class AliquotaRepository(BaseRepository[FisAliquota]):
    model = FisAliquota

    def list_by_config(self, config_id: uuid.UUID) -> Select[tuple[FisAliquota]]:
        return (
            self._base_query()
            .where(FisAliquota.config_id == config_id)
            .order_by(FisAliquota.tipo.asc())
        )


class XmlRepository(BaseRepository[FisXmlArquivo]):
    model = FisXmlArquivo

    async def get_by_hash(self, tenant_id: uuid.UUID, hash_sha256: str) -> FisXmlArquivo | None:
        stmt = self._base_query().where(
            FisXmlArquivo.tenant_id == tenant_id,
            FisXmlArquivo.hash_sha256 == hash_sha256,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    def list_query(
        self,
        *,
        tipo: FiscalXmlTipo | None = None,
        direcao: FiscalXmlDirecao | None = None,
    ) -> Select[tuple[FisXmlArquivo]]:
        stmt = self._base_query().order_by(FisXmlArquivo.created_at.desc())
        if tipo:
            stmt = stmt.where(FisXmlArquivo.tipo == tipo)
        if direcao:
            stmt = stmt.where(FisXmlArquivo.direcao == direcao)
        return stmt


class NfseRepository(BaseRepository[FisNfse]):
    model = FisNfse

    async def count_by_tenant(self, tenant_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(FisNfse)
            .where(FisNfse.tenant_id == tenant_id, FisNfse.deleted_at.is_(None))
        )
        return (await self.session.execute(stmt)).scalar_one()

    def list_query(
        self,
        *,
        status: NfseStatus | None = None,
        cliente_id: uuid.UUID | None = None,
        filial_id: uuid.UUID | None = None,
    ) -> Select[tuple[FisNfse]]:
        stmt = self._base_query().order_by(FisNfse.created_at.desc())
        if status:
            stmt = stmt.where(FisNfse.status == status)
        if cliente_id:
            stmt = stmt.where(FisNfse.cliente_id == cliente_id)
        if filial_id:
            stmt = stmt.where(FisNfse.filial_id == filial_id)
        return stmt


class NfeRepository(BaseRepository[FisNfe]):
    model = FisNfe

    async def count_by_tenant(self, tenant_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(FisNfe)
            .where(FisNfe.tenant_id == tenant_id, FisNfe.deleted_at.is_(None))
        )
        return (await self.session.execute(stmt)).scalar_one()

    def list_query(
        self, *, status: NfeStatus | None = None, filial_id: uuid.UUID | None = None
    ) -> Select[tuple[FisNfe]]:
        stmt = self._base_query().order_by(FisNfe.created_at.desc())
        if status:
            stmt = stmt.where(FisNfe.status == status)
        if filial_id:
            stmt = stmt.where(FisNfe.filial_id == filial_id)
        return stmt


class NfeItemRepository(BaseRepository[FisNfeItem]):
    model = FisNfeItem

    def list_by_nfe(self, nfe_id: uuid.UUID) -> Select[tuple[FisNfeItem]]:
        return (
            self._base_query()
            .where(FisNfeItem.nfe_id == nfe_id)
            .order_by(FisNfeItem.created_at.asc())
        )


class CancelamentoRepository(BaseRepository[FisCancelamento]):
    model = FisCancelamento

    async def count_by_tenant(self, tenant_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(FisCancelamento)
            .where(FisCancelamento.tenant_id == tenant_id, FisCancelamento.deleted_at.is_(None))
        )
        return (await self.session.execute(stmt)).scalar_one()

    def list_query(
        self,
        *,
        status: CancelamentoStatus | None = None,
        documento_tipo: FiscalDocumentoTipo | None = None,
    ) -> Select[tuple[FisCancelamento]]:
        stmt = self._base_query().order_by(FisCancelamento.solicitado_em.desc())
        if status:
            stmt = stmt.where(FisCancelamento.status == status)
        if documento_tipo:
            stmt = stmt.where(FisCancelamento.documento_tipo == documento_tipo)
        return stmt


class PrazoRepository(BaseRepository[FisPrazoCancelamento]):
    model = FisPrazoCancelamento

    def list_query(self) -> Select[tuple[FisPrazoCancelamento]]:
        return self._base_query().order_by(FisPrazoCancelamento.tipo_documento.asc())


# =========================================================== 10.5 Impostos
class ImpostoService:
    """Parametrização de regimes/alíquotas e apuração tributária (§10.5)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.config_repo = ImpostoConfigRepository(session)
        self.aliquota_repo = AliquotaRepository(session)

    # ---------------------------------------------------------- Configs
    async def list_configs(self, params: PageParams) -> Page[FisImpostoConfig]:
        return await self.config_repo.paginate(params, stmt=self.config_repo.list_query())

    async def get_config(self, config_id: uuid.UUID) -> FisImpostoConfig:
        item = await self.config_repo.get(config_id)
        if item is None:
            raise NotFoundError("Configuração fiscal não encontrada.")
        return item

    async def create_config(
        self, tenant_id: uuid.UUID, data: ImpostoConfigCreate
    ) -> FisImpostoConfig:
        config = FisImpostoConfig(tenant_id=tenant_id, **data.model_dump())
        self.config_repo.add(config)
        await self.config_repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="fis_imposto_config",
            entity_id=config.id,
            description=f"Config fiscal criada ({data.regime.value}).",
        )
        return config

    async def update_config(
        self, config_id: uuid.UUID, data: ImpostoConfigUpdate
    ) -> FisImpostoConfig:
        config = await self.get_config(config_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(config, key, value)
        await self.config_repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="fis_imposto_config",
            entity_id=config.id,
            description="Config fiscal atualizada.",
        )
        return config

    # ---------------------------------------------------------- Alíquotas
    async def list_aliquotas(self, config_id: uuid.UUID) -> list[FisAliquota]:
        stmt = self.aliquota_repo.list_by_config(config_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def create_aliquota(self, tenant_id: uuid.UUID, data: AliquotaCreate) -> FisAliquota:
        await self.get_config(data.config_id)
        aliquota = FisAliquota(tenant_id=tenant_id, **data.model_dump())
        self.aliquota_repo.add(aliquota)
        await self.aliquota_repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="fis_aliquota",
            entity_id=aliquota.id,
            description=f"Alíquota {data.tipo.value} {data.aliquota_percentual}% criada.",
        )
        return aliquota

    async def delete_aliquota(self, aliquota_id: uuid.UUID) -> None:
        aliquota = await self.aliquota_repo.get(aliquota_id)
        if aliquota is None:
            raise NotFoundError("Alíquota não encontrada.")
        await self.aliquota_repo.delete(aliquota)
        await self.aliquota_repo.flush()

    # ---------------------------------------------------------- Resolução
    async def get_config_vigente(
        self, filial_id: uuid.UUID | None, *, ref: date | None = None
    ) -> FisImpostoConfig | None:
        ref = ref or date.today()
        stmt = self.config_repo._base_query().where(
            FisImpostoConfig.ativo.is_(True),
            FisImpostoConfig.vigencia_inicio <= ref,
        )
        rows = list((await self.session.execute(stmt)).scalars().all())
        candidatos = [
            c
            for c in rows
            if (c.vigencia_fim is None or c.vigencia_fim >= ref)
            and (c.filial_id == filial_id or c.filial_id is None)
        ]
        if not candidatos:
            return None
        # Prefere config específica da filial sobre o padrão do tenant.
        candidatos.sort(key=lambda c: (c.filial_id is None, c.vigencia_inicio), reverse=False)
        especificas = [c for c in candidatos if c.filial_id == filial_id]
        return especificas[0] if especificas else candidatos[0]

    async def get_aliquota_vigente(
        self,
        filial_id: uuid.UUID | None,
        tipo: ImpostoTipo,
        *,
        ref: date | None = None,
        codigo: str | None = None,
    ) -> FisAliquota | None:
        config = await self.get_config_vigente(filial_id, ref=ref)
        if config is None:
            return None
        ref = ref or date.today()
        stmt = self.aliquota_repo.list_by_config(config.id).where(FisAliquota.tipo == tipo)
        rows = list((await self.session.execute(stmt)).scalars().all())
        vigentes = [
            a
            for a in rows
            if a.vigencia_inicio <= ref and (a.vigencia_fim is None or a.vigencia_fim >= ref)
        ]
        if codigo:
            especificas = [a for a in vigentes if a.servico_produto_codigo == codigo]
            if especificas:
                return especificas[0]
        return vigentes[0] if vigentes else None

    async def calcular_imposto(
        self,
        valor: Decimal,
        filial_id: uuid.UUID | None,
        tipo: ImpostoTipo,
        *,
        codigo: str | None = None,
    ) -> dict:
        aliquota = await self.get_aliquota_vigente(filial_id, tipo, codigo=codigo)
        if aliquota is not None:
            percentual = aliquota.aliquota_percentual
            retencao = aliquota.retencao
        else:
            percentual = _DEFAULT_ALIQUOTAS.get(tipo, _ZERO)
            retencao = False
        valor_imposto = _money(Decimal(valor) * percentual / Decimal(100))
        return {"percentual": percentual, "valor": valor_imposto, "retencao": retencao}

    async def calcular_iss(self, valor: Decimal, filial_id: uuid.UUID | None) -> dict:
        return await self.calcular_imposto(valor, filial_id, ImpostoTipo.ISS)

    async def calcular_icms(self, valor: Decimal, filial_id: uuid.UUID | None) -> dict:
        return await self.calcular_imposto(valor, filial_id, ImpostoTipo.ICMS)

    async def nfse_automatica(self, filial_id: uuid.UUID | None) -> bool:
        config = await self.get_config_vigente(filial_id)
        if config is None:
            return False
        if not await fiscal_emissao_habilitada(self.session, config.tenant_id):
            return False
        return bool(config.nfse_automatica)

    async def apuracao(self, periodo_inicio: date, periodo_fim: date) -> list[dict]:
        inicio = datetime.combine(periodo_inicio, datetime.min.time(), tzinfo=UTC)
        fim = datetime.combine(periodo_fim, datetime.max.time(), tzinfo=UTC)
        # ISS de NFS-e autorizadas
        nfse_stmt = select(FisNfse).where(
            FisNfse.deleted_at.is_(None),
            FisNfse.status == NfseStatus.AUTORIZADA,
            FisNfse.autorizada_em.is_not(None),
            FisNfse.autorizada_em >= inicio,
            FisNfse.autorizada_em <= fim,
        )
        nfses = list((await self.session.execute(nfse_stmt)).scalars().all())
        iss_base = sum((n.valor_servico for n in nfses), _ZERO)
        iss_valor = sum((n.valor_iss for n in nfses), _ZERO)
        # ICMS de NF-e autorizadas
        nfe_stmt = select(FisNfe).where(
            FisNfe.deleted_at.is_(None),
            FisNfe.status == NfeStatus.AUTORIZADA_SEFAZ,
            FisNfe.autorizada_em.is_not(None),
            FisNfe.autorizada_em >= inicio,
            FisNfe.autorizada_em <= fim,
        )
        nfes = list((await self.session.execute(nfe_stmt)).scalars().all())
        icms_valor = _ZERO
        nfe_base = _ZERO
        for nfe in nfes:
            nfe_base += nfe.valor_total
            item_stmt = NfeItemRepository(self.session).list_by_nfe(nfe.id)
            itens = list((await self.session.execute(item_stmt)).scalars().all())
            icms_valor += sum((i.icms_valor for i in itens), _ZERO)
        return [
            {
                "tipo": "ISS",
                "documentos": len(nfses),
                "base_calculo": _money(iss_base),
                "valor_imposto": _money(iss_valor),
            },
            {
                "tipo": "ICMS",
                "documentos": len(nfes),
                "base_calculo": _money(nfe_base),
                "valor_imposto": _money(icms_valor),
            },
        ]


# =========================================================== 10.3 XML
class XmlService:
    """Repositório central de XMLs fiscais (§10.3)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = XmlRepository(session)

    @staticmethod
    def _hash(conteudo: str) -> str:
        return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()

    @staticmethod
    def validar_schema_basico(conteudo_xml: str, *, tags_obrigatorias: list[str] | None = None) -> bool:
        """Valida se o XML é bem-formado e contém tags obrigatórias (não é XSD)."""
        try:
            root = ET.fromstring(conteudo_xml)
        except ET.ParseError:
            return False
        if not tags_obrigatorias:
            return True
        encontrados = {_localname(el.tag) for el in root.iter()}
        encontrados.add(_localname(root.tag))
        return all(tag in encontrados for tag in tags_obrigatorias)

    async def get(self, xml_id: uuid.UUID) -> FisXmlArquivo:
        item = await self.repo.get(xml_id)
        if item is None:
            raise NotFoundError("Arquivo XML não encontrado.")
        return item

    async def list_items(
        self,
        params: PageParams,
        *,
        tipo: FiscalXmlTipo | None = None,
        direcao: FiscalXmlDirecao | None = None,
    ) -> Page[FisXmlArquivo]:
        return await self.repo.paginate(
            params, stmt=self.repo.list_query(tipo=tipo, direcao=direcao)
        )

    async def archivar_emitido(
        self,
        tenant_id: uuid.UUID,
        *,
        tipo: FiscalXmlTipo,
        conteudo_xml: str,
        chave_acesso: str | None,
        documento_tipo: str | None,
        documento_id: uuid.UUID | None,
        filial_id: uuid.UUID | None,
        filename: str,
        periodo_ref: date | None = None,
    ) -> FisXmlArquivo:
        """Arquiva um XML emitido; nunca sobrescreve (dedup por hash)."""
        hash_sha256 = self._hash(conteudo_xml)
        existing = await self.repo.get_by_hash(tenant_id, hash_sha256)
        if existing is not None:
            return existing
        arquivo = FisXmlArquivo(
            tenant_id=tenant_id,
            tipo=tipo,
            direcao=FiscalXmlDirecao.EMITIDO,
            chave_acesso=chave_acesso,
            hash_sha256=hash_sha256,
            conteudo_xml=conteudo_xml,
            documento_tipo=documento_tipo,
            documento_id=documento_id,
            filial_id=filial_id,
            periodo_ref=periodo_ref or date.today(),
            filename=filename,
            tamanho_bytes=len(conteudo_xml.encode("utf-8")),
        )
        self.repo.add(arquivo)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="fis_xml_arquivo",
            entity_id=arquivo.id,
            description=f"XML emitido arquivado ({tipo.value}).",
        )
        return arquivo

    async def importar_xml_fornecedor(
        self,
        tenant_id: uuid.UUID,
        conteudo_xml: str,
        *,
        filial_id: uuid.UUID | None = None,
        filename: str | None = None,
    ) -> FisXmlArquivo:
        """Importa um XML de fornecedor e opcionalmente rascunha um Contas a Pagar."""
        if not self.validar_schema_basico(conteudo_xml):
            raise ValidationError("XML inválido ou mal formado.")

        chave, cnpj, valor = self._parse_nfe_recebida(conteudo_xml)
        hash_sha256 = self._hash(conteudo_xml)
        existing = await self.repo.get_by_hash(tenant_id, hash_sha256)
        if existing is not None:
            return existing

        arquivo = FisXmlArquivo(
            tenant_id=tenant_id,
            tipo=FiscalXmlTipo.NFE_RECEBIDA,
            direcao=FiscalXmlDirecao.RECEBIDO,
            chave_acesso=chave,
            hash_sha256=hash_sha256,
            conteudo_xml=conteudo_xml,
            documento_tipo=None,
            documento_id=None,
            filial_id=filial_id,
            periodo_ref=date.today(),
            filename=filename or f"nfe_{(chave or hash_sha256)[:20]}.xml",
            tamanho_bytes=len(conteudo_xml.encode("utf-8")),
            fornecedor_cnpj=cnpj,
        )
        self.repo.add(arquivo)
        await self.repo.flush()

        # Rascunha um título a pagar quando há valor, CNPJ e filial de destino.
        if valor and valor > _ZERO and cnpj and filial_id is not None:
            try:
                from app.modules.financeiro.schemas import ContaPagarCreate
                from app.modules.financeiro.service import ContaPagarService
                from app.shared.enums import ContaPagarOrigem

                titulo = await ContaPagarService(self.session).create(
                    tenant_id,
                    ContaPagarCreate(
                        beneficiario_nome=f"Fornecedor CNPJ {cnpj}",
                        filial_id=filial_id,
                        descricao=f"NF-e recebida {chave or ''}".strip(),
                        valor_original=_money(valor),
                        vencimento=date.today() + timedelta(days=30),
                        origem=ContaPagarOrigem.FORNECEDOR,
                    ),
                )
                arquivo.titulo_pagar_id = titulo.id
                await self.repo.flush()
            except Exception:  # noqa: BLE001 - importação não deve falhar por CP
                pass

        await audit_service.record(
            AuditAction.CREATE,
            entity="fis_xml_arquivo",
            entity_id=arquivo.id,
            description="XML de fornecedor importado.",
        )
        return arquivo

    def _parse_nfe_recebida(self, conteudo_xml: str) -> tuple[str | None, str | None, Decimal | None]:
        """Extrai chave, CNPJ do emitente e valor total de um XML de NF-e."""
        try:
            root = ET.fromstring(conteudo_xml)
        except ET.ParseError:
            return None, None, None

        chave: str | None = None
        cnpj: str | None = None
        valor: Decimal | None = None

        for el in root.iter():
            name = _localname(el.tag)
            if name == "infNFe" and chave is None:
                raw = el.get("Id") or ""
                digits = "".join(ch for ch in raw if ch.isdigit())
                if len(digits) >= 44:
                    chave = digits[-44:]
            elif name == "chNFe" and chave is None and el.text:
                digits = "".join(ch for ch in el.text if ch.isdigit())
                if len(digits) >= 44:
                    chave = digits[-44:]
            elif name == "vNF" and valor is None and el.text:
                try:
                    valor = Decimal(el.text.strip())
                except (ArithmeticError, ValueError):
                    valor = None

        # CNPJ do emitente (primeiro CNPJ dentro de <emit>).
        for el in root.iter():
            if _localname(el.tag) == "emit":
                for child in el.iter():
                    if _localname(child.tag) == "CNPJ" and child.text:
                        cnpj = child.text.strip()
                        break
                break
        return chave, cnpj, valor

    async def exportar_lote(
        self,
        periodo_inicio: date,
        periodo_fim: date,
        *,
        tipos: list[FiscalXmlTipo] | None = None,
    ) -> bytes:
        """Exporta os XMLs do período em um ZIP (bytes) para o contador."""
        stmt = self.repo._base_query().where(
            FisXmlArquivo.periodo_ref >= periodo_inicio,
            FisXmlArquivo.periodo_ref <= periodo_fim,
        )
        if tipos:
            stmt = stmt.where(FisXmlArquivo.tipo.in_(tipos))
        arquivos = list((await self.session.execute(stmt)).scalars().all())
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            usados: set[str] = set()
            for arq in arquivos:
                name = arq.filename or f"{arq.id}.xml"
                if name in usados:
                    name = f"{arq.id}_{name}"
                usados.add(name)
                zf.writestr(f"{arq.tipo.value}/{name}", arq.conteudo_xml)
        return buffer.getvalue()


# =========================================================== 10.4 Cancelamentos
class CancelamentoService:
    """Central de eventos fiscais de cancelamento/correção (§10.4)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CancelamentoRepository(session)
        self.prazo_repo = PrazoRepository(session)

    async def next_numero(self, tenant_id: uuid.UUID) -> str:
        count = await self.repo.count_by_tenant(tenant_id)
        return f"EVT-{count + 1:06d}"

    async def list_items(
        self,
        params: PageParams,
        *,
        status: CancelamentoStatus | None = None,
        documento_tipo: FiscalDocumentoTipo | None = None,
    ) -> Page[FisCancelamento]:
        return await self.repo.paginate(
            params, stmt=self.repo.list_query(status=status, documento_tipo=documento_tipo)
        )

    async def get(self, evento_id: uuid.UUID) -> FisCancelamento:
        item = await self.repo.get(evento_id)
        if item is None:
            raise NotFoundError("Evento fiscal não encontrado.")
        return item

    async def _horas_limite(
        self, tipo_documento: FiscalDocumentoTipo, *, uf: str | None, municipio_ibge: str | None
    ) -> int:
        stmt = self.prazo_repo._base_query().where(
            FisPrazoCancelamento.tipo_documento == tipo_documento,
            FisPrazoCancelamento.ativo.is_(True),
        )
        rows = list((await self.session.execute(stmt)).scalars().all())
        # Prioriza município, depois UF, depois regra genérica.
        for row in rows:
            if municipio_ibge and row.municipio_ibge == municipio_ibge:
                return row.horas_limite
        for row in rows:
            if uf and row.uf == uf:
                return row.horas_limite
        for row in rows:
            if row.uf is None and row.municipio_ibge is None:
                return row.horas_limite
        return _DEFAULT_PRAZO_HORAS.get(tipo_documento, 24)

    async def solicitar(
        self,
        tenant_id: uuid.UUID,
        data: CancelamentoCreate,
        *,
        user_id: uuid.UUID | None = None,
        referencia_em: datetime | None = None,
        uf: str | None = None,
        municipio_ibge: str | None = None,
    ) -> FisCancelamento:
        horas_limite = await self._horas_limite(
            data.documento_tipo, uf=uf, municipio_ibge=municipio_ibge
        )
        fora_do_prazo = False
        if referencia_em is not None:
            ref = referencia_em
            if ref.tzinfo is None:
                ref = ref.replace(tzinfo=UTC)
            fora_do_prazo = _now() - ref > timedelta(hours=horas_limite)

        if fora_do_prazo and data.tipo_evento == CancelamentoEventoTipo.CANCELAMENTO:
            raise BusinessRuleError(
                "Cancelamento fora do prazo legal. Emita carta de correção ou nota de "
                "estorno em vez do cancelamento direto.",
                code="cancelamento_fora_prazo",
            )

        evento = FisCancelamento(
            tenant_id=tenant_id,
            numero=await self.next_numero(tenant_id),
            documento_tipo=data.documento_tipo,
            documento_id=data.documento_id,
            tipo_evento=data.tipo_evento,
            motivo=data.motivo,
            justificativa_completa=data.justificativa_completa,
            solicitado_em=_now(),
            status=CancelamentoStatus.SOLICITADO,
            fora_do_prazo=fora_do_prazo,
            user_id=user_id,
        )
        self.repo.add(evento)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="fis_cancelamento",
            entity_id=evento.id,
            description=(
                f"Evento fiscal {evento.numero} ({data.tipo_evento.value}) solicitado "
                f"para {data.documento_tipo.value}."
            ),
        )
        return evento

    async def processar(
        self, evento_id: uuid.UUID, *, chave_acesso: str | None = None
    ) -> FisCancelamento:
        """Processa o evento no provedor (simulado) e confirma o protocolo."""
        evento = await self.get(evento_id)
        if evento.status in {CancelamentoStatus.CONFIRMADO, CancelamentoStatus.REJEITADO}:
            return evento
        protocolo: str | None = None
        if evento.documento_tipo == FiscalDocumentoTipo.NFSE:
            provedor = await get_nfse_provider(self.session, evento.tenant_id)
            resultado = provedor.cancelar(
                chave_acesso=chave_acesso or "", motivo=evento.motivo
            )
            protocolo = resultado.protocolo
            confirmado = resultado.confirmado
        else:
            provedor_nfe = await get_nfe_provider(self.session, evento.tenant_id)
            resultado_nfe = provedor_nfe.cancelar(
                chave_acesso=chave_acesso or "", motivo=evento.motivo
            )
            protocolo = resultado_nfe.protocolo
            confirmado = resultado_nfe.confirmado
        evento.protocolo_retorno = protocolo
        evento.processado_em = _now()
        evento.status = (
            CancelamentoStatus.CONFIRMADO if confirmado else CancelamentoStatus.REJEITADO
        )
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="fis_cancelamento",
            entity_id=evento.id,
            description=f"Evento fiscal {evento.numero} {evento.status.value}.",
        )
        return evento

    # -------------------------------------------------------- Prazos (CRUD)
    async def list_prazos(self, params: PageParams) -> Page[FisPrazoCancelamento]:
        return await self.prazo_repo.paginate(params, stmt=self.prazo_repo.list_query())

    async def create_prazo(
        self, tenant_id: uuid.UUID, data: PrazoCancelamentoCreate
    ) -> FisPrazoCancelamento:
        prazo = FisPrazoCancelamento(tenant_id=tenant_id, **data.model_dump())
        self.prazo_repo.add(prazo)
        await self.prazo_repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="fis_prazo_cancelamento",
            entity_id=prazo.id,
            description=f"Prazo de cancelamento {data.tipo_documento.value}={data.horas_limite}h.",
        )
        return prazo


# =========================================================== 10.1 NFS-e
class NfseService:
    """Emissão e gestão de NFS-e (§10.1)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = NfseRepository(session)
        self.imposto_svc = ImpostoService(session)
        self.xml_svc = XmlService(session)

    async def next_numero(self, tenant_id: uuid.UUID) -> str:
        count = await self.repo.count_by_tenant(tenant_id)
        return f"{count + 1:06d}"

    async def list_items(
        self,
        params: PageParams,
        *,
        status: NfseStatus | None = None,
        cliente_id: uuid.UUID | None = None,
        filial_id: uuid.UUID | None = None,
    ) -> Page[FisNfse]:
        return await self.repo.paginate(
            params,
            stmt=self.repo.list_query(status=status, cliente_id=cliente_id, filial_id=filial_id),
        )

    async def get(self, nfse_id: uuid.UUID) -> FisNfse:
        item = await self.repo.get(nfse_id)
        if item is None:
            raise NotFoundError("NFS-e não encontrada.")
        return item

    async def _calcular_iss(
        self, valor_servico: Decimal, filial_id: uuid.UUID, *, aliquota_iss: Decimal | None, retencao: bool
    ) -> tuple[Decimal, Decimal, Decimal, bool]:
        if aliquota_iss is None:
            calc = await self.imposto_svc.calcular_iss(valor_servico, filial_id)
            aliquota_iss = calc["percentual"]
            retencao = retencao or calc["retencao"]
        valor_iss = _money(Decimal(valor_servico) * aliquota_iss / Decimal(100))
        valor_iss_retido = valor_iss if retencao else _ZERO
        return aliquota_iss, valor_iss, valor_iss_retido, retencao

    async def create(
        self, tenant_id: uuid.UUID, data: NfseCreate, *, automatica: bool = False
    ) -> FisNfse:
        await assert_fiscal_emissao_habilitada(self.session, tenant_id)
        valor = _money(data.valor_servico)
        aliquota_iss, valor_iss, valor_iss_retido, retencao = await self._calcular_iss(
            valor, data.filial_id, aliquota_iss=data.aliquota_iss, retencao=data.retencao_iss
        )
        nfse = FisNfse(
            tenant_id=tenant_id,
            numero=await self.next_numero(tenant_id),
            serie="A",
            status=NfseStatus.A_EMITIR,
            contrato_id=data.contrato_id,
            fatura_id=data.fatura_id,
            cliente_id=data.cliente_id,
            filial_id=data.filial_id,
            municipio_ibge=data.municipio_ibge,
            municipio_nome=data.municipio_nome,
            valor_servico=valor,
            aliquota_iss=aliquota_iss,
            valor_iss=valor_iss,
            valor_iss_retido=valor_iss_retido,
            retencao_iss=retencao,
            discriminacao=data.discriminacao or "Serviço de locação de bem móvel.",
            provedor=(await get_nfse_provider(self.session, tenant_id)).nome,
            automatica=automatica,
        )
        self.repo.add(nfse)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="fis_nfse",
            entity_id=nfse.id,
            description=f"NFS-e criada {nfse.serie}-{nfse.numero} ({valor}).",
        )
        return nfse

    async def create_from_contrato(
        self, contrato_id: uuid.UUID, *, automatica: bool = False
    ) -> FisNfse:
        from app.modules.locacoes.service import ContratoService

        contrato = await ContratoService(self.session).get(contrato_id)
        valor = contrato.valor_final or contrato.valor_total
        return await self.create(
            contrato.tenant_id,
            NfseCreate(
                filial_id=contrato.filial_retirada_id,
                cliente_id=contrato.cliente_id,
                contrato_id=contrato.id,
                valor_servico=_money(valor),
                discriminacao=f"Locação de veículo — contrato {contrato.numero}.",
            ),
            automatica=automatica,
        )

    async def create_from_fatura(
        self, fatura_id: uuid.UUID, *, automatica: bool = False
    ) -> FisNfse:
        from app.modules.financeiro.service import FaturamentoService

        fat_svc = FaturamentoService(self.session)
        fatura = await fat_svc.get_fatura(fatura_id)
        titulos = await fat_svc.list_titulos(fatura_id)
        filial_id = titulos[0].filial_id if titulos else None
        if filial_id is None:
            raise BusinessRuleError("Fatura sem títulos vinculados para emitir NFS-e.")
        return await self.create(
            fatura.tenant_id,
            NfseCreate(
                filial_id=filial_id,
                cliente_id=fatura.cliente_id,
                fatura_id=fatura.id,
                valor_servico=_money(fatura.valor_total),
                discriminacao=f"Serviços faturados — fatura {fatura.numero}.",
            ),
            automatica=automatica,
        )

    async def emitir(self, nfse_id: uuid.UUID) -> FisNfse:
        nfse = await self.get(nfse_id)
        await assert_fiscal_emissao_habilitada(self.session, nfse.tenant_id)
        if nfse.status not in {NfseStatus.A_EMITIR, NfseStatus.REJEITADA}:
            raise BusinessRuleError(
                f"NFS-e {nfse.serie}-{nfse.numero} não está apta para emissão "
                f"(status {nfse.status.value})."
            )
        tomador_nome = await self._tomador_nome(nfse.cliente_id)
        cnpj_prestador = await self._cnpj_prestador(nfse.filial_id)
        provedor = await get_nfse_provider(self.session, nfse.tenant_id)
        resultado = provedor.emitir(
            numero=nfse.numero,
            serie=nfse.serie,
            cnpj_prestador=cnpj_prestador,
            tomador_nome=tomador_nome,
            municipio_ibge=nfse.municipio_ibge,
            valor_servico=nfse.valor_servico,
            aliquota_iss=nfse.aliquota_iss,
            valor_iss=nfse.valor_iss,
            discriminacao=nfse.discriminacao or "",
        )
        nfse.emitida_em = _now()
        nfse.provedor = provedor.nome
        if not resultado.autorizada:
            nfse.status = NfseStatus.REJEITADA
            nfse.rejeicao_motivo = resultado.rejeicao_motivo
            await self.repo.flush()
            await audit_service.record(
                AuditAction.UPDATE,
                entity="fis_nfse",
                entity_id=nfse.id,
                description=f"NFS-e {nfse.numero} rejeitada: {resultado.rejeicao_motivo}.",
            )
            return nfse

        arquivo = await self.xml_svc.archivar_emitido(
            nfse.tenant_id,
            tipo=FiscalXmlTipo.NFSE_EMITIDA,
            conteudo_xml=resultado.xml,
            chave_acesso=resultado.chave_acesso,
            documento_tipo="nfse",
            documento_id=nfse.id,
            filial_id=nfse.filial_id,
            filename=f"nfse_{nfse.serie}_{nfse.numero}.xml",
        )
        nfse.chave_acesso = resultado.chave_acesso
        nfse.protocolo = resultado.protocolo
        nfse.xml_arquivo_id = arquivo.id
        nfse.status = NfseStatus.AUTORIZADA
        nfse.autorizada_em = _now()
        nfse.rejeicao_motivo = None
        nfse.pdf_url = f"/fiscal/nfse/{nfse.id}/danfse"
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="fis_nfse",
            entity_id=nfse.id,
            description=f"NFS-e {nfse.numero} autorizada (chave {resultado.chave_acesso}).",
        )
        return nfse

    async def cancelar(
        self, nfse_id: uuid.UUID, motivo: str, *, user_id: uuid.UUID | None = None
    ) -> FisNfse:
        nfse = await self.get(nfse_id)
        if nfse.status != NfseStatus.AUTORIZADA:
            raise BusinessRuleError("Somente NFS-e autorizada pode ser cancelada.")
        canc_svc = CancelamentoService(self.session)
        evento = await canc_svc.solicitar(
            nfse.tenant_id,
            CancelamentoCreate(
                documento_tipo=FiscalDocumentoTipo.NFSE,
                documento_id=nfse.id,
                tipo_evento=CancelamentoEventoTipo.CANCELAMENTO,
                motivo=motivo,
            ),
            user_id=user_id,
            referencia_em=nfse.autorizada_em or nfse.emitida_em,
            municipio_ibge=nfse.municipio_ibge,
        )
        await canc_svc.processar(evento.id, chave_acesso=nfse.chave_acesso)
        nfse.status = NfseStatus.CANCELADA
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="fis_nfse",
            entity_id=nfse.id,
            description=f"NFS-e {nfse.numero} cancelada ({motivo}).",
        )
        return nfse

    async def reprocessar_rejeitadas(self) -> int:
        """Reenvia NFS-e rejeitadas ao provedor; retorna quantas foram autorizadas."""
        from app.core import context

        tenant_id = context.get_tenant_id()
        if tenant_id is None or not await fiscal_emissao_habilitada(self.session, tenant_id):
            return 0
        stmt = self.repo.list_query(status=NfseStatus.REJEITADA)
        rows = list((await self.session.execute(stmt)).scalars().all())
        autorizadas = 0
        for nfse in rows:
            try:
                result = await self.emitir(nfse.id)
            except BusinessRuleError:
                continue
            if result.status == NfseStatus.AUTORIZADA:
                autorizadas += 1
        return autorizadas

    async def apuracao_iss(self, periodo_inicio: date, periodo_fim: date) -> dict:
        linhas = await self.imposto_svc.apuracao(periodo_inicio, periodo_fim)
        return next((linha for linha in linhas if linha["tipo"] == "ISS"), linhas[0])

    async def _tomador_nome(self, cliente_id: uuid.UUID | None) -> str:
        if cliente_id is None:
            return "Consumidor não identificado"
        try:
            from app.modules.cadastros.service import ClienteService

            cliente = await ClienteService(self.session).get(cliente_id)
            return getattr(cliente, "nome", "Tomador")
        except Exception:  # noqa: BLE001
            return "Tomador"

    async def _cnpj_prestador(self, filial_id: uuid.UUID) -> str:
        try:
            from app.modules.tenants.service import FilialService

            filial = await FilialService(self.session).get_filial(filial_id)
            return getattr(filial, "cnpj", None) or "00000000000000"
        except Exception:  # noqa: BLE001
            return "00000000000000"


# =========================================================== 10.2 NF-e
class NfeService:
    """Emissão e gestão de NF-e (§10.2)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = NfeRepository(session)
        self.item_repo = NfeItemRepository(session)
        self.imposto_svc = ImpostoService(session)
        self.xml_svc = XmlService(session)

    async def next_numero(self, tenant_id: uuid.UUID) -> str:
        count = await self.repo.count_by_tenant(tenant_id)
        return f"{count + 1:06d}"

    async def list_items(
        self,
        params: PageParams,
        *,
        status: NfeStatus | None = None,
        filial_id: uuid.UUID | None = None,
    ) -> Page[FisNfe]:
        return await self.repo.paginate(
            params, stmt=self.repo.list_query(status=status, filial_id=filial_id)
        )

    async def get(self, nfe_id: uuid.UUID) -> FisNfe:
        item = await self.repo.get(nfe_id)
        if item is None:
            raise NotFoundError("NF-e não encontrada.")
        return item

    async def list_nfe_itens(self, nfe_id: uuid.UUID) -> list[FisNfeItem]:
        stmt = self.item_repo.list_by_nfe(nfe_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def create(self, tenant_id: uuid.UUID, data: NfeCreate) -> FisNfe:
        await assert_fiscal_emissao_habilitada(self.session, tenant_id)
        nfe = FisNfe(
            tenant_id=tenant_id,
            numero=await self.next_numero(tenant_id),
            serie="1",
            status=NfeStatus.A_EMITIR,
            operacao=data.operacao,
            destinatario_nome=data.destinatario_nome,
            destinatario_doc=data.destinatario_doc,
            destinatario_id=data.destinatario_id,
            filial_id=data.filial_id,
            veiculo_id=data.veiculo_id,
            natureza_operacao=data.natureza_operacao or data.operacao.value.capitalize(),
            cfop_padrao=data.cfop_padrao,
            valor_total=_ZERO,
            provedor=(await get_nfe_provider(self.session, tenant_id)).nome,
        )
        self.repo.add(nfe)
        await self.repo.flush()

        total = _ZERO
        for item_in in data.itens:
            valor_total_item = _money(Decimal(item_in.quantidade) * Decimal(item_in.valor_unitario))
            icms_valor = _money(valor_total_item * item_in.icms_aliquota / Decimal(100))
            ipi_valor = _money(valor_total_item * item_in.ipi_aliquota / Decimal(100))
            self.item_repo.add(
                FisNfeItem(
                    tenant_id=tenant_id,
                    nfe_id=nfe.id,
                    descricao=item_in.descricao,
                    codigo=item_in.codigo,
                    ncm=item_in.ncm,
                    cfop=item_in.cfop or data.cfop_padrao,
                    quantidade=item_in.quantidade,
                    valor_unitario=_money(item_in.valor_unitario),
                    valor_total=valor_total_item,
                    icms_aliquota=item_in.icms_aliquota,
                    icms_valor=icms_valor,
                    ipi_aliquota=item_in.ipi_aliquota,
                    ipi_valor=ipi_valor,
                    produto_ref_tipo=item_in.produto_ref_tipo,
                    produto_ref_id=item_in.produto_ref_id,
                )
            )
            total += valor_total_item
        await self.item_repo.flush()
        nfe.valor_total = _money(total)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="fis_nfe",
            entity_id=nfe.id,
            description=f"NF-e criada {nfe.serie}-{nfe.numero} ({nfe.valor_total}).",
        )
        return nfe

    async def create_from_veiculo_baixar(
        self,
        tenant_id: uuid.UUID,
        *,
        veiculo_id: uuid.UUID,
        filial_id: uuid.UUID,
        destinatario_nome: str,
        destinatario_doc: str | None,
        valor: Decimal,
        descricao: str,
    ) -> FisNfe:
        """Gera uma NF-e de venda (rascunho a_emitir) para um veículo baixado."""
        return await self.create(
            tenant_id,
            NfeCreate(
                filial_id=filial_id,
                destinatario_nome=destinatario_nome,
                destinatario_doc=destinatario_doc,
                operacao=NfeOperacao.VENDA,
                veiculo_id=veiculo_id,
                natureza_operacao="Venda de ativo imobilizado",
                cfop_padrao="5551",
                itens=[
                    NfeItemInput(
                        descricao=descricao,
                        quantidade=Decimal("1"),
                        valor_unitario=_money(valor),
                        cfop="5551",
                    )
                ],
            ),
        )

    async def emitir(self, nfe_id: uuid.UUID) -> FisNfe:
        nfe = await self.get(nfe_id)
        await assert_fiscal_emissao_habilitada(self.session, nfe.tenant_id)
        if nfe.status not in {NfeStatus.A_EMITIR, NfeStatus.REJEITADA}:
            raise BusinessRuleError(
                f"NF-e {nfe.serie}-{nfe.numero} não está apta para emissão "
                f"(status {nfe.status.value})."
            )
        itens = await self.list_nfe_itens(nfe_id)
        payload = [
            NfeItemPayload(
                descricao=i.descricao,
                quantidade=i.quantidade,
                valor_total=i.valor_total,
                ncm=i.ncm,
                cfop=i.cfop,
            )
            for i in itens
        ]
        cnpj_emitente = await self._cnpj_emitente(nfe.filial_id)
        provedor = await get_nfe_provider(self.session, nfe.tenant_id)
        resultado = provedor.emitir(
            numero=nfe.numero,
            serie=nfe.serie,
            cnpj_emitente=cnpj_emitente,
            destinatario_nome=nfe.destinatario_nome,
            destinatario_doc=nfe.destinatario_doc,
            natureza_operacao=nfe.natureza_operacao or "Venda",
            valor_total=nfe.valor_total,
            itens=payload,
        )
        nfe.emitida_em = _now()
        nfe.provedor = provedor.nome
        if not resultado.autorizada:
            nfe.status = NfeStatus.REJEITADA
            nfe.rejeicao_motivo = resultado.rejeicao_motivo
            await self.repo.flush()
            await audit_service.record(
                AuditAction.UPDATE,
                entity="fis_nfe",
                entity_id=nfe.id,
                description=f"NF-e {nfe.numero} rejeitada: {resultado.rejeicao_motivo}.",
            )
            return nfe

        arquivo = await self.xml_svc.archivar_emitido(
            nfe.tenant_id,
            tipo=FiscalXmlTipo.NFE_EMITIDA,
            conteudo_xml=resultado.xml,
            chave_acesso=resultado.chave_acesso,
            documento_tipo="nfe",
            documento_id=nfe.id,
            filial_id=nfe.filial_id,
            filename=f"nfe_{nfe.serie}_{nfe.numero}.xml",
        )
        nfe.chave_acesso = resultado.chave_acesso
        nfe.protocolo = resultado.protocolo
        nfe.xml_arquivo_id = arquivo.id
        nfe.status = NfeStatus.AUTORIZADA_SEFAZ
        nfe.autorizada_em = _now()
        nfe.rejeicao_motivo = None
        nfe.pdf_url = f"/fiscal/nfe/{nfe.id}/danfe"
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="fis_nfe",
            entity_id=nfe.id,
            description=f"NF-e {nfe.numero} autorizada (chave {resultado.chave_acesso}).",
        )
        return nfe

    async def cancelar(
        self, nfe_id: uuid.UUID, motivo: str, *, user_id: uuid.UUID | None = None
    ) -> FisNfe:
        nfe = await self.get(nfe_id)
        if nfe.status != NfeStatus.AUTORIZADA_SEFAZ:
            raise BusinessRuleError("Somente NF-e autorizada pode ser cancelada.")
        canc_svc = CancelamentoService(self.session)
        evento = await canc_svc.solicitar(
            nfe.tenant_id,
            CancelamentoCreate(
                documento_tipo=FiscalDocumentoTipo.NFE,
                documento_id=nfe.id,
                tipo_evento=CancelamentoEventoTipo.CANCELAMENTO,
                motivo=motivo,
            ),
            user_id=user_id,
            referencia_em=nfe.autorizada_em or nfe.emitida_em,
        )
        await canc_svc.processar(evento.id, chave_acesso=nfe.chave_acesso)
        nfe.status = NfeStatus.CANCELADA
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="fis_nfe",
            entity_id=nfe.id,
            description=f"NF-e {nfe.numero} cancelada ({motivo}).",
        )
        return nfe

    async def reprocessar_rejeitadas(self) -> int:
        """Reenvia NF-e rejeitadas à SEFAZ; retorna quantas foram autorizadas."""
        from app.core import context

        tenant_id = context.get_tenant_id()
        if tenant_id is None or not await fiscal_emissao_habilitada(self.session, tenant_id):
            return 0
        stmt = self.repo.list_query(status=NfeStatus.REJEITADA)
        rows = list((await self.session.execute(stmt)).scalars().all())
        autorizadas = 0
        for nfe in rows:
            try:
                result = await self.emitir(nfe.id)
            except BusinessRuleError:
                continue
            if result.status == NfeStatus.AUTORIZADA_SEFAZ:
                autorizadas += 1
        return autorizadas

    async def _cnpj_emitente(self, filial_id: uuid.UUID) -> str:
        try:
            from app.modules.tenants.service import FilialService

            filial = await FilialService(self.session).get_filial(filial_id)
            return getattr(filial, "cnpj", None) or "00000000000000"
        except Exception:  # noqa: BLE001
            return "00000000000000"
