"""Serviço de agregação de indicadores do dashboard (§1)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import has_permission
from app.modules.cadastros.models_extra import Motorista
from app.modules.comercial.models import CrmOportunidade, CrmProposta
from app.modules.financeiro.models import (
    FinCaixaLancamento,
    FinCaixaSessao,
    FinContaPagar,
    FinContaReceber,
)
from app.modules.fiscal.models import FisNfe, FisNfse
from app.modules.frota.models import FrotaDocumento, FrotaVeiculo
from app.modules.identity.models import User
from app.modules.locacoes.models import LocContrato, LocMulta
from app.modules.manutencao.models import ManOrdemServico, ManPneu, ManPlanoPreventivo, ManVeiculoPlano
from app.modules.manutencao.service import _calc_preventiva_urgencia
from app.modules.reservas.models import ResReserva
from app.modules.tenants.models import Filial
from app.shared.enums import (
    CaixaLancamentoTipo,
    CaixaSessaoStatus,
    CadastroStatus,
    ContratoStatus,
    CrmEstagio,
    CrmPropostaStatus,
    FilialStatus,
    NfeStatus,
    NfseStatus,
    OrdemServicoStatus,
    PneuStatus,
    ReservaStatus,
    TituloStatus,
    VeiculoStatus,
)


@dataclass(slots=True)
class OcupacaoPonto:
    label: str
    pct: float


@dataclass(slots=True)
class FrotaKpis:
    total: int
    disponiveis: int
    locados: int
    manutencao: int
    bloqueados: int
    ocupacao_pct: float


@dataclass(slots=True)
class ReservasKpis:
    hoje: int
    proximas_48h: int
    pendentes: int


@dataclass(slots=True)
class LocacoesKpis:
    ativos: int
    vencendo_24h: int
    vencendo_48h: int


@dataclass(slots=True)
class FinanceiroKpis:
    faturamento_dia: Decimal
    faturamento_mes: Decimal
    receber_aberto: Decimal
    receber_vencido: Decimal
    pagar_aberto: Decimal
    pagar_vencido: Decimal
    saldo_caixa: Decimal


@dataclass(slots=True)
class ManutencaoKpis:
    os_abertas: int
    aguardando_aprovacao: int
    preventiva_pendente: int
    pneus_alerta: int


@dataclass(slots=True)
class ComercialKpis:
    oportunidades_abertas: int
    propostas_abertas: int
    propostas_aceitas_mes: int
    taxa_conversao_pct: float
    funil_por_estagio: dict[str, int]


@dataclass(slots=True)
class AlertaItem:
    tipo: str
    mensagem: str
    url: str | None = None


@dataclass(slots=True)
class DashboardSnapshot:
    """Indicadores consolidados exibidos na visão geral."""

    total_users: int = 0
    active_users: int = 0
    total_filiais: int = 0
    active_filiais: int = 0
    frota: FrotaKpis | None = None
    reservas: ReservasKpis | None = None
    locacoes: LocacoesKpis | None = None
    financeiro: FinanceiroKpis | None = None
    manutencao: ManutencaoKpis | None = None
    comercial: ComercialKpis | None = None
    ocupacao_30: list[OcupacaoPonto] = field(default_factory=list)
    ocupacao_90: list[OcupacaoPonto] = field(default_factory=list)
    alertas: list[AlertaItem] = field(default_factory=list)


class DashboardService:
    """Calcula KPIs do tenant, respeitando escopo de filial e permissões."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _count(self, stmt) -> int:
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def _sum_decimal(self, stmt) -> Decimal:
        value = (await self.session.execute(stmt)).scalar_one()
        return Decimal(str(value or 0))

    def _filial_filter(self, column, filial_id: uuid.UUID | None):
        if filial_id is None:
            return True
        return column == filial_id

    async def get_snapshot(
        self,
        *,
        permissions: set[str],
        is_superuser: bool = False,
        filial_id: uuid.UUID | None = None,
    ) -> DashboardSnapshot:
        snap = DashboardSnapshot()
        snap.total_users = await self._count(
            select(func.count()).select_from(User).where(User.deleted_at.is_(None))
        )
        snap.active_users = await self._count(
            select(func.count())
            .select_from(User)
            .where(User.deleted_at.is_(None), User.is_active.is_(True))
        )
        snap.total_filiais = await self._count(
            select(func.count()).select_from(Filial).where(Filial.deleted_at.is_(None))
        )
        snap.active_filiais = await self._count(
            select(func.count())
            .select_from(Filial)
            .where(Filial.deleted_at.is_(None), Filial.status == FilialStatus.ACTIVE)
        )

        if self._can(permissions, "frota.veiculo.visualizar", is_superuser):
            snap.frota = await self._frota_kpis(filial_id)
            snap.alertas.extend(await self._alertas_frota(filial_id))
            if self._can(permissions, "locacoes.contrato.visualizar", is_superuser):
                snap.ocupacao_30 = await self._ocupacao_serie(filial_id, days=30, step=1)
                snap.ocupacao_90 = await self._ocupacao_serie(filial_id, days=90, step=7)

        if self._can(permissions, "reservas.reserva.visualizar", is_superuser):
            snap.reservas = await self._reservas_kpis(filial_id)

        if self._can(permissions, "locacoes.contrato.visualizar", is_superuser):
            snap.locacoes = await self._locacoes_kpis(filial_id)
            snap.alertas.extend(await self._alertas_locacoes(filial_id))
            snap.alertas.extend(await self._alertas_contratos_atrasados(filial_id))

        if self._can(permissions, "financeiro.receber.visualizar", is_superuser):
            snap.financeiro = await self._financeiro_kpis(filial_id)

        if self._can(permissions, "manutencao.os.visualizar", is_superuser):
            snap.manutencao = await self._manutencao_kpis(filial_id)

        if self._can(permissions, "comercial.funil.visualizar", is_superuser):
            snap.comercial = await self._comercial_kpis()

        if self._can(permissions, "cadastros.motorista.visualizar", is_superuser):
            snap.alertas.extend(await self._alertas_motoristas())

        if self._can(permissions, "fiscal.nfe.visualizar", is_superuser):
            snap.alertas.extend(await self._alertas_fiscal())

        return snap

    def _can(self, permissions: set[str], code: str, is_superuser: bool) -> bool:
        return has_permission(permissions, code, is_superuser=is_superuser)

    async def _frota_kpis(self, filial_id: uuid.UUID | None) -> FrotaKpis:
        base = select(func.count()).select_from(FrotaVeiculo).where(
            FrotaVeiculo.deleted_at.is_(None),
            FrotaVeiculo.status != VeiculoStatus.BAIXADO,
        )
        if filial_id:
            base = base.where(FrotaVeiculo.filial_id == filial_id)

        total = await self._count(base)
        disponiveis = await self._count(
            base.where(FrotaVeiculo.status == VeiculoStatus.DISPONIVEL)
        )
        locados = await self._count(base.where(FrotaVeiculo.status == VeiculoStatus.LOCADO))
        manutencao = await self._count(
            base.where(FrotaVeiculo.status == VeiculoStatus.MANUTENCAO)
        )
        bloqueados = await self._count(
            base.where(
                FrotaVeiculo.status.in_(
                    (VeiculoStatus.BLOQUEADO, VeiculoStatus.RESTRITO)
                )
            )
        )
        operacional = max(total - disponiveis, 1)
        ocupacao = round((locados / operacional) * 100, 1) if total else 0.0
        return FrotaKpis(
            total=total,
            disponiveis=disponiveis,
            locados=locados,
            manutencao=manutencao,
            bloqueados=bloqueados,
            ocupacao_pct=ocupacao,
        )

    async def _reservas_kpis(self, filial_id: uuid.UUID | None) -> ReservasKpis:
        now = datetime.now(UTC)
        hoje_ini = now.replace(hour=0, minute=0, second=0, microsecond=0)
        hoje_fim = hoje_ini + timedelta(days=1)
        prox_48h = now + timedelta(hours=48)

        base = select(func.count()).select_from(ResReserva).where(
            ResReserva.deleted_at.is_(None),
            ResReserva.status.not_in((ReservaStatus.CANCELADA, ReservaStatus.NO_SHOW)),
        )
        if filial_id:
            base = base.where(ResReserva.filial_retirada_id == filial_id)

        hoje = await self._count(
            base.where(
                ResReserva.retirada_em >= hoje_ini,
                ResReserva.retirada_em < hoje_fim,
            )
        )
        proximas = await self._count(
            base.where(
                ResReserva.retirada_em >= now,
                ResReserva.retirada_em <= prox_48h,
            )
        )
        pendentes = await self._count(base.where(ResReserva.status == ReservaStatus.PENDENTE))
        return ReservasKpis(hoje=hoje, proximas_48h=proximas, pendentes=pendentes)

    async def _locacoes_kpis(self, filial_id: uuid.UUID | None) -> LocacoesKpis:
        now = datetime.now(UTC)
        lim_24h = now + timedelta(hours=24)
        lim_48h = now + timedelta(hours=48)

        base = select(func.count()).select_from(LocContrato).where(
            LocContrato.deleted_at.is_(None),
            LocContrato.status == ContratoStatus.ATIVO,
        )
        if filial_id:
            base = base.where(LocContrato.filial_retirada_id == filial_id)

        ativos = await self._count(base)
        v24 = await self._count(
            base.where(
                LocContrato.devolucao_prevista_em >= now,
                LocContrato.devolucao_prevista_em <= lim_24h,
            )
        )
        v48 = await self._count(
            base.where(
                LocContrato.devolucao_prevista_em > lim_24h,
                LocContrato.devolucao_prevista_em <= lim_48h,
            )
        )
        return LocacoesKpis(ativos=ativos, vencendo_24h=v24, vencendo_48h=v48)

    async def _financeiro_kpis(self, filial_id: uuid.UUID | None) -> FinanceiroKpis:
        hoje = date.today()
        mes_ini = hoje.replace(day=1)

        lanc_base = (
            select(func.coalesce(func.sum(FinCaixaLancamento.valor), 0))
            .select_from(FinCaixaLancamento)
            .join(FinCaixaSessao, FinCaixaLancamento.sessao_id == FinCaixaSessao.id)
            .where(
                FinCaixaLancamento.deleted_at.is_(None),
                FinCaixaSessao.deleted_at.is_(None),
                FinCaixaLancamento.tipo == CaixaLancamentoTipo.ENTRADA,
            )
        )
        if filial_id:
            lanc_base = lanc_base.where(FinCaixaSessao.filial_id == filial_id)

        faturamento_dia = await self._sum_decimal(
            lanc_base.where(func.date(FinCaixaLancamento.created_at) == hoje)
        )
        faturamento_mes = await self._sum_decimal(
            lanc_base.where(func.date(FinCaixaLancamento.created_at) >= mes_ini)
        )

        cr_base = select(func.coalesce(func.sum(FinContaReceber.valor_saldo), 0)).where(
            FinContaReceber.deleted_at.is_(None),
            FinContaReceber.status.in_(
                (TituloStatus.EM_ABERTO, TituloStatus.VENCIDO, TituloStatus.PAGO_PARCIAL)
            ),
        )
        cp_base = select(func.coalesce(func.sum(FinContaPagar.valor_saldo), 0)).where(
            FinContaPagar.deleted_at.is_(None),
            FinContaPagar.status.in_(
                (TituloStatus.EM_ABERTO, TituloStatus.VENCIDO, TituloStatus.PAGO_PARCIAL)
            ),
        )
        if filial_id:
            cr_base = cr_base.where(FinContaReceber.filial_id == filial_id)
            cp_base = cp_base.where(FinContaPagar.filial_id == filial_id)

        receber_aberto = await self._sum_decimal(
            cr_base.where(FinContaReceber.status != TituloStatus.VENCIDO)
        )
        receber_vencido = await self._sum_decimal(
            cr_base.where(FinContaReceber.status == TituloStatus.VENCIDO)
        )
        pagar_aberto = await self._sum_decimal(
            cp_base.where(FinContaPagar.status != TituloStatus.VENCIDO)
        )
        pagar_vencido = await self._sum_decimal(
            cp_base.where(FinContaPagar.status == TituloStatus.VENCIDO)
        )
        saldo_caixa = await self._saldo_caixa_aberto(filial_id)

        return FinanceiroKpis(
            faturamento_dia=faturamento_dia,
            faturamento_mes=faturamento_mes,
            receber_aberto=receber_aberto,
            receber_vencido=receber_vencido,
            pagar_aberto=pagar_aberto,
            pagar_vencido=pagar_vencido,
            saldo_caixa=saldo_caixa,
        )

    async def _manutencao_kpis(self, filial_id: uuid.UUID | None) -> ManutencaoKpis:
        base = select(func.count()).select_from(ManOrdemServico).where(
            ManOrdemServico.deleted_at.is_(None),
            ManOrdemServico.status.not_in(
                (OrdemServicoStatus.CONCLUIDA, OrdemServicoStatus.CANCELADA)
            ),
        )
        if filial_id:
            base = base.where(ManOrdemServico.filial_id == filial_id)

        abertas = await self._count(base)
        aprovacao = await self._count(
            base.where(ManOrdemServico.status == OrdemServicoStatus.AGUARDANDO_APROVACAO)
        )
        preventiva = await self._count_preventivas_pendentes(filial_id)
        pneus = await self._count_pneus_alerta(filial_id)
        return ManutencaoKpis(
            os_abertas=abertas,
            aguardando_aprovacao=aprovacao,
            preventiva_pendente=preventiva,
            pneus_alerta=pneus,
        )

    async def _comercial_kpis(self) -> ComercialKpis:
        mes_ini = date.today().replace(day=1)
        oportunidades = await self._count(
            select(func.count())
            .select_from(CrmOportunidade)
            .where(
                CrmOportunidade.deleted_at.is_(None),
                CrmOportunidade.estagio.not_in(
                    (CrmEstagio.FECHADO_GANHO, CrmEstagio.PERDIDO)
                ),
            )
        )
        propostas_abertas = await self._count(
            select(func.count())
            .select_from(CrmProposta)
            .where(
                CrmProposta.deleted_at.is_(None),
                CrmProposta.status.in_(
                    (
                        CrmPropostaStatus.RASCUNHO,
                        CrmPropostaStatus.ENVIADA,
                        CrmPropostaStatus.VISUALIZADA,
                    )
                ),
            )
        )
        aceitas_mes = await self._count(
            select(func.count())
            .select_from(CrmProposta)
            .where(
                CrmProposta.deleted_at.is_(None),
                CrmProposta.status == CrmPropostaStatus.ACEITA,
                func.date(CrmProposta.updated_at) >= mes_ini,
            )
        )
        recusadas_mes = await self._count(
            select(func.count())
            .select_from(CrmProposta)
            .where(
                CrmProposta.deleted_at.is_(None),
                CrmProposta.status == CrmPropostaStatus.RECUSADA,
                func.date(CrmProposta.updated_at) >= mes_ini,
            )
        )
        funil_rows = (
            await self.session.execute(
                select(CrmOportunidade.estagio, func.count())
                .select_from(CrmOportunidade)
                .where(
                    CrmOportunidade.deleted_at.is_(None),
                    CrmOportunidade.estagio.not_in(
                        (CrmEstagio.FECHADO_GANHO, CrmEstagio.PERDIDO)
                    ),
                )
                .group_by(CrmOportunidade.estagio)
            )
        ).all()
        funil = {row[0].value: int(row[1]) for row in funil_rows}
        finalizadas = aceitas_mes + recusadas_mes
        taxa = round((aceitas_mes / finalizadas) * 100, 1) if finalizadas else 0.0
        return ComercialKpis(
            oportunidades_abertas=oportunidades,
            propostas_abertas=propostas_abertas,
            propostas_aceitas_mes=aceitas_mes,
            taxa_conversao_pct=taxa,
            funil_por_estagio=funil,
        )

    async def _alertas_frota(self, filial_id: uuid.UUID | None) -> list[AlertaItem]:
        limite = date.today() + timedelta(days=30)
        stmt = (
            select(func.count())
            .select_from(FrotaDocumento)
            .join(FrotaVeiculo, FrotaDocumento.veiculo_id == FrotaVeiculo.id)
            .where(
                FrotaDocumento.deleted_at.is_(None),
                FrotaVeiculo.deleted_at.is_(None),
                FrotaDocumento.data_validade.is_not(None),
                FrotaDocumento.data_validade <= limite,
                FrotaDocumento.data_validade >= date.today(),
            )
        )
        if filial_id:
            stmt = stmt.where(FrotaVeiculo.filial_id == filial_id)
        qtd = await self._count(stmt)
        if qtd:
            return [
                AlertaItem(
                    tipo="documentacao",
                    mensagem=f"{qtd} documento(s) de veículo vencendo em até 30 dias",
                    url="/frota/documentacao",
                )
            ]
        return []

    async def _alertas_motoristas(self) -> list[AlertaItem]:
        limite = date.today() + timedelta(days=30)
        qtd = await self._count(
            select(func.count())
            .select_from(Motorista)
            .where(
                Motorista.deleted_at.is_(None),
                Motorista.cnh_validade.is_not(None),
                Motorista.cnh_validade <= limite,
                Motorista.cnh_validade >= date.today(),
            )
        )
        if qtd:
            return [
                AlertaItem(
                    tipo="cnh",
                    mensagem=f"{qtd} motorista(s) com CNH vencendo em até 30 dias",
                    url="/cadastros/motoristas",
                )
            ]
        return []

    async def _alertas_locacoes(self, filial_id: uuid.UUID | None) -> list[AlertaItem]:
        base = select(func.count()).select_from(LocMulta).where(
            LocMulta.deleted_at.is_(None),
            LocMulta.contrato_id.is_(None),
        )
        qtd = await self._count(base)
        if qtd:
            return [
                AlertaItem(
                    tipo="multa",
                    mensagem=f"{qtd} multa(s) sem vínculo com contrato",
                    url="/locacoes/multas",
                )
            ]
        return []

    async def _alertas_fiscal(self) -> list[AlertaItem]:
        nfe = await self._count(
            select(func.count())
            .select_from(FisNfe)
            .where(FisNfe.deleted_at.is_(None), FisNfe.status == NfeStatus.REJEITADA)
        )
        nfse = await self._count(
            select(func.count())
            .select_from(FisNfse)
            .where(FisNfse.deleted_at.is_(None), FisNfse.status == NfseStatus.REJEITADA)
        )
        alertas: list[AlertaItem] = []
        if nfe:
            alertas.append(
                AlertaItem(
                    tipo="nfe",
                    mensagem=f"{nfe} NF-e rejeitada(s) pela SEFAZ",
                    url="/fiscal/nfe",
                )
            )
        if nfse:
            alertas.append(
                AlertaItem(
                    tipo="nfse",
                    mensagem=f"{nfse} NFS-e rejeitada(s)",
                    url="/fiscal/nfse",
                )
            )
        return alertas

    async def _saldo_caixa_aberto(self, filial_id: uuid.UUID | None) -> Decimal:
        credit_types = (CaixaLancamentoTipo.ENTRADA, CaixaLancamentoTipo.SUPRIMENTO)
        mov_expr = func.coalesce(
            func.sum(
                case(
                    (FinCaixaLancamento.tipo.in_(credit_types), FinCaixaLancamento.valor),
                    else_=-FinCaixaLancamento.valor,
                )
            ),
            0,
        )
        stmt = (
            select(FinCaixaSessao.valor_abertura, mov_expr.label("movimentos"))
            .outerjoin(
                FinCaixaLancamento,
                and_(
                    FinCaixaLancamento.sessao_id == FinCaixaSessao.id,
                    FinCaixaLancamento.deleted_at.is_(None),
                ),
            )
            .where(
                FinCaixaSessao.deleted_at.is_(None),
                FinCaixaSessao.status == CaixaSessaoStatus.ABERTA,
            )
            .group_by(FinCaixaSessao.id, FinCaixaSessao.valor_abertura)
        )
        if filial_id:
            stmt = stmt.where(FinCaixaSessao.filial_id == filial_id)
        rows = (await self.session.execute(stmt)).all()
        total = Decimal("0")
        for abertura, movimentos in rows:
            total += Decimal(str(abertura or 0)) + Decimal(str(movimentos or 0))
        return total

    async def _count_preventivas_pendentes(self, filial_id: uuid.UUID | None) -> int:
        stmt = (
            select(ManVeiculoPlano, ManPlanoPreventivo, FrotaVeiculo)
            .join(
                ManPlanoPreventivo,
                and_(
                    ManPlanoPreventivo.id == ManVeiculoPlano.plano_id,
                    ManPlanoPreventivo.deleted_at.is_(None),
                    ManPlanoPreventivo.status == CadastroStatus.ACTIVE,
                ),
            )
            .join(
                FrotaVeiculo,
                and_(
                    FrotaVeiculo.id == ManVeiculoPlano.veiculo_id,
                    FrotaVeiculo.deleted_at.is_(None),
                ),
            )
            .where(ManVeiculoPlano.deleted_at.is_(None))
        )
        if filial_id:
            stmt = stmt.where(FrotaVeiculo.filial_id == filial_id)
        rows = (await self.session.execute(stmt)).all()
        count = 0
        for vp, plano, veiculo in rows:
            _, _, urgencia = _calc_preventiva_urgencia(
                km_atual=veiculo.km_atual,
                km_ultima=vp.km_ultima_execucao,
                data_ultima=vp.data_ultima_execucao,
                intervalo_km=plano.intervalo_km,
                intervalo_meses=plano.intervalo_meses,
            )
            if urgencia >= 0.8:
                count += 1
        return count

    async def _count_pneus_alerta(self, filial_id: uuid.UUID | None) -> int:
        stmt = (
            select(func.count())
            .select_from(ManPneu)
            .outerjoin(FrotaVeiculo, ManPneu.veiculo_id == FrotaVeiculo.id)
            .where(
                ManPneu.deleted_at.is_(None),
                ManPneu.sulco_mm.is_not(None),
                ManPneu.sulco_mm < 2,
                ManPneu.status != PneuStatus.DESCARTADO,
            )
        )
        if filial_id:
            stmt = stmt.where(FrotaVeiculo.filial_id == filial_id)
        return await self._count(stmt)

    async def _ocupacao_serie(
        self,
        filial_id: uuid.UUID | None,
        *,
        days: int,
        step: int,
    ) -> list[OcupacaoPonto]:
        frota = await self._frota_kpis(filial_id)
        if frota.total <= 0:
            return []
        hoje = date.today()
        pontos: list[OcupacaoPonto] = []
        for offset in range(days - 1, -1, -step):
            ref = hoje - timedelta(days=offset)
            day_start = datetime.combine(ref, time.min, tzinfo=UTC)
            day_end = datetime.combine(ref, time.max, tzinfo=UTC)
            locados = await self._count_locados_no_dia(filial_id, day_start, day_end)
            pct = round((locados / frota.total) * 100, 1)
            label = ref.strftime("%d/%m") if step > 1 else ref.strftime("%d/%m")
            pontos.append(OcupacaoPonto(label=label, pct=pct))
        return pontos

    async def _count_locados_no_dia(
        self,
        filial_id: uuid.UUID | None,
        day_start: datetime,
        day_end: datetime,
    ) -> int:
        inicio = func.coalesce(LocContrato.checkout_em, LocContrato.retirada_prevista_em)
        fim = func.coalesce(LocContrato.checkin_em, LocContrato.devolucao_prevista_em)
        stmt = (
            select(func.count(func.distinct(LocContrato.veiculo_id)))
            .select_from(LocContrato)
            .where(
            LocContrato.deleted_at.is_(None),
            LocContrato.status.not_in(
                (
                    ContratoStatus.RASCUNHO,
                    ContratoStatus.CANCELADO,
                    ContratoStatus.AGUARDANDO_CHECKOUT,
                )
            ),
            inicio <= day_end,
                fim >= day_start,
            )
        )
        if filial_id:
            stmt = stmt.where(LocContrato.filial_retirada_id == filial_id)
        return await self._count(stmt)

    async def _alertas_contratos_atrasados(
        self, filial_id: uuid.UUID | None
    ) -> list[AlertaItem]:
        now = datetime.now(UTC)
        stmt = select(func.count()).select_from(LocContrato).where(
            LocContrato.deleted_at.is_(None),
            LocContrato.status == ContratoStatus.ATIVO,
            LocContrato.devolucao_prevista_em < now,
            LocContrato.checkin_em.is_(None),
        )
        if filial_id:
            stmt = stmt.where(LocContrato.filial_retirada_id == filial_id)
        qtd = await self._count(stmt)
        if qtd:
            return [
                AlertaItem(
                    tipo="checkin",
                    mensagem=f"{qtd} contrato(s) ativo(s) com devolução vencida sem check-in",
                    url="/locacoes/contratos",
                )
            ]
        return []

    async def get_overview(
        self,
        *,
        permissions: set[str] | None = None,
        is_superuser: bool = False,
        filial_id: uuid.UUID | None = None,
    ) -> DashboardSnapshot:
        """Compatibilidade: retorna snapshot com permissões informadas."""
        return await self.get_snapshot(
            permissions=permissions or set(),
            is_superuser=is_superuser,
            filial_id=filial_id,
        )
