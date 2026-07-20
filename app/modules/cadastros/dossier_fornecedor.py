"""Contexto da tela Dossiê do fornecedor operacional."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.cadastros.models_extra import Fornecedor
from app.modules.cadastros.repository import TabelaAuxiliarRepository
from app.modules.cadastros.service_extra import FornecedorService
from app.modules.financeiro.models import FinContaPagar
from app.modules.fiscal.models import FisXmlArquivo
from app.modules.frota.models import FrotaVeiculo
from app.modules.intermediacao.models import FornecedorContratoLocacao, LocRepasseLancamento
from app.modules.manutencao.models import ManOrdemServico
from app.shared.enums import FiscalXmlDirecao, OrdemServicoStatus, TituloStatus
from app.shared.value_objects import only_digits


@dataclass
class FornecedorDossier:
    fornecedor: Fornecedor
    categoria_label: str | None = None
    stats: dict[str, int | Decimal] = field(default_factory=dict)
    ordens_recentes: list[ManOrdemServico] = field(default_factory=list)
    contratos_intermediacao: list[FornecedorContratoLocacao] = field(default_factory=list)
    titulos_recentes: list[FinContaPagar] = field(default_factory=list)
    xml_recentes: list[FisXmlArquivo] = field(default_factory=list)
    veiculos_terceiros: list[FrotaVeiculo] = field(default_factory=list)
    repasses_recentes: list[LocRepasseLancamento] = field(default_factory=list)


async def build_fornecedor_dossier(
    session: AsyncSession, fornecedor_id: uuid.UUID
) -> FornecedorDossier:
    fornecedor = await FornecedorService(session).get(fornecedor_id)
    fid = fornecedor_id

    categoria_label = None
    if fornecedor.categoria_codigo:
        item = await TabelaAuxiliarRepository(session).get_by_grupo_codigo(
            "categoria_fornecedor", fornecedor.categoria_codigo
        )
        categoria_label = item.descricao if item else fornecedor.categoria_codigo

    os_abertas_status = (
        OrdemServicoStatus.ABERTA,
        OrdemServicoStatus.AGUARDANDO_PECA,
        OrdemServicoStatus.EM_EXECUCAO,
        OrdemServicoStatus.AGUARDANDO_APROVACAO,
    )

    total_os = (
        await session.execute(
            select(func.count())
            .select_from(ManOrdemServico)
            .where(ManOrdemServico.fornecedor_id == fid, ManOrdemServico.deleted_at.is_(None))
        )
    ).scalar_one() or 0

    os_abertas = (
        await session.execute(
            select(func.count())
            .select_from(ManOrdemServico)
            .where(
                ManOrdemServico.fornecedor_id == fid,
                ManOrdemServico.deleted_at.is_(None),
                ManOrdemServico.status.in_(os_abertas_status),
            )
        )
    ).scalar_one() or 0

    custo_manutencao = (
        await session.execute(
            select(func.coalesce(func.sum(ManOrdemServico.custo_total), 0))
            .select_from(ManOrdemServico)
            .where(ManOrdemServico.fornecedor_id == fid, ManOrdemServico.deleted_at.is_(None))
        )
    ).scalar_one() or Decimal("0")

    total_contratos = (
        await session.execute(
            select(func.count())
            .select_from(FornecedorContratoLocacao)
            .where(
                FornecedorContratoLocacao.fornecedor_id == fid,
                FornecedorContratoLocacao.deleted_at.is_(None),
            )
        )
    ).scalar_one() or 0

    titulos_pendentes = (
        await session.execute(
            select(func.count())
            .select_from(FinContaPagar)
            .where(
                FinContaPagar.fornecedor_id == fid,
                FinContaPagar.deleted_at.is_(None),
                FinContaPagar.status.in_(
                    (TituloStatus.EM_ABERTO, TituloStatus.VENCIDO, TituloStatus.PAGO_PARCIAL)
                ),
            )
        )
    ).scalar_one() or 0

    saldo_pagar = (
        await session.execute(
            select(func.coalesce(func.sum(FinContaPagar.valor_saldo), 0))
            .select_from(FinContaPagar)
            .where(
                FinContaPagar.fornecedor_id == fid,
                FinContaPagar.deleted_at.is_(None),
                FinContaPagar.status.in_(
                    (TituloStatus.EM_ABERTO, TituloStatus.VENCIDO, TituloStatus.PAGO_PARCIAL)
                ),
            )
        )
    ).scalar_one() or Decimal("0")

    veiculos_count = (
        await session.execute(
            select(func.count())
            .select_from(FrotaVeiculo)
            .where(FrotaVeiculo.fornecedor_id == fid, FrotaVeiculo.deleted_at.is_(None))
        )
    ).scalar_one() or 0

    repasse_pendente = (
        await session.execute(
            select(func.coalesce(func.sum(LocRepasseLancamento.valor_repasse), 0))
            .select_from(LocRepasseLancamento)
            .where(
                LocRepasseLancamento.fornecedor_id == fid,
                LocRepasseLancamento.deleted_at.is_(None),
                LocRepasseLancamento.status.in_(
                    (TituloStatus.EM_ABERTO, TituloStatus.VENCIDO, TituloStatus.PAGO_PARCIAL)
                ),
            )
        )
    ).scalar_one() or Decimal("0")

    ordens_recentes = list(
        (
            await session.execute(
                select(ManOrdemServico)
                .where(ManOrdemServico.fornecedor_id == fid, ManOrdemServico.deleted_at.is_(None))
                .order_by(ManOrdemServico.created_at.desc())
                .limit(8)
            )
        ).scalars().all()
    )

    contratos_intermediacao = list(
        (
            await session.execute(
                select(FornecedorContratoLocacao)
                .where(
                    FornecedorContratoLocacao.fornecedor_id == fid,
                    FornecedorContratoLocacao.deleted_at.is_(None),
                )
                .order_by(FornecedorContratoLocacao.vigencia_inicio.desc())
                .limit(12)
            )
        ).scalars().all()
    )

    titulos_recentes = list(
        (
            await session.execute(
                select(FinContaPagar)
                .where(FinContaPagar.fornecedor_id == fid, FinContaPagar.deleted_at.is_(None))
                .order_by(FinContaPagar.vencimento.desc())
                .limit(8)
            )
        ).scalars().all()
    )

    xml_recentes: list[FisXmlArquivo] = []
    cnpj_digits = only_digits(fornecedor.cnpj) if fornecedor.cnpj else None
    if cnpj_digits:
        xml_recentes = list(
            (
                await session.execute(
                    select(FisXmlArquivo)
                    .where(
                        FisXmlArquivo.deleted_at.is_(None),
                        FisXmlArquivo.direcao == FiscalXmlDirecao.RECEBIDO,
                        or_(
                            FisXmlArquivo.fornecedor_cnpj == cnpj_digits,
                            FisXmlArquivo.fornecedor_cnpj == fornecedor.cnpj,
                        ),
                    )
                    .order_by(FisXmlArquivo.created_at.desc())
                    .limit(8)
                )
            ).scalars().all()
        )

    veiculos_terceiros = list(
        (
            await session.execute(
                select(FrotaVeiculo)
                .where(FrotaVeiculo.fornecedor_id == fid, FrotaVeiculo.deleted_at.is_(None))
                .order_by(FrotaVeiculo.placa.asc())
                .limit(12)
            )
        ).scalars().all()
    )

    repasses_recentes = list(
        (
            await session.execute(
                select(LocRepasseLancamento)
                .where(
                    LocRepasseLancamento.fornecedor_id == fid,
                    LocRepasseLancamento.deleted_at.is_(None),
                )
                .order_by(LocRepasseLancamento.created_at.desc())
                .limit(8)
            )
        ).scalars().all()
    )

    return FornecedorDossier(
        fornecedor=fornecedor,
        categoria_label=categoria_label,
        stats={
            "ordens_servico": int(total_os),
            "os_abertas": int(os_abertas),
            "custo_manutencao": custo_manutencao,
            "contratos_intermediacao": int(total_contratos),
            "titulos_pendentes": int(titulos_pendentes),
            "saldo_pagar": saldo_pagar,
            "veiculos_terceiros": int(veiculos_count),
            "repasse_pendente": repasse_pendente,
            "xml_importados": len(xml_recentes),
        },
        ordens_recentes=ordens_recentes,
        contratos_intermediacao=contratos_intermediacao,
        titulos_recentes=titulos_recentes,
        xml_recentes=xml_recentes,
        veiculos_terceiros=veiculos_terceiros,
        repasses_recentes=repasses_recentes,
    )
