"""Serviços de negócio do módulo Manutenção."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.pagination import Page, PageParams
from app.modules.audit.service import audit_service
from app.modules.frota.service import VeiculoService
from app.modules.manutencao.models import (
    ManEstoqueMovimento,
    ManEstoquePeca,
    ManOrdemServico,
    ManOsFoto,
    ManOsItem,
    ManPeca,
    ManPlanoChecklist,
    ManPlanoPreventivo,
    ManPneu,
    ManPneuHistorico,
    ManVeiculoPlano,
)
from app.modules.manutencao.schemas import (
    EstoqueAjuste,
    EstoqueAlertaItem,
    EstoqueEntrada,
    EstoqueEnsure,
    EstoqueSaida,
    EstoqueTransferencia,
    OrdemServicoAprovar,
    OrdemServicoCancelar,
    OrdemServicoConcluir,
    OrdemServicoCreate,
    OrdemServicoFotoCreate,
    OrdemServicoItemCreate,
    OrdemServicoStatusChange,
    OrdemServicoUpdate,
    PecaCreate,
    PecaUpdate,
    PlanoPreventivoCreate,
    PlanoPreventivoUpdate,
    PneuAlertaItem,
    PneuCreate,
    PneuDescartar,
    PneuInstalar,
    PneuInspecionar,
    PneuRodizio,
    PneuUpdate,
    PreventivaUrgenciaItem,
    VeiculoPlanoLink,
)
from app.shared.enums import (
    AuditAction,
    CadastroStatus,
    EstoqueMovimentoTipo,
    OrdemServicoItemTipo,
    OrdemServicoOrigem,
    OrdemServicoStatus,
    OrdemServicoTipo,
    PneuStatus,
    VeiculoStatus,
)
from app.shared.repository import BaseRepository

LIMITE_APROVACAO_OS = Decimal("5000")

_CORRETIVA_TIPOS = {OrdemServicoTipo.CORRETIVA, OrdemServicoTipo.SINISTRO}

OS_TRANSITIONS: dict[OrdemServicoStatus, set[OrdemServicoStatus]] = {
    OrdemServicoStatus.ABERTA: {
        OrdemServicoStatus.AGUARDANDO_PECA,
        OrdemServicoStatus.EM_EXECUCAO,
        OrdemServicoStatus.AGUARDANDO_APROVACAO,
        OrdemServicoStatus.CANCELADA,
        OrdemServicoStatus.CONCLUIDA,
    },
    OrdemServicoStatus.AGUARDANDO_PECA: {
        OrdemServicoStatus.EM_EXECUCAO,
        OrdemServicoStatus.CANCELADA,
    },
    OrdemServicoStatus.EM_EXECUCAO: {
        OrdemServicoStatus.AGUARDANDO_APROVACAO,
        OrdemServicoStatus.CONCLUIDA,
        OrdemServicoStatus.AGUARDANDO_PECA,
        OrdemServicoStatus.CANCELADA,
    },
    OrdemServicoStatus.AGUARDANDO_APROVACAO: {
        OrdemServicoStatus.EM_EXECUCAO,
        OrdemServicoStatus.CONCLUIDA,
        OrdemServicoStatus.CANCELADA,
    },
    OrdemServicoStatus.CONCLUIDA: set(),
    OrdemServicoStatus.CANCELADA: set(),
}

_RESTORE_STATUSES = {
    VeiculoStatus.DISPONIVEL,
    VeiculoStatus.RESERVADO,
    VeiculoStatus.RESTRITO,
}


# ---------------------------------------------------------------- Repositories
class OrdemServicoRepository(BaseRepository[ManOrdemServico]):
    model = ManOrdemServico

    async def count_by_tenant(self, tenant_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(ManOrdemServico)
            .where(
                ManOrdemServico.tenant_id == tenant_id,
                ManOrdemServico.deleted_at.is_(None),
            )
        )
        return (await self.session.execute(stmt)).scalar_one()

    def list_query(
        self,
        *,
        status: OrdemServicoStatus | None = None,
        tipo: OrdemServicoTipo | None = None,
        veiculo_id: uuid.UUID | None = None,
        search: str | None = None,
        tipos: set[OrdemServicoTipo] | None = None,
    ) -> Select[tuple[ManOrdemServico]]:
        stmt = self._base_query().order_by(ManOrdemServico.data_abertura.desc())
        if status:
            stmt = stmt.where(ManOrdemServico.status == status)
        if tipo:
            stmt = stmt.where(ManOrdemServico.tipo == tipo)
        if tipos:
            stmt = stmt.where(ManOrdemServico.tipo.in_(tipos))
        if veiculo_id:
            stmt = stmt.where(ManOrdemServico.veiculo_id == veiculo_id)
        if search:
            term = f"%{search.strip().lower()}%"
            stmt = stmt.where(func.lower(ManOrdemServico.numero).like(term))
        return stmt


class OsItemRepository(BaseRepository[ManOsItem]):
    model = ManOsItem

    def list_by_os(self, os_id: uuid.UUID) -> Select[tuple[ManOsItem]]:
        return (
            self._base_query()
            .where(ManOsItem.os_id == os_id)
            .order_by(ManOsItem.created_at.asc())
        )

    async def sum_by_os(self, os_id: uuid.UUID) -> tuple[Decimal, Decimal]:
        stmt = select(
            ManOsItem.tipo_item,
            func.coalesce(func.sum(ManOsItem.valor_total), 0),
        ).where(ManOsItem.os_id == os_id, ManOsItem.deleted_at.is_(None)).group_by(
            ManOsItem.tipo_item
        )
        rows = (await self.session.execute(stmt)).all()
        mao_obra = Decimal("0")
        pecas = Decimal("0")
        for tipo, total in rows:
            if tipo == OrdemServicoItemTipo.MAO_DE_OBRA:
                mao_obra = Decimal(str(total))
            elif tipo == OrdemServicoItemTipo.PECA:
                pecas = Decimal(str(total))
        return mao_obra, pecas


class OsFotoRepository(BaseRepository[ManOsFoto]):
    model = ManOsFoto

    def list_by_os(self, os_id: uuid.UUID) -> Select[tuple[ManOsFoto]]:
        return (
            self._base_query()
            .where(ManOsFoto.os_id == os_id)
            .order_by(ManOsFoto.ordem.asc(), ManOsFoto.created_at.asc())
        )


class PlanoPreventivoRepository(BaseRepository[ManPlanoPreventivo]):
    model = ManPlanoPreventivo

    def list_query(self, *, search: str | None = None) -> Select[tuple[ManPlanoPreventivo]]:
        stmt = self._base_query().order_by(ManPlanoPreventivo.nome.asc())
        if search:
            term = f"%{search.strip().lower()}%"
            stmt = stmt.where(func.lower(ManPlanoPreventivo.nome).like(term))
        return stmt


class PlanoChecklistRepository(BaseRepository[ManPlanoChecklist]):
    model = ManPlanoChecklist

    async def delete_by_plano(self, plano_id: uuid.UUID) -> None:
        stmt = select(ManPlanoChecklist).where(
            ManPlanoChecklist.plano_id == plano_id,
            ManPlanoChecklist.deleted_at.is_(None),
        )
        items = list((await self.session.execute(stmt)).scalars().all())
        for item in items:
            await self.delete(item)


class VeiculoPlanoRepository(BaseRepository[ManVeiculoPlano]):
    model = ManVeiculoPlano

    async def get_vinculo(
        self, veiculo_id: uuid.UUID, plano_id: uuid.UUID
    ) -> ManVeiculoPlano | None:
        stmt = (
            self._base_query()
            .where(
                ManVeiculoPlano.veiculo_id == veiculo_id,
                ManVeiculoPlano.plano_id == plano_id,
            )
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    def list_by_veiculo(self, veiculo_id: uuid.UUID) -> Select[tuple[ManVeiculoPlano]]:
        return (
            self._base_query()
            .where(ManVeiculoPlano.veiculo_id == veiculo_id)
            .order_by(ManVeiculoPlano.created_at.asc())
        )

    def list_by_plano(self, plano_id: uuid.UUID) -> Select[tuple[ManVeiculoPlano]]:
        return (
            self._base_query()
            .where(ManVeiculoPlano.plano_id == plano_id)
            .order_by(ManVeiculoPlano.created_at.asc())
        )

    def list_all_active(self) -> Select[tuple[ManVeiculoPlano]]:
        return self._base_query().order_by(ManVeiculoPlano.created_at.asc())


class PecaRepository(BaseRepository[ManPeca]):
    model = ManPeca

    async def get_by_codigo(self, codigo: str) -> ManPeca | None:
        stmt = self._base_query().where(ManPeca.codigo == codigo).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    def search_query(self, *, search: str | None = None) -> Select[tuple[ManPeca]]:
        stmt = self._base_query().order_by(ManPeca.nome.asc())
        if search:
            term = f"%{search.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(ManPeca.nome).like(term),
                    func.lower(ManPeca.codigo).like(term),
                )
            )
        return stmt


class EstoquePecaRepository(BaseRepository[ManEstoquePeca]):
    model = ManEstoquePeca

    async def get_by_peca_filial(
        self, peca_id: uuid.UUID, filial_id: uuid.UUID
    ) -> ManEstoquePeca | None:
        stmt = (
            self._base_query()
            .where(
                ManEstoquePeca.peca_id == peca_id,
                ManEstoquePeca.filial_id == filial_id,
            )
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    def list_query(
        self,
        *,
        filial_id: uuid.UUID | None = None,
        search: str | None = None,
    ) -> Select[tuple[ManEstoquePeca]]:
        stmt = self._base_query().order_by(ManEstoquePeca.created_at.desc())
        if filial_id:
            stmt = stmt.where(ManEstoquePeca.filial_id == filial_id)
        if search:
            term = f"%{search.strip().lower()}%"
            stmt = stmt.join(ManPeca, ManPeca.id == ManEstoquePeca.peca_id).where(
                or_(
                    func.lower(ManPeca.nome).like(term),
                    func.lower(ManPeca.codigo).like(term),
                ),
                ManPeca.deleted_at.is_(None),
            )
        return stmt

    def alertas_query(self) -> Select[tuple[ManEstoquePeca]]:
        return (
            self._base_query()
            .where(ManEstoquePeca.quantidade_atual < ManEstoquePeca.quantidade_minima)
            .order_by(ManEstoquePeca.quantidade_atual.asc())
        )


class EstoqueMovimentoRepository(BaseRepository[ManEstoqueMovimento]):
    model = ManEstoqueMovimento

    def list_by_peca(self, peca_id: uuid.UUID) -> Select[tuple[ManEstoqueMovimento]]:
        return (
            self._base_query()
            .where(ManEstoqueMovimento.peca_id == peca_id)
            .order_by(ManEstoqueMovimento.ocorrido_em.desc())
        )


class PneuRepository(BaseRepository[ManPneu]):
    model = ManPneu

    async def get_by_numero_fogo(self, numero_fogo: str) -> ManPneu | None:
        stmt = self._base_query().where(ManPneu.numero_fogo == numero_fogo).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    def list_query(
        self,
        *,
        status: PneuStatus | None = None,
        veiculo_id: uuid.UUID | None = None,
        search: str | None = None,
    ) -> Select[tuple[ManPneu]]:
        stmt = self._base_query().order_by(ManPneu.numero_fogo.asc())
        if status:
            stmt = stmt.where(ManPneu.status == status)
        if veiculo_id:
            stmt = stmt.where(ManPneu.veiculo_id == veiculo_id)
        if search:
            term = f"%{search.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(ManPneu.numero_fogo).like(term),
                    func.lower(ManPneu.marca).like(term),
                )
            )
        return stmt


class PneuHistoricoRepository(BaseRepository[ManPneuHistorico]):
    model = ManPneuHistorico

    def list_by_pneu(self, pneu_id: uuid.UUID) -> Select[tuple[ManPneuHistorico]]:
        return (
            self._base_query()
            .where(ManPneuHistorico.pneu_id == pneu_id)
            .order_by(ManPneuHistorico.ocorrido_em.desc())
        )


# --------------------------------------------------------------------- Helpers
def _resolve_restore_status(anterior: str | None) -> VeiculoStatus:
    if anterior is None:
        return VeiculoStatus.DISPONIVEL
    try:
        prev = VeiculoStatus(anterior)
    except ValueError:
        return VeiculoStatus.DISPONIVEL
    if prev == VeiculoStatus.MANUTENCAO:
        return VeiculoStatus.DISPONIVEL
    if prev in _RESTORE_STATUSES:
        return prev
    return VeiculoStatus.DISPONIVEL


def _calc_preventiva_urgencia(
    *,
    km_atual: int | None,
    km_ultima: int | None,
    data_ultima: date | None,
    intervalo_km: int | None,
    intervalo_meses: int | None,
) -> tuple[int | None, int | None, float]:
    km_pct = 0.0
    time_pct = 0.0
    km_restante: int | None = None
    dias_restantes: int | None = None

    if intervalo_km and intervalo_km > 0:
        km_base = km_ultima or 0
        km_corrido = max(0, (km_atual or 0) - km_base)
        km_restante = max(0, intervalo_km - km_corrido)
        km_pct = min(1.0, km_corrido / intervalo_km)

    if intervalo_meses and intervalo_meses > 0:
        base_date = data_ultima or date.today()
        dias_intervalo = intervalo_meses * 30
        dias_corrido = max(0, (date.today() - base_date).days)
        dias_restantes = max(0, dias_intervalo - dias_corrido)
        time_pct = min(1.0, dias_corrido / dias_intervalo)

    urgencia = max(km_pct, time_pct)
    return km_restante, dias_restantes, urgencia


# --------------------------------------------------------------------- Services
class OrdemServicoService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = OrdemServicoRepository(session)
        self.item_repo = OsItemRepository(session)
        self.foto_repo = OsFotoRepository(session)
        self.veiculo_svc = VeiculoService(session)
        self._estoque_svc: EstoqueService | None = None

    def _estoque(self) -> EstoqueService:
        if self._estoque_svc is None:
            self._estoque_svc = EstoqueService(self.session)
        return self._estoque_svc

    async def next_numero(self, tenant_id: uuid.UUID) -> str:
        count = await self.repo.count_by_tenant(tenant_id)
        return f"OS-{count + 1:06d}"

    async def list_items(
        self,
        params: PageParams,
        *,
        status: OrdemServicoStatus | None = None,
        tipo: OrdemServicoTipo | None = None,
        veiculo_id: uuid.UUID | None = None,
        search: str | None = None,
    ) -> Page[ManOrdemServico]:
        stmt = self.repo.list_query(
            status=status, tipo=tipo, veiculo_id=veiculo_id, search=search
        )
        return await self.repo.paginate(params, stmt=stmt)

    async def list_corretivas(
        self,
        params: PageParams,
        *,
        status: OrdemServicoStatus | None = None,
        veiculo_id: uuid.UUID | None = None,
        search: str | None = None,
    ) -> Page[ManOrdemServico]:
        stmt = self.repo.list_query(
            status=status,
            veiculo_id=veiculo_id,
            search=search,
            tipos=_CORRETIVA_TIPOS,
        )
        return await self.repo.paginate(params, stmt=stmt)

    async def get(self, os_id: uuid.UUID) -> ManOrdemServico:
        item = await self.repo.get(os_id)
        if item is None:
            raise NotFoundError("Ordem de serviço não encontrada.")
        return item

    async def _iniciar_workflow_aprovacao(self, item: ManOrdemServico) -> None:
        from app.modules.automacoes.hooks import try_start_workflow

        await try_start_workflow(
            self.session,
            item.tenant_id,
            workflow_codigo="os_valor_alto",
            entidade_tipo="ordem_servico",
            entidade_id=item.id,
            contexto={
                "numero": item.numero,
                "custo_total": str(item.custo_total),
                "veiculo_id": str(item.veiculo_id),
            },
        )

    async def create(self, tenant_id: uuid.UUID, data: OrdemServicoCreate) -> ManOrdemServico:
        veiculo = await self.veiculo_svc.get(data.veiculo_id)
        numero = await self.next_numero(tenant_id)
        payload = data.model_dump(exclude={"limite_aprovacao"})
        payload["numero"] = numero
        payload["status"] = OrdemServicoStatus.ABERTA
        payload["data_abertura"] = date.today()
        payload["status_veiculo_anterior"] = veiculo.status.value

        item = ManOrdemServico(tenant_id=tenant_id, **payload)
        self.repo.add(item)
        await self.repo.flush()

        if veiculo.status not in {VeiculoStatus.MANUTENCAO, VeiculoStatus.BAIXADO}:
            await self.veiculo_svc.change_status(
                data.veiculo_id, VeiculoStatus.MANUTENCAO
            )

        await audit_service.record(
            AuditAction.CREATE,
            entity="man_ordem_servico",
            entity_id=item.id,
            description=f"OS criada: {item.numero} ({item.tipo.value})",
        )
        return item

    async def update(self, os_id: uuid.UUID, data: OrdemServicoUpdate) -> ManOrdemServico:
        item = await self.get(os_id)
        if item.status in {OrdemServicoStatus.CONCLUIDA, OrdemServicoStatus.CANCELADA}:
            raise ConflictError(
                "OS concluída ou cancelada não pode ser alterada.",
                code="os_terminal",
            )
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(item, k, v)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="man_ordem_servico",
            entity_id=item.id,
            description=f"OS atualizada: {item.numero}",
        )
        return item

    async def change_status(
        self,
        os_id: uuid.UUID,
        data: OrdemServicoStatusChange,
        *,
        limite_aprovacao: Decimal | None = None,
    ) -> ManOrdemServico:
        item = await self.get(os_id)
        current = item.status
        new_status = data.status

        if current in {OrdemServicoStatus.CONCLUIDA, OrdemServicoStatus.CANCELADA}:
            if not data.force:
                raise ConflictError(
                    f"OS em status terminal ({current.value}).",
                    code="os_terminal",
                )

        if new_status == OrdemServicoStatus.EM_EXECUCAO:
            limite = limite_aprovacao or LIMITE_APROVACAO_OS
            if item.custo_total > limite and item.aprovado_em is None:
                item.requer_aprovacao = True
                new_status = OrdemServicoStatus.AGUARDANDO_APROVACAO
                await self._iniciar_workflow_aprovacao(item)

        allowed = OS_TRANSITIONS.get(current, set())
        if new_status not in allowed and not (
            current in {OrdemServicoStatus.CONCLUIDA, OrdemServicoStatus.CANCELADA}
            and data.force
        ):
            raise ValidationError(
                f"Transição inválida: {current.value} → {new_status.value}."
            )

        if new_status == OrdemServicoStatus.CONCLUIDA:
            return await self.concluir(
                os_id, OrdemServicoConcluir(force=data.force), limite_aprovacao=limite_aprovacao
            )
        if new_status == OrdemServicoStatus.CANCELADA:
            return await self.cancelar(
                os_id, OrdemServicoCancelar(force=data.force)
            )

        item.status = new_status
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="man_ordem_servico",
            entity_id=item.id,
            description=f"OS {item.numero}: {current.value} → {new_status.value}",
        )
        return item

    async def concluir(
        self,
        os_id: uuid.UUID,
        data: OrdemServicoConcluir | None = None,
        *,
        limite_aprovacao: Decimal | None = None,
    ) -> ManOrdemServico:
        data = data or OrdemServicoConcluir()
        item = await self.get(os_id)
        current = item.status

        if current == OrdemServicoStatus.CONCLUIDA:
            return item
        if current == OrdemServicoStatus.CANCELADA and not data.force:
            raise ConflictError("OS cancelada não pode ser concluída.", code="os_cancelada")
        allowed = OS_TRANSITIONS.get(current, set())
        if OrdemServicoStatus.CONCLUIDA not in allowed and not data.force:
            raise ValidationError(f"Não é possível concluir OS em {current.value}.")

        limite = limite_aprovacao or LIMITE_APROVACAO_OS
        if item.custo_total > limite and item.aprovado_em is None and not data.force:
            item.requer_aprovacao = True
            item.status = OrdemServicoStatus.AGUARDANDO_APROVACAO
            await self.repo.flush()
            await self._iniciar_workflow_aprovacao(item)
            raise ConflictError(
                "OS requer aprovação antes da conclusão.",
                code="os_requer_aprovacao",
            )

        if data.km_saida is not None:
            item.km_saida = data.km_saida
        item.status = OrdemServicoStatus.CONCLUIDA
        item.data_conclusao = data.data_conclusao or date.today()
        await self.repo.flush()

        veiculo = await self.veiculo_svc.get(item.veiculo_id)
        if item.km_saida is not None:
            veiculo.km_atual = item.km_saida
            await self.veiculo_svc.repo.flush()

        restore = _resolve_restore_status(item.status_veiculo_anterior)
        if veiculo.status == VeiculoStatus.MANUTENCAO:
            await self.veiculo_svc.change_status(item.veiculo_id, restore)

        filial_id = item.filial_id or veiculo.filial_id
        if filial_id:
            items_stmt = self.item_repo.list_by_os(item.id)
            os_items = list((await self.session.execute(items_stmt)).scalars().all())
            estoque = self._estoque()
            for os_item in os_items:
                if (
                    os_item.tipo_item == OrdemServicoItemTipo.PECA
                    and os_item.peca_id is not None
                ):
                    await estoque.saida(
                        item.tenant_id,
                        os_item.peca_id,
                        EstoqueSaida(
                            filial_id=filial_id,
                            quantidade=os_item.quantidade,
                            custo_unitario=os_item.valor_unitario,
                            os_id=item.id,
                            observacoes=f"Baixa OS {item.numero}",
                        ),
                    )

        if item.fornecedor_id is not None and item.custo_total and item.custo_total > 0:
            await self._gerar_conta_pagar(item, filial_id)

        await audit_service.record(
            AuditAction.UPDATE,
            entity="man_ordem_servico",
            entity_id=item.id,
            description=f"OS concluída: {item.numero}",
        )
        return item

    async def _gerar_conta_pagar(
        self, item: ManOrdemServico, filial_id: uuid.UUID | None
    ) -> None:
        """Gera título a pagar ao fornecedor quando a OS terceirizada é concluída (§9.3)."""
        if filial_id is None:
            return
        from app.modules.financeiro.models import FinContaPagar
        from app.modules.financeiro.service import ContaPagarService
        from app.shared.enums import ContaPagarOrigem

        cp_svc = ContaPagarService(self.session)
        dup_stmt = (
            cp_svc.repo._base_query()
            .where(
                FinContaPagar.origem == ContaPagarOrigem.OS,
                FinContaPagar.origem_id == item.id,
            )
            .limit(1)
        )
        if (await self.session.execute(dup_stmt)).scalar_one_or_none() is not None:
            return
        await cp_svc.from_os(
            item.tenant_id,
            os_id=item.id,
            fornecedor_id=item.fornecedor_id,
            filial_id=filial_id,
            valor=item.custo_total,
            descricao=f"OS {item.numero} (manutenção)",
        )

    async def cancelar(
        self, os_id: uuid.UUID, data: OrdemServicoCancelar | None = None
    ) -> ManOrdemServico:
        data = data or OrdemServicoCancelar()
        item = await self.get(os_id)
        current = item.status

        if current == OrdemServicoStatus.CANCELADA:
            return item
        if current == OrdemServicoStatus.CONCLUIDA and not data.force:
            raise ConflictError("OS concluída não pode ser cancelada.", code="os_concluida")
        if current not in OS_TRANSITIONS.get(current, set()) | {current}:
            if not data.force:
                raise ValidationError(f"Não é possível cancelar OS em {current.value}.")

        item.status = OrdemServicoStatus.CANCELADA
        if data.motivo:
            obs = item.observacoes or ""
            item.observacoes = f"{obs}\n[CANCELADA] {data.motivo}".strip()
        await self.repo.flush()

        veiculo = await self.veiculo_svc.get(item.veiculo_id)
        if veiculo.status == VeiculoStatus.MANUTENCAO:
            restore = _resolve_restore_status(item.status_veiculo_anterior)
            await self.veiculo_svc.change_status(item.veiculo_id, restore)

        await audit_service.record(
            AuditAction.UPDATE,
            entity="man_ordem_servico",
            entity_id=item.id,
            description=f"OS cancelada: {item.numero}",
        )
        return item

    async def aprovar(self, os_id: uuid.UUID, data: OrdemServicoAprovar) -> ManOrdemServico:
        item = await self.get(os_id)
        if item.status == OrdemServicoStatus.CONCLUIDA:
            raise ConflictError("OS já concluída.", code="os_concluida")
        if item.status == OrdemServicoStatus.CANCELADA:
            raise ConflictError("OS cancelada.", code="os_cancelada")

        item.aprovado_em = datetime.now(tz=UTC)
        item.aprovado_por_user_id = data.aprovado_por_user_id
        item.requer_aprovacao = False

        if item.status == OrdemServicoStatus.AGUARDANDO_APROVACAO:
            item.status = OrdemServicoStatus.EM_EXECUCAO

        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="man_ordem_servico",
            entity_id=item.id,
            description=f"OS aprovada: {item.numero}",
        )
        return item

    async def recalc_custos(self, os_id: uuid.UUID) -> ManOrdemServico:
        item = await self.get(os_id)
        mao_obra, pecas = await self.item_repo.sum_by_os(os_id)
        item.custo_mao_obra = mao_obra
        item.custo_pecas = pecas
        item.custo_total = mao_obra + pecas
        await self.repo.flush()
        return item

    async def add_item(
        self, tenant_id: uuid.UUID, os_id: uuid.UUID, data: OrdemServicoItemCreate
    ) -> ManOsItem:
        os_item = await self.get(os_id)
        if os_item.status in {OrdemServicoStatus.CONCLUIDA, OrdemServicoStatus.CANCELADA}:
            raise ConflictError("OS terminal não aceita itens.", code="os_terminal")

        if data.tipo_item == OrdemServicoItemTipo.PECA and data.peca_id is None:
            raise ValidationError("Item de peça requer peca_id.")
        if data.peca_id:
            peca_repo = PecaRepository(self.session)
            if await peca_repo.get(data.peca_id) is None:
                raise ValidationError("Peça inválida.")

        valor_total = (data.quantidade * data.valor_unitario).quantize(Decimal("0.01"))
        item = ManOsItem(
            tenant_id=tenant_id,
            os_id=os_id,
            valor_total=valor_total,
            **data.model_dump(),
        )
        self.item_repo.add(item)
        await self.item_repo.flush()
        await self.recalc_custos(os_id)
        await audit_service.record(
            AuditAction.CREATE,
            entity="man_os_item",
            entity_id=item.id,
            description=f"Item adicionado à OS {os_item.numero}",
        )
        return item

    async def remove_item(self, os_id: uuid.UUID, item_id: uuid.UUID) -> None:
        os_item = await self.get(os_id)
        if os_item.status in {OrdemServicoStatus.CONCLUIDA, OrdemServicoStatus.CANCELADA}:
            raise ConflictError("OS terminal não aceita alteração de itens.", code="os_terminal")
        item = await self.item_repo.get(item_id)
        if item is None or item.os_id != os_id:
            raise NotFoundError("Item da OS não encontrado.")
        await self.item_repo.delete(item)
        await self.recalc_custos(os_id)
        await audit_service.record(
            AuditAction.DELETE,
            entity="man_os_item",
            entity_id=item.id,
            description=f"Item removido da OS {os_item.numero}",
        )

    async def add_foto(
        self, tenant_id: uuid.UUID, os_id: uuid.UUID, data: OrdemServicoFotoCreate
    ) -> ManOsFoto:
        await self.get(os_id)
        foto = ManOsFoto(tenant_id=tenant_id, os_id=os_id, **data.model_dump())
        self.foto_repo.add(foto)
        await self.foto_repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="man_os_foto",
            entity_id=foto.id,
            description=f"Foto adicionada à OS {os_id}",
        )
        return foto

    async def remove_foto(self, os_id: uuid.UUID, foto_id: uuid.UUID) -> None:
        await self.get(os_id)
        foto = await self.foto_repo.get(foto_id)
        if foto is None or foto.os_id != os_id:
            raise NotFoundError("Foto da OS não encontrada.")
        await self.foto_repo.delete(foto)
        await audit_service.record(
            AuditAction.DELETE,
            entity="man_os_foto",
            entity_id=foto.id,
            description=f"Foto removida da OS {os_id}",
        )


class PlanoPreventivoService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PlanoPreventivoRepository(session)
        self.checklist_repo = PlanoChecklistRepository(session)
        self.veiculo_plano_repo = VeiculoPlanoRepository(session)
        self.veiculo_svc = VeiculoService(session)
        self.os_svc = OrdemServicoService(session)

    async def list_items(
        self, params: PageParams, *, search: str | None = None
    ) -> Page[ManPlanoPreventivo]:
        return await self.repo.paginate(params, stmt=self.repo.list_query(search=search))

    async def get(self, plano_id: uuid.UUID) -> ManPlanoPreventivo:
        item = await self.repo.get(plano_id)
        if item is None:
            raise NotFoundError("Plano preventivo não encontrado.")
        return item

    async def create(
        self, tenant_id: uuid.UUID, data: PlanoPreventivoCreate
    ) -> ManPlanoPreventivo:
        payload = data.model_dump(exclude={"checklist"})
        item = ManPlanoPreventivo(tenant_id=tenant_id, **payload)
        self.repo.add(item)
        await self.repo.flush()
        await self._replace_checklist(tenant_id, item.id, data.checklist)
        await audit_service.record(
            AuditAction.CREATE,
            entity="man_plano_preventivo",
            entity_id=item.id,
            description=f"Plano preventivo criado: {item.nome}",
        )
        return item

    async def update(
        self, plano_id: uuid.UUID, data: PlanoPreventivoUpdate
    ) -> ManPlanoPreventivo:
        item = await self.get(plano_id)
        payload = data.model_dump(exclude_unset=True, exclude={"checklist"})
        for k, v in payload.items():
            setattr(item, k, v)
        await self.repo.flush()
        if data.checklist is not None:
            await self._replace_checklist(item.tenant_id, item.id, data.checklist)
        await audit_service.record(
            AuditAction.UPDATE,
            entity="man_plano_preventivo",
            entity_id=item.id,
            description=f"Plano preventivo atualizado: {item.nome}",
        )
        return item

    async def delete(self, plano_id: uuid.UUID) -> None:
        item = await self.get(plano_id)
        await self.checklist_repo.delete_by_plano(plano_id)
        await self.repo.delete(item)
        await audit_service.record(
            AuditAction.DELETE,
            entity="man_plano_preventivo",
            entity_id=item.id,
            description=f"Plano preventivo excluído: {item.nome}",
        )

    async def link_veiculo(
        self, tenant_id: uuid.UUID, plano_id: uuid.UUID, data: VeiculoPlanoLink
    ) -> ManVeiculoPlano:
        await self.get(plano_id)
        await self.veiculo_svc.get(data.veiculo_id)
        if await self.veiculo_plano_repo.get_vinculo(data.veiculo_id, plano_id):
            raise ConflictError("Veículo já vinculado ao plano.", code="plano_vinculado")
        vinculo = ManVeiculoPlano(
            tenant_id=tenant_id,
            plano_id=plano_id,
            veiculo_id=data.veiculo_id,
            km_ultima_execucao=data.km_ultima_execucao,
            data_ultima_execucao=data.data_ultima_execucao,
        )
        self.veiculo_plano_repo.add(vinculo)
        await self.veiculo_plano_repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="man_veiculo_plano",
            entity_id=vinculo.id,
            description=f"Veículo {data.veiculo_id} vinculado ao plano {plano_id}",
        )
        return vinculo

    async def unlink_veiculo(self, plano_id: uuid.UUID, veiculo_id: uuid.UUID) -> None:
        vinculo = await self.veiculo_plano_repo.get_vinculo(veiculo_id, plano_id)
        if vinculo is None:
            raise NotFoundError("Vínculo veículo/plano não encontrado.")
        await self.veiculo_plano_repo.delete(vinculo)
        await audit_service.record(
            AuditAction.DELETE,
            entity="man_veiculo_plano",
            entity_id=vinculo.id,
            description=f"Veículo {veiculo_id} desvinculado do plano {plano_id}",
        )

    async def list_veiculo_planos(
        self, params: PageParams, veiculo_id: uuid.UUID
    ) -> Page[ManVeiculoPlano]:
        await self.veiculo_svc.get(veiculo_id)
        return await self.veiculo_plano_repo.paginate(
            params, stmt=self.veiculo_plano_repo.list_by_veiculo(veiculo_id)
        )

    async def proximas_preventivas(
        self, params: PageParams | None = None
    ) -> list[PreventivaUrgenciaItem]:
        stmt = self.veiculo_plano_repo.list_all_active()
        vinculos = list((await self.session.execute(stmt)).scalars().all())
        resultados: list[PreventivaUrgenciaItem] = []

        for vp in vinculos:
            plano = await self.repo.get(vp.plano_id)
            if plano is None or plano.status != CadastroStatus.ACTIVE:
                continue
            veiculo = await self.veiculo_svc.repo.get(vp.veiculo_id)
            if veiculo is None:
                continue

            km_restante, dias_restantes, urgencia = _calc_preventiva_urgencia(
                km_atual=veiculo.km_atual,
                km_ultima=vp.km_ultima_execucao,
                data_ultima=vp.data_ultima_execucao,
                intervalo_km=plano.intervalo_km,
                intervalo_meses=plano.intervalo_meses,
            )
            resultados.append(
                PreventivaUrgenciaItem(
                    veiculo_plano_id=vp.id,
                    veiculo_id=vp.veiculo_id,
                    plano_id=vp.plano_id,
                    plano_nome=plano.nome,
                    km_atual=veiculo.km_atual,
                    km_ultima_execucao=vp.km_ultima_execucao,
                    data_ultima_execucao=vp.data_ultima_execucao,
                    intervalo_km=plano.intervalo_km,
                    intervalo_meses=plano.intervalo_meses,
                    km_restante=km_restante,
                    dias_restantes=dias_restantes,
                    urgencia_pct=round(urgencia * 100, 2),
                )
            )

        resultados.sort(key=lambda x: x.urgencia_pct, reverse=True)
        if params is not None:
            start = params.offset
            end = start + params.limit
            return resultados[start:end]
        return resultados

    async def gerar_os_preventiva(
        self, tenant_id: uuid.UUID, veiculo_plano_id: uuid.UUID
    ) -> ManOrdemServico:
        vp = await self.veiculo_plano_repo.get(veiculo_plano_id)
        if vp is None:
            raise NotFoundError("Vínculo veículo/plano não encontrado.")
        plano = await self.get(vp.plano_id)
        veiculo = await self.veiculo_svc.get(vp.veiculo_id)

        os_data = OrdemServicoCreate(
            veiculo_id=vp.veiculo_id,
            tipo=OrdemServicoTipo.PREVENTIVA,
            origem=OrdemServicoOrigem.PLANO_PREVENTIVO,
            fornecedor_id=plano.fornecedor_sugerido_id,
            filial_id=veiculo.filial_id,
            plano_preventivo_id=plano.id,
            km_entrada=veiculo.km_atual,
            observacoes=f"Gerada automaticamente pelo plano {plano.nome}",
        )
        return await self.os_svc.create(tenant_id, os_data)

    async def avaliar_planos_automaticos(self, tenant_id: uuid.UUID) -> list[ManOrdemServico]:
        """Avalia vínculos com plano automático e gera OS ao atingir 100% do gatilho."""
        stmt = self.veiculo_plano_repo.list_all_active()
        vinculos = list((await self.session.execute(stmt)).scalars().all())
        geradas: list[ManOrdemServico] = []

        for vp in vinculos:
            if vp.tenant_id != tenant_id:
                continue
            plano = await self.repo.get(vp.plano_id)
            if plano is None or not plano.automatico or plano.status != CadastroStatus.ACTIVE:
                continue
            veiculo = await self.veiculo_svc.repo.get(vp.veiculo_id)
            if veiculo is None:
                continue

            _, _, urgencia = _calc_preventiva_urgencia(
                km_atual=veiculo.km_atual,
                km_ultima=vp.km_ultima_execucao,
                data_ultima=vp.data_ultima_execucao,
                intervalo_km=plano.intervalo_km,
                intervalo_meses=plano.intervalo_meses,
            )
            if urgencia >= 1.0:
                os_item = await self.gerar_os_preventiva(tenant_id, vp.id)
                geradas.append(os_item)

        return geradas

    async def _replace_checklist(
        self, tenant_id: uuid.UUID, plano_id: uuid.UUID, items: list
    ) -> None:
        await self.checklist_repo.delete_by_plano(plano_id)
        for entry in items:
            payload = entry.model_dump() if hasattr(entry, "model_dump") else entry
            row = ManPlanoChecklist(tenant_id=tenant_id, plano_id=plano_id, **payload)
            self.checklist_repo.add(row)
        await self.checklist_repo.flush()


class PecaService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PecaRepository(session)

    async def list_items(
        self, params: PageParams, *, search: str | None = None
    ) -> Page[ManPeca]:
        return await self.repo.paginate(params, stmt=self.repo.search_query(search=search))

    async def get(self, peca_id: uuid.UUID) -> ManPeca:
        item = await self.repo.get(peca_id)
        if item is None:
            raise NotFoundError("Peça não encontrada.")
        return item

    async def create(self, tenant_id: uuid.UUID, data: PecaCreate) -> ManPeca:
        if await self.repo.get_by_codigo(data.codigo):
            raise ConflictError("Já existe peça com este código.", code="codigo_taken")
        item = ManPeca(tenant_id=tenant_id, **data.model_dump())
        self.repo.add(item)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="man_peca",
            entity_id=item.id,
            description=f"Peça criada: {item.codigo} — {item.nome}",
        )
        return item

    async def update(self, peca_id: uuid.UUID, data: PecaUpdate) -> ManPeca:
        item = await self.get(peca_id)
        payload = data.model_dump(exclude_unset=True)
        if "codigo" in payload and payload["codigo"] != item.codigo:
            existing = await self.repo.get_by_codigo(payload["codigo"])
            if existing and existing.id != peca_id:
                raise ConflictError("Já existe peça com este código.", code="codigo_taken")
        for k, v in payload.items():
            setattr(item, k, v)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="man_peca",
            entity_id=item.id,
            description=f"Peça atualizada: {item.codigo}",
        )
        return item

    async def delete(self, peca_id: uuid.UUID) -> None:
        item = await self.get(peca_id)
        await self.repo.delete(item)
        await audit_service.record(
            AuditAction.DELETE,
            entity="man_peca",
            entity_id=item.id,
            description=f"Peça excluída: {item.codigo}",
        )


class EstoqueService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = EstoquePecaRepository(session)
        self.mov_repo = EstoqueMovimentoRepository(session)
        self.peca_svc = PecaService(session)

    async def list_estoque(
        self,
        params: PageParams,
        *,
        filial_id: uuid.UUID | None = None,
        search: str | None = None,
    ) -> Page[ManEstoquePeca]:
        stmt = self.repo.list_query(filial_id=filial_id, search=search)
        return await self.repo.paginate(params, stmt=stmt)

    async def list_alertas(self, params: PageParams) -> Page[EstoqueAlertaItem]:
        page = await self.repo.paginate(params, stmt=self.repo.alertas_query())
        alertas: list[EstoqueAlertaItem] = []
        for est in page.items:
            peca = await self.peca_svc.get(est.peca_id)
            alertas.append(
                EstoqueAlertaItem(
                    estoque_id=est.id,
                    peca_id=est.peca_id,
                    peca_codigo=peca.codigo,
                    peca_nome=peca.nome,
                    filial_id=est.filial_id,
                    quantidade_atual=est.quantidade_atual,
                    quantidade_minima=est.quantidade_minima,
                )
            )
        return Page(items=alertas, total=page.total, page=page.page, size=page.size)

    async def get(self, estoque_id: uuid.UUID) -> ManEstoquePeca:
        item = await self.repo.get(estoque_id)
        if item is None:
            raise NotFoundError("Posição de estoque não encontrada.")
        return item

    async def ensure_estoque(
        self, tenant_id: uuid.UUID, peca_id: uuid.UUID, data: EstoqueEnsure
    ) -> ManEstoquePeca:
        await self.peca_svc.get(peca_id)
        existing = await self.repo.get_by_peca_filial(peca_id, data.filial_id)
        if existing:
            return existing
        item = ManEstoquePeca(
            tenant_id=tenant_id,
            peca_id=peca_id,
            filial_id=data.filial_id,
            quantidade_atual=Decimal("0"),
            quantidade_minima=data.quantidade_minima,
            quantidade_maxima=data.quantidade_maxima,
            localizacao=data.localizacao,
        )
        self.repo.add(item)
        await self.repo.flush()
        return item

    async def entrada(
        self, tenant_id: uuid.UUID, peca_id: uuid.UUID, data: EstoqueEntrada
    ) -> ManEstoqueMovimento:
        peca = await self.peca_svc.get(peca_id)
        estoque = await self.ensure_estoque(
            tenant_id,
            peca_id,
            EstoqueEnsure(filial_id=data.filial_id),
        )
        estoque.quantidade_atual += data.quantidade
        if data.custo_unitario > 0:
            peca.custo_medio = data.custo_unitario

        mov = ManEstoqueMovimento(
            tenant_id=tenant_id,
            peca_id=peca_id,
            filial_id=data.filial_id,
            tipo=EstoqueMovimentoTipo.ENTRADA,
            quantidade=data.quantidade,
            custo_unitario=data.custo_unitario,
            observacoes=data.observacoes,
            ocorrido_em=datetime.now(tz=UTC),
        )
        self.mov_repo.add(mov)
        await self.mov_repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="man_estoque_movimento",
            entity_id=mov.id,
            description=f"Entrada estoque peça {peca.codigo} (+{data.quantidade})",
        )
        return mov

    async def saida(
        self, tenant_id: uuid.UUID, peca_id: uuid.UUID, data: EstoqueSaida
    ) -> ManEstoqueMovimento:
        peca = await self.peca_svc.get(peca_id)
        estoque = await self.repo.get_by_peca_filial(peca_id, data.filial_id)
        if estoque is None or estoque.quantidade_atual < data.quantidade:
            raise ConflictError(
                "Estoque insuficiente para a saída.",
                code="estoque_insuficiente",
            )
        estoque.quantidade_atual -= data.quantidade
        mov = ManEstoqueMovimento(
            tenant_id=tenant_id,
            peca_id=peca_id,
            filial_id=data.filial_id,
            tipo=EstoqueMovimentoTipo.SAIDA,
            quantidade=data.quantidade,
            custo_unitario=data.custo_unitario or peca.custo_medio,
            os_id=data.os_id,
            observacoes=data.observacoes,
            ocorrido_em=datetime.now(tz=UTC),
        )
        self.mov_repo.add(mov)
        await self.mov_repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="man_estoque_movimento",
            entity_id=mov.id,
            description=f"Saída estoque peça {peca.codigo} (-{data.quantidade})",
        )
        return mov

    async def ajuste(
        self, tenant_id: uuid.UUID, peca_id: uuid.UUID, data: EstoqueAjuste
    ) -> ManEstoqueMovimento:
        await self.peca_svc.get(peca_id)
        estoque = await self.ensure_estoque(
            tenant_id, peca_id, EstoqueEnsure(filial_id=data.filial_id)
        )
        nova_qtd = estoque.quantidade_atual + data.quantidade
        if nova_qtd < 0:
            raise ConflictError(
                "Ajuste resultaria em estoque negativo.",
                code="estoque_negativo",
            )
        estoque.quantidade_atual = nova_qtd
        mov = ManEstoqueMovimento(
            tenant_id=tenant_id,
            peca_id=peca_id,
            filial_id=data.filial_id,
            tipo=EstoqueMovimentoTipo.AJUSTE,
            quantidade=data.quantidade,
            custo_unitario=data.custo_unitario,
            observacoes=data.observacoes,
            ocorrido_em=datetime.now(tz=UTC),
        )
        self.mov_repo.add(mov)
        await self.mov_repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="man_estoque_movimento",
            entity_id=mov.id,
            description=f"Ajuste estoque peça {peca_id} ({data.quantidade:+})",
        )
        return mov

    async def transferencia(
        self, tenant_id: uuid.UUID, peca_id: uuid.UUID, data: EstoqueTransferencia
    ) -> ManEstoqueMovimento:
        if data.filial_origem_id == data.filial_destino_id:
            raise ValidationError("Filial de origem e destino devem ser diferentes.")
        await self.peca_svc.get(peca_id)
        origem = await self.repo.get_by_peca_filial(peca_id, data.filial_origem_id)
        if origem is None or origem.quantidade_atual < data.quantidade:
            raise ConflictError(
                "Estoque insuficiente na filial de origem.",
                code="estoque_insuficiente",
            )
        destino = await self.ensure_estoque(
            tenant_id, peca_id, EstoqueEnsure(filial_id=data.filial_destino_id)
        )
        origem.quantidade_atual -= data.quantidade
        destino.quantidade_atual += data.quantidade

        mov = ManEstoqueMovimento(
            tenant_id=tenant_id,
            peca_id=peca_id,
            filial_id=data.filial_origem_id,
            filial_destino_id=data.filial_destino_id,
            tipo=EstoqueMovimentoTipo.TRANSFERENCIA,
            quantidade=data.quantidade,
            custo_unitario=Decimal("0"),
            observacoes=data.observacoes,
            ocorrido_em=datetime.now(tz=UTC),
        )
        self.mov_repo.add(mov)
        await self.mov_repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="man_estoque_movimento",
            entity_id=mov.id,
            description=(
                f"Transferência peça {peca_id}: "
                f"{data.filial_origem_id} → {data.filial_destino_id}"
            ),
        )
        return mov


class PneuService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PneuRepository(session)
        self.hist_repo = PneuHistoricoRepository(session)
        self.veiculo_svc = VeiculoService(session)

    async def list_items(
        self,
        params: PageParams,
        *,
        status: PneuStatus | None = None,
        veiculo_id: uuid.UUID | None = None,
        search: str | None = None,
    ) -> Page[ManPneu]:
        stmt = self.repo.list_query(status=status, veiculo_id=veiculo_id, search=search)
        return await self.repo.paginate(params, stmt=stmt)

    async def get(self, pneu_id: uuid.UUID) -> ManPneu:
        item = await self.repo.get(pneu_id)
        if item is None:
            raise NotFoundError("Pneu não encontrado.")
        return item

    async def create(self, tenant_id: uuid.UUID, data: PneuCreate) -> ManPneu:
        if await self.repo.get_by_numero_fogo(data.numero_fogo):
            raise ConflictError(
                "Já existe pneu com este número de fogo.", code="numero_fogo_taken"
            )
        item = ManPneu(tenant_id=tenant_id, status=PneuStatus.NOVO, **data.model_dump())
        self.repo.add(item)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.CREATE,
            entity="man_pneu",
            entity_id=item.id,
            description=f"Pneu cadastrado: {item.numero_fogo}",
        )
        return item

    async def update(self, pneu_id: uuid.UUID, data: PneuUpdate) -> ManPneu:
        item = await self.get(pneu_id)
        if item.status == PneuStatus.DESCARTADO:
            raise ConflictError("Pneu descartado não pode ser alterado.", code="pneu_descartado")
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(item, k, v)
        await self.repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="man_pneu",
            entity_id=item.id,
            description=f"Pneu atualizado: {item.numero_fogo}",
        )
        return item

    async def delete(self, pneu_id: uuid.UUID) -> None:
        item = await self.get(pneu_id)
        if item.status == PneuStatus.EM_USO:
            raise ConflictError(
                "Pneu em uso não pode ser excluído.", code="pneu_em_uso"
            )
        await self.repo.delete(item)
        await audit_service.record(
            AuditAction.DELETE,
            entity="man_pneu",
            entity_id=item.id,
            description=f"Pneu excluído: {item.numero_fogo}",
        )

    async def instalar(
        self, tenant_id: uuid.UUID, pneu_id: uuid.UUID, data: PneuInstalar
    ) -> ManPneu:
        item = await self.get(pneu_id)
        if item.status == PneuStatus.DESCARTADO:
            raise ConflictError("Pneu descartado não pode ser instalado.", code="pneu_descartado")
        await self.veiculo_svc.get(data.veiculo_id)

        item.veiculo_id = data.veiculo_id
        item.posicao = data.posicao
        item.km_instalacao = data.km
        item.km_atual = data.km
        item.status = PneuStatus.EM_USO
        await self.repo.flush()

        hist = ManPneuHistorico(
            tenant_id=tenant_id,
            pneu_id=pneu_id,
            veiculo_id=data.veiculo_id,
            posicao=data.posicao,
            km_evento=data.km,
            tipo_evento="instalacao",
            ocorrido_em=datetime.now(tz=UTC),
        )
        self.hist_repo.add(hist)
        await self.hist_repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="man_pneu",
            entity_id=item.id,
            description=f"Pneu {item.numero_fogo} instalado em {data.veiculo_id}",
        )
        return item

    async def rodizio(
        self, tenant_id: uuid.UUID, pneu_id: uuid.UUID, data: PneuRodizio
    ) -> ManPneu:
        item = await self.get(pneu_id)
        if item.status != PneuStatus.EM_USO:
            raise ValidationError("Rodízio só é permitido para pneu em uso.")
        posicao_anterior = item.posicao
        item.posicao = data.posicao_destino
        if data.km is not None:
            item.km_atual = data.km
        await self.repo.flush()

        hist = ManPneuHistorico(
            tenant_id=tenant_id,
            pneu_id=pneu_id,
            veiculo_id=item.veiculo_id,
            posicao=data.posicao_destino,
            km_evento=data.km,
            tipo_evento="rodizio",
            observacoes=data.observacoes
            or (f"{posicao_anterior.value} → {data.posicao_destino.value}" if posicao_anterior else None),
            ocorrido_em=datetime.now(tz=UTC),
        )
        self.hist_repo.add(hist)
        await self.hist_repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="man_pneu",
            entity_id=item.id,
            description=f"Rodízio pneu {item.numero_fogo}",
        )
        return item

    async def inspecionar(
        self, tenant_id: uuid.UUID, pneu_id: uuid.UUID, data: PneuInspecionar
    ) -> ManPneu:
        item = await self.get(pneu_id)
        item.sulco_mm = data.sulco_mm
        if data.km is not None:
            item.km_atual = data.km
        await self.repo.flush()

        hist = ManPneuHistorico(
            tenant_id=tenant_id,
            pneu_id=pneu_id,
            veiculo_id=item.veiculo_id,
            posicao=item.posicao,
            km_evento=data.km,
            tipo_evento="inspecao",
            observacoes=data.observacoes or f"Sulco: {data.sulco_mm} mm",
            ocorrido_em=datetime.now(tz=UTC),
        )
        self.hist_repo.add(hist)
        await self.hist_repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="man_pneu",
            entity_id=item.id,
            description=f"Inspeção pneu {item.numero_fogo}: sulco {data.sulco_mm} mm",
        )
        return item

    async def descartar(
        self, tenant_id: uuid.UUID, pneu_id: uuid.UUID, data: PneuDescartar
    ) -> ManPneu:
        item = await self.get(pneu_id)
        if item.status == PneuStatus.DESCARTADO:
            return item

        veiculo_id = item.veiculo_id
        item.status = PneuStatus.DESCARTADO
        item.veiculo_id = None
        item.posicao = None
        if data.km is not None:
            item.km_atual = data.km
        await self.repo.flush()

        hist = ManPneuHistorico(
            tenant_id=tenant_id,
            pneu_id=pneu_id,
            veiculo_id=veiculo_id,
            posicao=None,
            km_evento=data.km,
            tipo_evento="descarte",
            observacoes=data.motivo,
            ocorrido_em=datetime.now(tz=UTC),
        )
        self.hist_repo.add(hist)
        await self.hist_repo.flush()
        await audit_service.record(
            AuditAction.UPDATE,
            entity="man_pneu",
            entity_id=item.id,
            description=f"Pneu descartado: {item.numero_fogo}",
        )
        return item

    async def alertas_vida_util(
        self, params: PageParams, *, threshold_pct: float = 0.9
    ) -> Page[PneuAlertaItem]:
        stmt = self.repo.list_query(status=PneuStatus.EM_USO)
        pneus = list((await self.session.execute(stmt)).scalars().all())
        alertas: list[PneuAlertaItem] = []
        for pneu in pneus:
            if not pneu.vida_util_km or pneu.km_instalacao is None or pneu.km_atual is None:
                continue
            km_percorrido = max(0, pneu.km_atual - pneu.km_instalacao)
            uso_pct = km_percorrido / pneu.vida_util_km
            if uso_pct >= threshold_pct:
                alertas.append(
                    PneuAlertaItem(
                        pneu_id=pneu.id,
                        numero_fogo=pneu.numero_fogo,
                        veiculo_id=pneu.veiculo_id,
                        km_percorrido=km_percorrido,
                        vida_util_km=pneu.vida_util_km,
                        uso_pct=round(uso_pct * 100, 2),
                    )
                )
        alertas.sort(key=lambda x: x.uso_pct, reverse=True)
        total = len(alertas)
        start = params.offset
        end = start + params.limit
        return Page(items=alertas[start:end], total=total, page=params.page, size=params.size)
