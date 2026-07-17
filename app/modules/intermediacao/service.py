"""Serviços de intermediação — locação terceirizada e repasse financeiro."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.shared.repository import BaseRepository
from app.modules.cadastros.models_extra import Fornecedor
from app.modules.financeiro.service import ContaPagarService, ContaReceberService
from app.modules.frota.models import FrotaVeiculo
from app.modules.intermediacao.models import (
    FornecedorContratoLocacao,
    FornecedorContratoPreco,
    FrotaIndisponibilidadeTerceiro,
    IntermediacaoConfig,
    LocRepasseLancamento,
)
from app.modules.intermediacao.schemas import (
    ContratoFornecedorCreate,
    ContratoFornecedorUpdate,
    ContratoPrecoCreate,
    IndisponibilidadeTerceiroCreate,
    IntermediacaoConfigUpdate,
    RepasseCalculoResult,
)
from app.modules.locacoes.models import LocContrato
from app.modules.reservas.models import ResReserva
from app.shared.enums import (
    CadastroStatus,
    ContaPagarOrigem,
    ContaReceberOrigem,
    ContratoFornecedorStatus,
    ContratoStatus,
    IntermediacaoStatus,
    ModeloNegocioTerceiro,
    ModoOperacaoLocadora,
    TituloStatus,
    VeiculoPropriedade,
    VeiculoStatus,
)

_ZERO = Decimal("0")


def _money(value: Decimal | float | int | None) -> Decimal:
    if value is None:
        return _ZERO
    return Decimal(str(value)).quantize(Decimal("0.01"))


class IntermediacaoConfigRepository(BaseRepository[IntermediacaoConfig]):
    model = IntermediacaoConfig


class ContratoFornecedorRepository(BaseRepository[FornecedorContratoLocacao]):
    model = FornecedorContratoLocacao


class ContratoPrecoRepository(BaseRepository[FornecedorContratoPreco]):
    model = FornecedorContratoPreco


class IndisponibilidadeTerceiroRepository(BaseRepository[FrotaIndisponibilidadeTerceiro]):
    model = FrotaIndisponibilidadeTerceiro


class RepasseLancamentoRepository(BaseRepository[LocRepasseLancamento]):
    model = LocRepasseLancamento


class IntermediacaoService:
    """Orquestra regras de locação própria vs terceirizada."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.config_repo = IntermediacaoConfigRepository(session)
        self.contrato_repo = ContratoFornecedorRepository(session)
        self.preco_repo = ContratoPrecoRepository(session)
        self.indisp_repo = IndisponibilidadeTerceiroRepository(session)
        self.repasse_repo = RepasseLancamentoRepository(session)

    async def get_config(self, tenant_id: uuid.UUID) -> IntermediacaoConfig:
        stmt = select(IntermediacaoConfig).where(
            IntermediacaoConfig.tenant_id == tenant_id,
            IntermediacaoConfig.deleted_at.is_(None),
        )
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if row is None:
            row = IntermediacaoConfig(tenant_id=tenant_id)
            self.config_repo.add(row)
            await self.config_repo.flush()
        return row

    async def update_config(
        self, tenant_id: uuid.UUID, data: IntermediacaoConfigUpdate
    ) -> IntermediacaoConfig:
        cfg = await self.get_config(tenant_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(cfg, field, value)
        await self.config_repo.flush()
        return cfg

    async def list_contratos_fornecedor(
        self, tenant_id: uuid.UUID, *, fornecedor_id: uuid.UUID | None = None
    ) -> list[FornecedorContratoLocacao]:
        stmt = select(FornecedorContratoLocacao).where(
            FornecedorContratoLocacao.tenant_id == tenant_id,
            FornecedorContratoLocacao.deleted_at.is_(None),
        )
        if fornecedor_id:
            stmt = stmt.where(FornecedorContratoLocacao.fornecedor_id == fornecedor_id)
        stmt = stmt.order_by(FornecedorContratoLocacao.vigencia_inicio.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_contrato_fornecedor(self, contrato_id: uuid.UUID) -> FornecedorContratoLocacao:
        return await self.contrato_repo.get(contrato_id)

    async def create_contrato_fornecedor(
        self, tenant_id: uuid.UUID, data: ContratoFornecedorCreate
    ) -> FornecedorContratoLocacao:
        fornecedor = await self._get_fornecedor(data.fornecedor_id)
        if not fornecedor.locadora_parceira:
            fornecedor.locadora_parceira = True
        contrato = FornecedorContratoLocacao(
            tenant_id=tenant_id,
            fornecedor_id=data.fornecedor_id,
            numero=data.numero.strip(),
            titulo=data.titulo.strip(),
            status=ContratoFornecedorStatus.RASCUNHO,
            modelo_negocio=data.modelo_negocio,
            tipo_calculo=data.tipo_calculo,
            percentual_repasse=data.percentual_repasse,
            percentual_comissao=data.percentual_comissao,
            valor_diaria_repasse=data.valor_diaria_repasse,
            margem_minima_percentual=data.margem_minima_percentual,
            prazo_pagamento_dias=data.prazo_pagamento_dias,
            vigencia_inicio=data.vigencia_inicio,
            vigencia_fim=data.vigencia_fim,
            km_livre_dia=data.km_livre_dia,
            valor_km_excedente=data.valor_km_excedente,
            seguro_incluso=data.seguro_incluso,
            clausulas=data.clausulas,
            observacoes=data.observacoes,
        )
        self.contrato_repo.add(contrato)
        await self.contrato_repo.flush()
        return contrato

    async def update_contrato_fornecedor(
        self, contrato_id: uuid.UUID, data: ContratoFornecedorUpdate
    ) -> FornecedorContratoLocacao:
        contrato = await self.get_contrato_fornecedor(contrato_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(contrato, field, value)
        await self.contrato_repo.flush()
        return contrato

    async def add_preco_contrato(
        self, tenant_id: uuid.UUID, contrato_id: uuid.UUID, data: ContratoPrecoCreate
    ) -> FornecedorContratoPreco:
        await self.get_contrato_fornecedor(contrato_id)
        if data.valor_repasse_diaria > data.valor_cliente_diaria:
            raise ValidationError(
                "Valor de repasse não pode ser maior que o valor cobrado do cliente."
            )
        preco = FornecedorContratoPreco(
            tenant_id=tenant_id,
            contrato_fornecedor_id=contrato_id,
            categoria_id=data.categoria_id,
            filial_id=data.filial_id,
            vigencia_inicio=data.vigencia_inicio,
            vigencia_fim=data.vigencia_fim,
            hora_inicio=data.hora_inicio,
            hora_fim=data.hora_fim,
            dias_minimos=data.dias_minimos,
            dias_maximos=data.dias_maximos,
            valor_cliente_diaria=_money(data.valor_cliente_diaria),
            valor_repasse_diaria=_money(data.valor_repasse_diaria),
            valor_hora_extra_cliente=_money(data.valor_hora_extra_cliente)
            if data.valor_hora_extra_cliente is not None
            else None,
            valor_hora_extra_repasse=_money(data.valor_hora_extra_repasse)
            if data.valor_hora_extra_repasse is not None
            else None,
            percentual_comissao=data.percentual_comissao,
            taxa_entrega=_money(data.taxa_entrega) if data.taxa_entrega is not None else None,
            prioridade=data.prioridade,
            observacoes=data.observacoes,
        )
        self.preco_repo.add(preco)
        await self.preco_repo.flush()
        return preco

    async def list_precos_contrato(self, contrato_id: uuid.UUID) -> list[FornecedorContratoPreco]:
        stmt = (
            select(FornecedorContratoPreco)
            .where(
                FornecedorContratoPreco.contrato_fornecedor_id == contrato_id,
                FornecedorContratoPreco.deleted_at.is_(None),
            )
            .order_by(FornecedorContratoPreco.prioridade.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def resolve_contrato_ativo_fornecedor(
        self,
        fornecedor_id: uuid.UUID,
        *,
        ref_date: date | None = None,
    ) -> FornecedorContratoLocacao | None:
        ref = ref_date or date.today()
        stmt = (
            select(FornecedorContratoLocacao)
            .where(
                FornecedorContratoLocacao.fornecedor_id == fornecedor_id,
                FornecedorContratoLocacao.status == ContratoFornecedorStatus.ATIVO,
                FornecedorContratoLocacao.deleted_at.is_(None),
                FornecedorContratoLocacao.vigencia_inicio <= ref,
                or_(
                    FornecedorContratoLocacao.vigencia_fim.is_(None),
                    FornecedorContratoLocacao.vigencia_fim >= ref,
                ),
            )
            .order_by(FornecedorContratoLocacao.vigencia_inicio.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def vincular_veiculo_terceirizado(
        self, veiculo: FrotaVeiculo, *, fornecedor_id: uuid.UUID | None = None
    ) -> None:
        """Valida e vincula contrato regente ao cadastrar/editar veículo terceirizado."""
        if veiculo.propriedade != VeiculoPropriedade.TERCEIRIZADA:
            veiculo.contrato_fornecedor_id = None
            veiculo.fornecedor_id = None
            return
        fid = fornecedor_id or veiculo.fornecedor_id
        if fid is None:
            raise ValidationError(
                "Veículo terceirizado exige fornecedor (locadora parceira) cadastrado."
            )
        fornecedor = await self._get_fornecedor(fid)
        if not fornecedor.locadora_parceira:
            raise ValidationError("Fornecedor selecionado não está marcado como locadora parceira.")
        contrato = await self.resolve_contrato_ativo_fornecedor(fid)
        cfg = await self.get_config(veiculo.tenant_id)
        if cfg.exige_contrato_fornecedor and contrato is None:
            raise ValidationError(
                "Não há contrato ativo com a locadora parceira. Cadastre em Intermediação → Contratos."
            )
        veiculo.fornecedor_id = fid
        veiculo.contrato_fornecedor_id = contrato.id if contrato else None
        if not veiculo.publicar_site and cfg.publicar_terceiros_site:
            veiculo.publicar_site = True

    async def veiculo_bloqueado_terceiro(
        self,
        veiculo_id: uuid.UUID,
        inicio: datetime,
        fim: datetime,
    ) -> bool:
        stmt = select(FrotaIndisponibilidadeTerceiro.id).where(
            FrotaIndisponibilidadeTerceiro.veiculo_id == veiculo_id,
            FrotaIndisponibilidadeTerceiro.deleted_at.is_(None),
            FrotaIndisponibilidadeTerceiro.inicio_em < fim,
            or_(
                FrotaIndisponibilidadeTerceiro.fim_em.is_(None),
                FrotaIndisponibilidadeTerceiro.fim_em > inicio,
            ),
        )
        return (await self.session.execute(stmt)).scalar_one_or_none() is not None

    async def veiculo_em_contrato_ativo(
        self, veiculo_id: uuid.UUID, inicio: datetime, fim: datetime
    ) -> bool:
        stmt = select(LocContrato.id).where(
            LocContrato.veiculo_id == veiculo_id,
            LocContrato.deleted_at.is_(None),
            LocContrato.status.in_(
                [
                    ContratoStatus.AGUARDANDO_CHECKOUT,
                    ContratoStatus.ATIVO,
                    ContratoStatus.AGUARDANDO_CHECKIN,
                ]
            ),
            LocContrato.retirada_prevista_em < fim,
            LocContrato.devolucao_prevista_em > inicio,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none() is not None

    async def veiculo_disponivel_periodo(
        self,
        veiculo: FrotaVeiculo,
        inicio: datetime,
        fim: datetime,
    ) -> tuple[bool, str | None]:
        if veiculo.status in {VeiculoStatus.BLOQUEADO, VeiculoStatus.BAIXADO, VeiculoStatus.MANUTENCAO}:
            return False, f"Veículo indisponível (status: {veiculo.status.value})."
        if await self.veiculo_bloqueado_terceiro(veiculo.id, inicio, fim):
            return False, "Veículo bloqueado pelo proprietário (locação externa/manutenção)."
        if await self.veiculo_em_contrato_ativo(veiculo.id, inicio, fim):
            return False, "Veículo já possui contrato ativo no período."
        return True, None

    async def registrar_indisponibilidade(
        self,
        tenant_id: uuid.UUID,
        data: IndisponibilidadeTerceiroCreate,
        *,
        user_id: uuid.UUID | None = None,
    ) -> FrotaIndisponibilidadeTerceiro:
        veiculo = await self._get_veiculo(data.veiculo_id)
        if veiculo.propriedade != VeiculoPropriedade.TERCEIRIZADA:
            raise ValidationError("Indisponibilidade de terceiro só se aplica a veículos terceirizados.")
        if data.fim_em and data.fim_em <= data.inicio_em:
            raise ValidationError("Fim deve ser posterior ao início.")
        row = FrotaIndisponibilidadeTerceiro(
            tenant_id=tenant_id,
            veiculo_id=data.veiculo_id,
            fornecedor_id=data.fornecedor_id,
            inicio_em=data.inicio_em,
            fim_em=data.fim_em,
            motivo=data.motivo,
            sincronizar_site=data.sincronizar_site,
            registrado_por_id=user_id,
            observacoes=data.observacoes,
        )
        self.indisp_repo.add(row)
        if data.sincronizar_site or data.motivo.value == "locado_pelo_proprietario":
            veiculo.status = VeiculoStatus.BLOQUEADO
            veiculo.motivo_bloqueio = data.motivo.value
            veiculo.publicar_site = False
        await self.indisp_repo.flush()
        return row

    async def calcular_repasse(
        self,
        *,
        tenant_id: uuid.UUID,
        veiculo: FrotaVeiculo,
        valor_cliente: Decimal,
        dias: int,
        filial_id: uuid.UUID | None = None,
        retirada_em: datetime | None = None,
    ) -> RepasseCalculoResult | None:
        if veiculo.propriedade != VeiculoPropriedade.TERCEIRIZADA:
            return None
        contrato = None
        if veiculo.contrato_fornecedor_id:
            contrato = await self.get_contrato_fornecedor(veiculo.contrato_fornecedor_id)
        elif veiculo.fornecedor_id:
            contrato = await self.resolve_contrato_ativo_fornecedor(veiculo.fornecedor_id)
        if contrato is None:
            return None

        ref_date = (retirada_em or datetime.now(tz=UTC)).date()
        preco = await self._resolver_preco_tabela(
            contrato.id,
            categoria_id=veiculo.categoria_id,
            filial_id=filial_id,
            ref_date=ref_date,
            dias=dias,
        )

        valor_cli = _money(valor_cliente)
        modelo = contrato.modelo_negocio

        if preco is not None:
            valor_cli_tabela = _money(preco.valor_cliente_diaria * dias)
            if valor_cli <= _ZERO:
                valor_cli = valor_cli_tabela
            valor_rep = _money(preco.valor_repasse_diaria * dias)
        elif contrato.valor_diaria_repasse is not None:
            valor_rep = _money(contrato.valor_diaria_repasse * dias)
        elif contrato.percentual_repasse is not None:
            valor_rep = _money(valor_cli * contrato.percentual_repasse / Decimal("100"))
        else:
            valor_rep = _ZERO

        if modelo == ModeloNegocioTerceiro.COMISSAO:
            pct = (
                preco.percentual_comissao
                if preco and preco.percentual_comissao is not None
                else contrato.percentual_comissao
            ) or _ZERO
            comissao = _money(valor_cli * pct / Decimal("100"))
            margem = comissao
            valor_rep = _ZERO
        else:
            comissao = _ZERO
            margem = _money(valor_cli - valor_rep)

        margem_pct = _money(margem / valor_cli * 100) if valor_cli > _ZERO else _ZERO
        cfg = await self.get_config(tenant_id)
        min_m = contrato.margem_minima_percentual or cfg.margem_minima_percentual
        if modelo == ModeloNegocioTerceiro.REPASSE and margem_pct < min_m and valor_cli > _ZERO:
            raise ValidationError(
                f"Margem ({margem_pct}%) abaixo do mínimo configurado ({min_m}%)."
            )

        snapshot = {
            "modelo_negocio": modelo.value,
            "contrato_fornecedor_id": str(contrato.id),
            "fornecedor_id": str(contrato.fornecedor_id),
            "valor_cliente": str(valor_cli),
            "valor_repasse": str(valor_rep),
            "valor_margem": str(margem),
            "valor_comissao": str(comissao),
            "dias": dias,
            "preco_tabela_id": str(preco.id) if preco else None,
        }
        return RepasseCalculoResult(
            modelo_negocio=modelo,
            valor_cliente=valor_cli,
            valor_repasse=valor_rep,
            valor_margem=margem,
            valor_comissao=comissao,
            margem_percentual=margem_pct,
            contrato_fornecedor_id=contrato.id,
            fornecedor_id=contrato.fornecedor_id,
            snapshot=snapshot,
        )

    async def aplicar_intermediacao_reserva(self, reserva: ResReserva, veiculo: FrotaVeiculo | None) -> None:
        if veiculo is None or veiculo.propriedade != VeiculoPropriedade.TERCEIRIZADA:
            reserva.intermediacao_status = IntermediacaoStatus.NAO_APLICAVEL
            return
        cfg = await self.get_config(reserva.tenant_id)
        calc = await self.calcular_repasse(
            tenant_id=reserva.tenant_id,
            veiculo=veiculo,
            valor_cliente=reserva.valor_total,
            dias=reserva.dias,
            filial_id=reserva.filial_retirada_id,
            retirada_em=reserva.retirada_em,
        )
        if calc is None:
            raise ValidationError("Veículo terceirizado sem contrato de intermediação válido.")
        reserva.fornecedor_id = calc.fornecedor_id
        reserva.contrato_fornecedor_id = calc.contrato_fornecedor_id
        reserva.modelo_negocio_terceiro = calc.modelo_negocio
        reserva.valor_repasse_total = calc.valor_repasse
        reserva.valor_margem = calc.valor_margem
        reserva.valor_comissao = calc.valor_comissao
        reserva.repasse_snapshot = json.dumps(calc.snapshot, ensure_ascii=False)
        if cfg.aprovar_reserva_automaticamente:
            reserva.intermediacao_status = IntermediacaoStatus.CONFIRMADO_FORNECEDOR
        else:
            reserva.intermediacao_status = IntermediacaoStatus.PENDENTE_APROVACAO

    async def notificar_pendencia_fornecedor(self, reserva: ResReserva) -> None:
        """E-mail/SMS ao contato operacional da locadora parceira."""
        if not reserva.fornecedor_id:
            return
        fornecedor = await self._get_fornecedor(reserva.fornecedor_id)
        from app.modules.notificacoes.schemas import NotificacaoSendInput
        from app.modules.notificacoes.service import NotificationService
        from app.shared.enums import NotificacaoCanal

        canais = [NotificacaoCanal.IN_APP]
        if fornecedor.contato_operacional_email:
            canais.append(NotificacaoCanal.EMAIL)
        if fornecedor.contato_operacional_telefone:
            canais.append(NotificacaoCanal.SMS)
        if len(canais) == 1:
            return
        await NotificationService(self.session).send(
            reserva.tenant_id,
            NotificacaoSendInput(
                titulo=f"Aprovação necessária — Reserva {reserva.numero}",
                mensagem=(
                    f"Nova reserva intermediada {reserva.numero} aguarda confirmação. "
                    f"Retirada: {reserva.retirada_em.strftime('%d/%m/%Y %H:%M')}. "
                    f"Valor repasse: {reserva.valor_repasse_total or 0}."
                ),
                email=fornecedor.contato_operacional_email,
                telefone=fornecedor.contato_operacional_telefone,
                canais=canais,
                evento="intermediacao.pendente_aprovacao",
                referencia_tipo="res_reserva",
                referencia_id=reserva.id,
                link=f"/intermediacao/aprovacoes",
            ),
        )

    async def aprovar_reserva_fornecedor(
        self, reserva_id: uuid.UUID, *, user_id: uuid.UUID | None = None
    ) -> ResReserva:
        from app.modules.reservas.models import ResReserva

        stmt = select(ResReserva).where(
            ResReserva.id == reserva_id,
            ResReserva.deleted_at.is_(None),
        )
        reserva = (await self.session.execute(stmt)).scalar_one_or_none()
        if reserva is None:
            raise ValidationError("Reserva não encontrada.")
        if reserva.intermediacao_status != IntermediacaoStatus.PENDENTE_APROVACAO:
            raise ValidationError("Reserva não aguarda aprovação da locadora parceira.")
        reserva.intermediacao_status = IntermediacaoStatus.CONFIRMADO_FORNECEDOR
        await self.session.flush()
        from app.modules.intermediacao.hooks import fire_intermediacao_event

        await fire_intermediacao_event(
            self.session,
            reserva.tenant_id,
            "intermediacao_aprovada",
            {"reserva_id": str(reserva.id), "numero": reserva.numero, "user_id": str(user_id) if user_id else None},
        )
        return reserva

    async def rejeitar_reserva_fornecedor(
        self, reserva_id: uuid.UUID, motivo: str, *, user_id: uuid.UUID | None = None
    ) -> ResReserva:
        from app.modules.reservas.models import ResReserva
        from app.modules.reservas.schemas import ReservaCancelInput
        from app.modules.reservas.service import ReservaService

        stmt = select(ResReserva).where(
            ResReserva.id == reserva_id,
            ResReserva.deleted_at.is_(None),
        )
        reserva = (await self.session.execute(stmt)).scalar_one_or_none()
        if reserva is None:
            raise ValidationError("Reserva não encontrada.")
        if reserva.intermediacao_status != IntermediacaoStatus.PENDENTE_APROVACAO:
            raise ValidationError("Reserva não aguarda aprovação da locadora parceira.")
        reserva.intermediacao_status = IntermediacaoStatus.REJEITADO_FORNECEDOR
        await self.session.flush()
        await ReservaService(self.session).cancelar(
            reserva_id, ReservaCancelInput(motivo=motivo or "Rejeitada pela locadora parceira")
        )
        from app.modules.intermediacao.hooks import fire_intermediacao_event

        await fire_intermediacao_event(
            self.session,
            reserva.tenant_id,
            "intermediacao_rejeitada",
            {"reserva_id": str(reserva.id), "numero": reserva.numero, "motivo": motivo},
        )
        return reserva

    async def list_aprovacoes_pendentes(self, tenant_id: uuid.UUID) -> list:
        from app.modules.reservas.models import ResReserva

        stmt = (
            select(ResReserva)
            .where(
                ResReserva.tenant_id == tenant_id,
                ResReserva.deleted_at.is_(None),
                ResReserva.intermediacao_status == IntermediacaoStatus.PENDENTE_APROVACAO,
            )
            .order_by(ResReserva.retirada_em.asc())
            .limit(200)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_repasse_lancamentos(
        self, tenant_id: uuid.UUID, *, fornecedor_id: uuid.UUID | None = None
    ) -> list[LocRepasseLancamento]:
        stmt = select(LocRepasseLancamento).where(
            LocRepasseLancamento.tenant_id == tenant_id,
            LocRepasseLancamento.deleted_at.is_(None),
        )
        if fornecedor_id:
            stmt = stmt.where(LocRepasseLancamento.fornecedor_id == fornecedor_id)
        stmt = stmt.order_by(LocRepasseLancamento.created_at.desc()).limit(500)
        return list((await self.session.execute(stmt)).scalars().all())

    async def encerrar_indisponibilidade(self, indisp_id: uuid.UUID) -> FrotaIndisponibilidadeTerceiro:
        row = await self.indisp_repo.get(indisp_id)
        row.fim_em = datetime.now(tz=UTC)
        veiculo = await self._get_veiculo(row.veiculo_id)
        cfg = await self.get_config(row.tenant_id)
        if row.sincronizar_site and cfg.publicar_terceiros_site:
            veiculo.publicar_site = True
        if veiculo.motivo_bloqueio and veiculo.status == VeiculoStatus.BLOQUEADO:
            veiculo.status = VeiculoStatus.DISPONIVEL
            veiculo.motivo_bloqueio = None
        await self.indisp_repo.flush()
        return row

    async def sincronizar_catalogo_site(self, tenant_id: uuid.UUID) -> dict[str, int]:
        """Atualiza flag publicar_site conforme config e bloqueios ativos."""
        cfg = await self.get_config(tenant_id)
        now = datetime.now(tz=UTC)
        stmt = select(FrotaVeiculo).where(
            FrotaVeiculo.tenant_id == tenant_id,
            FrotaVeiculo.deleted_at.is_(None),
            FrotaVeiculo.propriedade == VeiculoPropriedade.TERCEIRIZADA,
        )
        veiculos = list((await self.session.execute(stmt)).scalars().all())
        publicados = 0
        ocultos = 0
        for v in veiculos:
            deseja = cfg.publicar_terceiros_site and v.status == VeiculoStatus.DISPONIVEL
            if deseja:
                bloqueado = await self.veiculo_bloqueado_terceiro(
                    v.id, now, now + timedelta(hours=1)
                )
                deseja = not bloqueado
            if deseja and not v.publicar_site:
                v.publicar_site = True
                publicados += 1
            elif not deseja and v.publicar_site:
                v.publicar_site = False
                ocultos += 1
        await self.session.flush()
        return {"publicados": publicados, "ocultos": ocultos, "total": len(veiculos)}

    async def list_veiculos_site(
        self,
        tenant_id: uuid.UUID,
        *,
        filial_id: uuid.UUID | None = None,
        categoria_id: uuid.UUID | None = None,
    ) -> list[dict]:
        stmt = select(FrotaVeiculo).where(
            FrotaVeiculo.tenant_id == tenant_id,
            FrotaVeiculo.deleted_at.is_(None),
            FrotaVeiculo.publicar_site.is_(True),
            FrotaVeiculo.status == VeiculoStatus.DISPONIVEL,
        )
        if filial_id:
            stmt = stmt.where(FrotaVeiculo.filial_id == filial_id)
        if categoria_id:
            stmt = stmt.where(FrotaVeiculo.categoria_id == categoria_id)
        rows = list((await self.session.execute(stmt)).scalars().all())
        cfg = await self.get_config(tenant_id)
        if cfg.modo_operacao == ModoOperacaoLocadora.PROPRIA:
            rows = [v for v in rows if v.propriedade != VeiculoPropriedade.TERCEIRIZADA]
        elif cfg.modo_operacao == ModoOperacaoLocadora.INTERMEDIACAO:
            rows = [v for v in rows if v.propriedade == VeiculoPropriedade.TERCEIRIZADA]
        return [
            {
                "id": str(v.id),
                "placa": v.placa,
                "categoria_id": str(v.categoria_id),
                "filial_id": str(v.filial_id) if v.filial_id else None,
                "propriedade": v.propriedade.value,
                "terceirizado": v.propriedade == VeiculoPropriedade.TERCEIRIZADA,
                "fornecedor_id": str(v.fornecedor_id) if v.fornecedor_id else None,
            }
            for v in rows
        ]

    async def propagar_intermediacao_contrato(
        self, contrato: LocContrato, reserva: ResReserva | None, veiculo: FrotaVeiculo
    ) -> None:
        if veiculo.propriedade != VeiculoPropriedade.TERCEIRIZADA:
            contrato.intermediacao_status = IntermediacaoStatus.NAO_APLICAVEL
            return
        if reserva and reserva.fornecedor_id:
            contrato.fornecedor_id = reserva.fornecedor_id
            contrato.contrato_fornecedor_id = reserva.contrato_fornecedor_id
            contrato.modelo_negocio_terceiro = reserva.modelo_negocio_terceiro
            contrato.intermediacao_status = reserva.intermediacao_status
            contrato.valor_repasse_total = reserva.valor_repasse_total
            contrato.valor_margem = reserva.valor_margem
            contrato.valor_comissao = reserva.valor_comissao
            contrato.repasse_snapshot = reserva.repasse_snapshot
            return
        calc = await self.calcular_repasse(
            tenant_id=contrato.tenant_id,
            veiculo=veiculo,
            valor_cliente=contrato.valor_total,
            dias=contrato.dias,
            filial_id=contrato.filial_retirada_id,
            retirada_em=contrato.retirada_prevista_em,
        )
        if calc:
            contrato.fornecedor_id = calc.fornecedor_id
            contrato.contrato_fornecedor_id = calc.contrato_fornecedor_id
            contrato.modelo_negocio_terceiro = calc.modelo_negocio
            contrato.valor_repasse_total = calc.valor_repasse
            contrato.valor_margem = calc.valor_margem
            contrato.valor_comissao = calc.valor_comissao
            contrato.repasse_snapshot = json.dumps(calc.snapshot, ensure_ascii=False)
            contrato.intermediacao_status = IntermediacaoStatus.CONFIRMADO_FORNECEDOR

    async def gerar_financeiro_encerramento(self, contrato: LocContrato) -> LocRepasseLancamento | None:
        if contrato.intermediacao_status == IntermediacaoStatus.NAO_APLICAVEL:
            return None
        if not contrato.fornecedor_id:
            return None
        valor_final = _money(contrato.valor_final or contrato.valor_total)
        valor_rep = _money(contrato.valor_repasse_total or _ZERO)
        valor_com = _money(contrato.valor_comissao or _ZERO)
        margem = _money(contrato.valor_margem or (valor_final - valor_rep))

        contrato_forn = None
        prazo = 30
        if contrato.contrato_fornecedor_id:
            contrato_forn = await self.get_contrato_fornecedor(contrato.contrato_fornecedor_id)
            prazo = contrato_forn.prazo_pagamento_dias

        vencimento = date.today() + timedelta(days=prazo)
        receber_svc = ContaReceberService(self.session)
        conta_receber = await receber_svc.from_origem(
            contrato.tenant_id,
            origem=ContaReceberOrigem.CONTRATO,
            origem_id=contrato.id,
            cliente_id=contrato.cliente_id,
            filial_id=contrato.filial_retirada_id,
            valor=valor_final,
            descricao=f"Locação {contrato.numero}",
            vencimento=vencimento,
        )

        conta_pagar = None
        pagar_svc = ContaPagarService(self.session)
        if contrato.modelo_negocio_terceiro == ModeloNegocioTerceiro.REPASSE and valor_rep > _ZERO:
            from app.modules.financeiro.schemas import ContaPagarCreate

            conta_pagar = await pagar_svc.create(
                contrato.tenant_id,
                ContaPagarCreate(
                    fornecedor_id=contrato.fornecedor_id,
                    filial_id=contrato.filial_retirada_id,
                    descricao=f"Repasse locação {contrato.numero}",
                    valor_original=valor_rep,
                    vencimento=vencimento,
                    origem=ContaPagarOrigem.REPASSE_LOCACAO,
                    origem_id=contrato.id,
                ),
            )
        elif (
            contrato.modelo_negocio_terceiro == ModeloNegocioTerceiro.COMISSAO
            and valor_com > _ZERO
        ):
            from app.modules.financeiro.schemas import ContaPagarCreate

            conta_pagar = await pagar_svc.create(
                contrato.tenant_id,
                ContaPagarCreate(
                    fornecedor_id=contrato.fornecedor_id,
                    filial_id=contrato.filial_retirada_id,
                    descricao=f"Comissão locação {contrato.numero}",
                    valor_original=valor_com,
                    vencimento=vencimento,
                    origem=ContaPagarOrigem.COMISSAO,
                    origem_id=contrato.id,
                ),
            )

        lanc = LocRepasseLancamento(
            tenant_id=contrato.tenant_id,
            contrato_id=contrato.id,
            reserva_id=contrato.reserva_id,
            fornecedor_id=contrato.fornecedor_id,
            contrato_fornecedor_id=contrato.contrato_fornecedor_id,
            modelo_negocio=contrato.modelo_negocio_terceiro or ModeloNegocioTerceiro.REPASSE,
            valor_cliente=valor_final,
            valor_repasse=valor_rep,
            valor_margem=margem,
            valor_comissao=valor_com,
            conta_pagar_id=conta_pagar.id if conta_pagar else None,
            conta_receber_id=conta_receber.id,
            vencimento=vencimento,
            status=TituloStatus.EM_ABERTO,
            repasse_snapshot=contrato.repasse_snapshot or "{}",
        )
        self.repasse_repo.add(lanc)
        await self.repasse_repo.flush()
        return lanc

    async def _resolver_preco_tabela(
        self,
        contrato_id: uuid.UUID,
        *,
        categoria_id: uuid.UUID,
        filial_id: uuid.UUID | None,
        ref_date: date,
        dias: int,
    ) -> FornecedorContratoPreco | None:
        stmt = select(FornecedorContratoPreco).where(
            FornecedorContratoPreco.contrato_fornecedor_id == contrato_id,
            FornecedorContratoPreco.deleted_at.is_(None),
            FornecedorContratoPreco.vigencia_inicio <= ref_date,
            or_(
                FornecedorContratoPreco.vigencia_fim.is_(None),
                FornecedorContratoPreco.vigencia_fim >= ref_date,
            ),
            FornecedorContratoPreco.dias_minimos <= dias,
            or_(
                FornecedorContratoPreco.dias_maximos.is_(None),
                FornecedorContratoPreco.dias_maximos >= dias,
            ),
        )
        rows = list((await self.session.execute(stmt)).scalars().all())
        if not rows:
            return None

        def score(p: FornecedorContratoPreco) -> tuple[int, int]:
            s = p.prioridade
            if p.categoria_id == categoria_id:
                s += 100
            if filial_id and p.filial_id == filial_id:
                s += 50
            elif p.filial_id is None:
                s += 10
            return (s, p.prioridade)

        return max(rows, key=score)

    async def _get_fornecedor(self, fornecedor_id: uuid.UUID) -> Fornecedor:
        stmt = select(Fornecedor).where(
            Fornecedor.id == fornecedor_id,
            Fornecedor.deleted_at.is_(None),
        )
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if row is None:
            raise ValidationError("Fornecedor não encontrado.")
        return row

    async def _get_veiculo(self, veiculo_id: uuid.UUID) -> FrotaVeiculo:
        stmt = select(FrotaVeiculo).where(
            FrotaVeiculo.id == veiculo_id,
            FrotaVeiculo.deleted_at.is_(None),
        )
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if row is None:
            raise ValidationError("Veículo não encontrado.")
        return row

    async def list_locadoras_parceiras(self, tenant_id: uuid.UUID) -> list[Fornecedor]:
        stmt = (
            select(Fornecedor)
            .where(
                Fornecedor.tenant_id == tenant_id,
                Fornecedor.deleted_at.is_(None),
                Fornecedor.locadora_parceira.is_(True),
                Fornecedor.status == CadastroStatus.ACTIVE,
            )
            .order_by(Fornecedor.nome)
        )
        return list((await self.session.execute(stmt)).scalars().all())
