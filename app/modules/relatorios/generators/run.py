"""Geradores de dados analíticos (§11) — consultas reais ao banco."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.financeiro.models import (
    FinCaixaLancamento,
    FinContaPagar,
    FinContaReceber,
    FinExtratoLinha,
)
from app.modules.fiscal.models import FisCancelamento, FisNfe, FisNfse
from app.modules.frota.models import FrotaCategoria, FrotaDocumento, FrotaVeiculo
from app.modules.locacoes.models import LocAvaria, LocContrato, LocContratoAditivo, LocMulta
from app.modules.relatorios.data import ReportData
from app.modules.reservas.models import ResReserva
from app.modules.tenants.models import Filial
from app.shared.enums import (
    CancelamentoStatus,
    ContaPagarOrigem,
    ContratoStatus,
    DocumentoVeiculoStatus,
    NfeStatus,
    NfseStatus,
    OrdemServicoStatus,
    ReservaStatus,
    TituloStatus,
)

# Import tardio para evitar ciclo no carregamento do pacote.
from app.modules.manutencao.models import ManOrdemServico  # noqa: E402


def _parse_params(params: dict[str, Any]) -> tuple[date, date, uuid.UUID | None]:
    ini = params.get("periodo_inicio")
    fim = params.get("periodo_fim")
    if isinstance(ini, str):
        ini = date.fromisoformat(ini)
    if isinstance(fim, str):
        fim = date.fromisoformat(fim)
    if not ini or not fim:
        fim = date.today()
        ini = fim - timedelta(days=30)
    filial_raw = params.get("filial_id")
    filial_id = uuid.UUID(str(filial_raw)) if filial_raw else None
    return ini, fim, filial_id


def _dt_start(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=UTC)


def _dt_end(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=UTC)


def _dec(v: Any) -> Decimal:
    if v is None:
        return Decimal("0")
    return Decimal(str(v))


def _apply_columns(data: ReportData, params: dict[str, Any]) -> ReportData:
    cols = params.get("colunas") or params.get("colunas_selecionadas")
    if not cols:
        return data
    selected = [c for c in cols if c in data.columns]
    if not selected:
        return data
    idx = [data.columns.index(c) for c in selected]
    return ReportData(
        titulo=data.titulo,
        columns=selected,
        rows=[[row[i] for i in idx] for row in data.rows],
        summary=data.summary,
    )


async def gerar(
    session: AsyncSession,
    codigo: str,
    params: dict[str, Any],
) -> ReportData:
    fn = _GENERATORS.get(codigo)
    if fn is None:
        raise ValueError(f"Relatório desconhecido: {codigo}")
    data = await fn(session, params)
    return _apply_columns(data, params)


# ------------------------------------------------------------------ §11.1 Frota
async def _frota_atual(session: AsyncSession, params: dict) -> ReportData:
    _, _, filial_id = _parse_params(params)
    stmt = (
        select(
            FrotaVeiculo.status,
            Filial.name,
            FrotaCategoria.nome,
            func.count(),
        )
        .join(Filial, FrotaVeiculo.filial_id == Filial.id, isouter=True)
        .join(FrotaCategoria, FrotaVeiculo.categoria_id == FrotaCategoria.id)
        .where(FrotaVeiculo.deleted_at.is_(None))
        .group_by(FrotaVeiculo.status, Filial.name, FrotaCategoria.nome)
    )
    if filial_id:
        stmt = stmt.where(FrotaVeiculo.filial_id == filial_id)
    rows = [
        [r[0].value if hasattr(r[0], "value") else r[0], r[1] or "—", r[2], r[3]]
        for r in (await session.execute(stmt)).all()
    ]
    return ReportData(
        "Frota atual",
        ["status", "filial", "categoria", "quantidade"],
        rows,
        {"total": sum(r[3] for r in rows)},
    )


async def _rentabilidade_veiculo(session: AsyncSession, params: dict) -> ReportData:
    ini, fim, filial_id = _parse_params(params)
    rec_stmt = (
        select(
            LocContrato.veiculo_id,
            func.coalesce(func.sum(LocContrato.valor_final), 0),
        )
        .where(
            LocContrato.deleted_at.is_(None),
            LocContrato.status.in_([ContratoStatus.ENCERRADO, ContratoStatus.ENCERRADO_PENDENCIA]),
            LocContrato.checkin_em >= _dt_start(ini),
            LocContrato.checkin_em <= _dt_end(fim),
        )
        .group_by(LocContrato.veiculo_id)
    )
    if filial_id:
        rec_stmt = rec_stmt.where(LocContrato.filial_retirada_id == filial_id)
    receitas = {r[0]: _dec(r[1]) for r in (await session.execute(rec_stmt)).all()}

    os_stmt = (
        select(
            ManOrdemServico.veiculo_id,
            func.coalesce(func.sum(ManOrdemServico.custo_total), 0),
        )
        .where(
            ManOrdemServico.deleted_at.is_(None),
            ManOrdemServico.status == OrdemServicoStatus.CONCLUIDA,
            ManOrdemServico.data_conclusao >= ini,
            ManOrdemServico.data_conclusao <= fim,
        )
        .group_by(ManOrdemServico.veiculo_id)
    )
    custos = {r[0]: _dec(r[1]) for r in (await session.execute(os_stmt)).all()}
    veic_ids = set(receitas) | set(custos)
    if not veic_ids:
        return ReportData("Rentabilidade por veículo", ["placa", "receita", "custo_manutencao", "margem"], [])

    v_stmt = select(FrotaVeiculo.id, FrotaVeiculo.placa).where(FrotaVeiculo.id.in_(veic_ids))
    placas = {r[0]: r[1] for r in (await session.execute(v_stmt)).all()}
    rows = []
    for vid in veic_ids:
        rec = receitas.get(vid, Decimal("0"))
        cust = custos.get(vid, Decimal("0"))
        rows.append([placas.get(vid, str(vid)), rec, cust, rec - cust])
    return ReportData(
        "Rentabilidade por veículo",
        ["placa", "receita", "custo_manutencao", "margem"],
        rows,
    )


async def _ociosidade_ocupacao(session: AsyncSession, params: dict) -> ReportData:
    ini, fim, filial_id = _parse_params(params)
    dias_periodo = max((fim - ini).days + 1, 1)
    stmt = select(FrotaVeiculo.id, FrotaVeiculo.placa, FrotaCategoria.nome).join(
        FrotaCategoria, FrotaVeiculo.categoria_id == FrotaCategoria.id
    ).where(FrotaVeiculo.deleted_at.is_(None))
    if filial_id:
        stmt = stmt.where(FrotaVeiculo.filial_id == filial_id)
    veiculos = list((await session.execute(stmt)).all())
    rows = []
    for vid, placa, cat in veiculos:
        c_stmt = select(func.count()).where(
            LocContrato.veiculo_id == vid,
            LocContrato.deleted_at.is_(None),
            LocContrato.status.in_(
                [ContratoStatus.ATIVO, ContratoStatus.ENCERRADO, ContratoStatus.ENCERRADO_PENDENCIA]
            ),
            LocContrato.checkout_em <= _dt_end(fim),
            func.coalesce(LocContrato.checkin_em, _dt_end(fim)) >= _dt_start(ini),
        )
        dias_loc = (await session.execute(c_stmt)).scalar_one() or 0
        dias_loc = min(dias_loc * 3, dias_periodo)  # proxy: contratos * média 3 dias
        taxa = round(dias_loc / dias_periodo * 100, 1)
        rows.append([placa, cat, dias_loc, dias_periodo - dias_loc, f"{taxa}%"])
    return ReportData(
        "Ociosidade / ocupação",
        ["placa", "categoria", "dias_locados", "dias_disponiveis", "taxa_ocupacao"],
        rows,
    )


async def _tco_veiculo(session: AsyncSession, params: dict) -> ReportData:
    _, _, filial_id = _parse_params(params)
    stmt = select(
        FrotaVeiculo.placa,
        FrotaVeiculo.valor_aquisicao,
        FrotaVeiculo.id,
    ).where(FrotaVeiculo.deleted_at.is_(None))
    if filial_id:
        stmt = stmt.where(FrotaVeiculo.filial_id == filial_id)
    rows_out = []
    for placa, vaq, vid in (await session.execute(stmt)).all():
        os_stmt = select(func.coalesce(func.sum(ManOrdemServico.custo_total), 0)).where(
            ManOrdemServico.veiculo_id == vid,
            ManOrdemServico.status == OrdemServicoStatus.CONCLUIDA,
            ManOrdemServico.deleted_at.is_(None),
        )
        cust = _dec((await session.execute(os_stmt)).scalar_one())
        aquis = _dec(vaq)
        rows_out.append([placa, aquis, cust, aquis + cust])
    return ReportData("TCO por veículo", ["placa", "valor_aquisicao", "custo_manutencao", "tco"], rows_out)


async def _idade_media_frota(session: AsyncSession, params: dict) -> ReportData:
    ano_atual = date.today().year
    stmt = (
        select(
            Filial.name,
            FrotaCategoria.nome,
            func.avg(ano_atual - FrotaVeiculo.ano_fabricacao),
            func.count(),
        )
        .join(Filial, FrotaVeiculo.filial_id == Filial.id, isouter=True)
        .join(FrotaCategoria, FrotaVeiculo.categoria_id == FrotaCategoria.id)
        .where(FrotaVeiculo.deleted_at.is_(None))
        .group_by(Filial.name, FrotaCategoria.nome)
    )
    rows = [
        [r[0] or "—", r[1], round(float(r[2] or 0), 1), r[3]]
        for r in (await session.execute(stmt)).all()
    ]
    return ReportData("Idade média da frota", ["filial", "categoria", "idade_media_anos", "quantidade"], rows)


async def _vencimentos_documentacao(session: AsyncSession, params: dict) -> ReportData:
    ini, fim, _ = _parse_params(params)
    dias = int(params.get("dias_vencimento", 30))
    limite = fim + timedelta(days=dias)
    stmt = (
        select(
            FrotaVeiculo.placa,
            FrotaDocumento.tipo,
            FrotaDocumento.data_validade,
            FrotaDocumento.status,
        )
        .join(FrotaVeiculo, FrotaDocumento.veiculo_id == FrotaVeiculo.id)
        .where(
            FrotaDocumento.deleted_at.is_(None),
            FrotaDocumento.data_validade.isnot(None),
            FrotaDocumento.data_validade <= limite,
            FrotaDocumento.data_validade >= ini,
        )
        .order_by(FrotaDocumento.data_validade)
    )
    rows = [
        [
            r[0],
            r[1].value if hasattr(r[1], "value") else r[1],
            r[2].isoformat() if r[2] else "—",
            r[3].value if hasattr(r[3], "value") else r[3],
        ]
        for r in (await session.execute(stmt)).all()
    ]
    return ReportData(
        "Vencimentos de documentação",
        ["placa", "tipo", "vencimento", "status"],
        rows,
    )


# ------------------------------------------------------------------ §11.2 Locação
async def _contratos_periodo(session: AsyncSession, params: dict) -> ReportData:
    ini, fim, filial_id = _parse_params(params)
    stmt = (
        select(
            LocContrato.numero,
            LocContrato.status,
            Filial.name,
            LocContrato.cliente_id,
            LocContrato.valor_final,
            LocContrato.retirada_prevista_em,
        )
        .join(Filial, LocContrato.filial_retirada_id == Filial.id, isouter=True)
        .where(
            LocContrato.deleted_at.is_(None),
            LocContrato.created_at >= _dt_start(ini),
            LocContrato.created_at <= _dt_end(fim),
        )
        .order_by(LocContrato.created_at.desc())
        .limit(500)
    )
    if filial_id:
        stmt = stmt.where(LocContrato.filial_retirada_id == filial_id)
    rows = [
        [
            r[0],
            r[1].value,
            r[2] or "—",
            str(r[3])[:8],
            r[4],
            r[5].strftime("%d/%m/%Y") if r[5] else "—",
        ]
        for r in (await session.execute(stmt)).all()
    ]
    return ReportData("Contratos por período", ["numero", "status", "filial", "cliente", "valor_final", "retirada"], rows)


async def _ticket_medio(session: AsyncSession, params: dict) -> ReportData:
    ini, fim, filial_id = _parse_params(params)
    stmt = (
        select(Filial.name, func.count(), func.avg(LocContrato.valor_final))
        .join(Filial, LocContrato.filial_retirada_id == Filial.id, isouter=True)
        .where(
            LocContrato.deleted_at.is_(None),
            LocContrato.status.in_([ContratoStatus.ENCERRADO, ContratoStatus.ENCERRADO_PENDENCIA]),
            LocContrato.checkin_em >= _dt_start(ini),
            LocContrato.checkin_em <= _dt_end(fim),
        )
        .group_by(Filial.name)
    )
    if filial_id:
        stmt = stmt.where(LocContrato.filial_retirada_id == filial_id)
    rows = [[r[0] or "—", r[1], round(float(r[2] or 0), 2)] for r in (await session.execute(stmt)).all()]
    return ReportData("Ticket médio", ["filial", "contratos", "ticket_medio"], rows)


async def _tempo_medio_locacao(session: AsyncSession, params: dict) -> ReportData:
    ini, fim, filial_id = _parse_params(params)
    stmt = (
        select(
            Filial.name,
            func.count(),
            func.avg(
                func.extract("epoch", LocContrato.checkin_em - LocContrato.checkout_em) / 86400
            ),
        )
        .join(Filial, LocContrato.filial_retirada_id == Filial.id, isouter=True)
        .where(
            LocContrato.checkout_em.isnot(None),
            LocContrato.checkin_em.isnot(None),
            LocContrato.checkin_em >= _dt_start(ini),
            LocContrato.checkin_em <= _dt_end(fim),
        )
        .group_by(Filial.name)
    )
    if filial_id:
        stmt = stmt.where(LocContrato.filial_retirada_id == filial_id)
    rows = [[r[0] or "—", r[1], round(float(r[2] or 0), 1)] for r in (await session.execute(stmt)).all()]
    return ReportData("Tempo médio de locação", ["filial", "contratos", "dias_medio"], rows)


async def _taxa_renovacao(session: AsyncSession, params: dict) -> ReportData:
    ini, fim, filial_id = _parse_params(params)
    base = select(func.count()).select_from(LocContrato).where(
        LocContrato.deleted_at.is_(None),
        LocContrato.created_at >= _dt_start(ini),
        LocContrato.created_at <= _dt_end(fim),
    )
    if filial_id:
        base = base.where(LocContrato.filial_retirada_id == filial_id)
    total = (await session.execute(base)).scalar_one() or 0
    ren = select(func.count()).select_from(LocContratoAditivo).where(
        LocContratoAditivo.deleted_at.is_(None),
        LocContratoAditivo.created_at >= _dt_start(ini),
        LocContratoAditivo.created_at <= _dt_end(fim),
    )
    renov = (await session.execute(ren)).scalar_one() or 0
    taxa = round(renov / total * 100, 1) if total else 0
    return ReportData(
        "Taxa de renovação",
        ["filial", "contratos_base", "renovacoes", "taxa_pct"],
        [["Todas", total, renov, f"{taxa}%"]],
    )


async def _taxa_no_show_cancelamento(session: AsyncSession, params: dict) -> ReportData:
    ini, fim, _ = _parse_params(params)
    stmt = (
        select(
            ResReserva.origem,
            func.count(),
            func.sum(case((ResReserva.status == ReservaStatus.NO_SHOW, 1), else_=0)),
            func.sum(case((ResReserva.status == ReservaStatus.CANCELADA, 1), else_=0)),
        )
        .where(
            ResReserva.deleted_at.is_(None),
            ResReserva.created_at >= _dt_start(ini),
            ResReserva.created_at <= _dt_end(fim),
        )
        .group_by(ResReserva.origem)
    )
    rows = []
    for orig, tot, ns, can in (await session.execute(stmt)).all():
        taxa = round(((ns or 0) + (can or 0)) / tot * 100, 1) if tot else 0
        rows.append([orig.value, tot, ns or 0, can or 0, f"{taxa}%"])
    return ReportData(
        "No-show e cancelamentos",
        ["origem", "total", "no_show", "canceladas", "taxa_pct"],
        rows,
    )


async def _ranking_clientes(session: AsyncSession, params: dict) -> ReportData:
    ini, fim, _ = _parse_params(params)
    stmt = (
        select(
            LocContrato.cliente_id,
            func.count(),
            func.sum(LocContrato.valor_final),
        )
        .where(
            LocContrato.deleted_at.is_(None),
            LocContrato.created_at >= _dt_start(ini),
            LocContrato.created_at <= _dt_end(fim),
        )
        .group_by(LocContrato.cliente_id)
        .order_by(func.sum(LocContrato.valor_final).desc())
        .limit(50)
    )
    rows = [[str(r[0])[:8], r[1], r[2]] for r in (await session.execute(stmt)).all()]
    return ReportData("Ranking de clientes", ["cliente", "contratos", "receita_total"], rows)


async def _avarias_responsabilizacao(session: AsyncSession, params: dict) -> ReportData:
    ini, fim, _ = _parse_params(params)
    stmt = (
        select(
            LocAvaria.responsabilidade,
            LocAvaria.status,
            func.count(),
            func.coalesce(func.sum(LocAvaria.valor_reparo), 0),
        )
        .where(
            LocAvaria.deleted_at.is_(None),
            LocAvaria.created_at >= _dt_start(ini),
            LocAvaria.created_at <= _dt_end(fim),
        )
        .group_by(LocAvaria.responsabilidade, LocAvaria.status)
    )
    rows = [
        [
            r[0].value if r[0] else "—",
            r[1].value,
            r[2],
            r[3],
        ]
        for r in (await session.execute(stmt)).all()
    ]
    return ReportData(
        "Avarias e responsabilização",
        ["responsabilidade", "status", "quantidade", "valor_estimado"],
        rows,
    )


async def _multas_relatorio(session: AsyncSession, params: dict) -> ReportData:
    ini, fim, _ = _parse_params(params)
    stmt = (
        select(
            LocMulta.status,
            func.count(),
            func.coalesce(func.sum(LocMulta.valor), 0),
            func.coalesce(func.sum(LocMulta.valor + LocMulta.taxa_admin), 0),
        )
        .where(
            LocMulta.deleted_at.is_(None),
            LocMulta.created_at >= _dt_start(ini),
            LocMulta.created_at <= _dt_end(fim),
        )
        .group_by(LocMulta.status)
    )
    rows = [[r[0].value, r[1], r[2], r[3]] for r in (await session.execute(stmt)).all()]
    return ReportData("Multas e infrações", ["status", "quantidade", "valor_total", "valor_repassado"], rows)


# ---------------------------------------------------------------- §11.3 Financeiro
async def _dre_simplificado(session: AsyncSession, params: dict) -> ReportData:
    ini, fim, _ = _parse_params(params)
    rec = select(func.coalesce(func.sum(FinContaReceber.valor_pago), 0)).where(
        FinContaReceber.deleted_at.is_(None),
        FinContaReceber.updated_at >= _dt_start(ini),
        FinContaReceber.updated_at <= _dt_end(fim),
        FinContaReceber.status == TituloStatus.PAGO,
    )
    receita = _dec((await session.execute(rec)).scalar_one())
    pag = select(func.coalesce(func.sum(FinContaPagar.valor_pago), 0)).where(
        FinContaPagar.deleted_at.is_(None),
        FinContaPagar.updated_at >= _dt_start(ini),
        FinContaPagar.updated_at <= _dt_end(fim),
        FinContaPagar.status == TituloStatus.PAGO,
    )
    despesas = _dec((await session.execute(pag)).scalar_one())
    os_c = select(func.coalesce(func.sum(ManOrdemServico.custo_total), 0)).where(
        ManOrdemServico.status == OrdemServicoStatus.CONCLUIDA,
        ManOrdemServico.data_conclusao >= ini,
        ManOrdemServico.data_conclusao <= fim,
    )
    custos = _dec((await session.execute(os_c)).scalar_one())
    rows = [
        ["Receita (CR pago)", receita],
        ["Despesas (CP pago)", -despesas],
        ["Custos OS", -custos],
        ["Resultado", receita - despesas - custos],
    ]
    return ReportData("DRE simplificado", ["conta", "valor"], rows)


async def _fluxo_caixa(session: AsyncSession, params: dict) -> ReportData:
    ini, fim, _ = _parse_params(params)
    stmt = (
        select(
            func.date(FinCaixaLancamento.created_at),
            func.sum(case((FinCaixaLancamento.tipo.in_(["entrada", "suprimento"]), FinCaixaLancamento.valor), else_=0)),
            func.sum(case((FinCaixaLancamento.tipo.in_(["saida", "sangria"]), FinCaixaLancamento.valor), else_=0)),
        )
        .where(
            FinCaixaLancamento.deleted_at.is_(None),
            FinCaixaLancamento.created_at >= _dt_start(ini),
            FinCaixaLancamento.created_at <= _dt_end(fim),
        )
        .group_by(func.date(FinCaixaLancamento.created_at))
        .order_by(func.date(FinCaixaLancamento.created_at))
    )
    rows = []
    saldo = Decimal("0")
    for d, ent, sai in (await session.execute(stmt)).all():
        ent, sai = _dec(ent), _dec(sai)
        saldo += ent - sai
        rows.append([str(d), ent, sai, saldo])
    return ReportData("Fluxo de caixa", ["data", "entradas", "saidas", "saldo_dia"], rows)


async def _inadimplencia_aging(session: AsyncSession, params: dict) -> ReportData:
    from app.modules.financeiro.service import ContaReceberService

    svc = ContaReceberService(session)
    buckets = await svc.aging()
    rows = [[b["bucket"], b["quantidade"], b["total"]] for b in buckets]
    return ReportData("Inadimplência (aging)", ["faixa", "quantidade", "valor"], rows)


async def _faturamento_segmento(session: AsyncSession, params: dict) -> ReportData:
    ini, fim, _ = _parse_params(params)
    stmt = (
        select(Filial.name, func.count(), func.coalesce(func.sum(LocContrato.valor_final), 0))
        .join(Filial, LocContrato.filial_retirada_id == Filial.id, isouter=True)
        .where(
            LocContrato.deleted_at.is_(None),
            LocContrato.checkin_em >= _dt_start(ini),
            LocContrato.checkin_em <= _dt_end(fim),
        )
        .group_by(Filial.name)
    )
    rows = [[r[0] or "—", r[1], r[2]] for r in (await session.execute(stmt)).all()]
    return ReportData("Faturamento por filial", ["filial", "contratos", "receita"], rows)


async def _comissoes_pagas(session: AsyncSession, params: dict) -> ReportData:
    ini, fim, _ = _parse_params(params)
    stmt = (
        select(
            FinContaPagar.beneficiario_nome,
            FinContaPagar.valor_original,
            FinContaPagar.vencimento,
            FinContaPagar.status,
        )
        .where(
            FinContaPagar.deleted_at.is_(None),
            FinContaPagar.origem == ContaPagarOrigem.COMISSAO,
            FinContaPagar.created_at >= _dt_start(ini),
            FinContaPagar.created_at <= _dt_end(fim),
        )
    )
    rows = [[r[0] or "—", r[1], r[2].isoformat(), r[3].value] for r in (await session.execute(stmt)).all()]
    return ReportData("Comissões pagas", ["beneficiario", "valor", "vencimento", "status"], rows)


async def _conciliacao_resumo(session: AsyncSession, params: dict) -> ReportData:
    stmt = (
        select(
            FinExtratoLinha.conta_id,
            func.sum(case((FinExtratoLinha.status_conciliacao == "conciliado", 1), else_=0)),
            func.sum(case((FinExtratoLinha.status_conciliacao == "pendente", 1), else_=0)),
            func.sum(case((FinExtratoLinha.status_conciliacao == "divergente", 1), else_=0)),
        )
        .where(FinExtratoLinha.deleted_at.is_(None))
        .group_by(FinExtratoLinha.conta_id)
    )
    rows = [[str(r[0])[:8], r[1], r[2], r[3]] for r in (await session.execute(stmt)).all()]
    return ReportData("Conciliação bancária", ["conta", "conciliado", "pendente", "divergente"], rows)


# ------------------------------------------------------------------- §11.4 Fiscal
async def _notas_periodo(session: AsyncSession, params: dict) -> ReportData:
    ini, fim, _ = _parse_params(params)
    nfse = (
        select(FisNfse.status, func.count(), func.coalesce(func.sum(FisNfse.valor_servico), 0))
        .where(
            FisNfse.deleted_at.is_(None),
            FisNfse.created_at >= _dt_start(ini),
            FisNfse.created_at <= _dt_end(fim),
        )
        .group_by(FisNfse.status)
    )
    rows = [["NFS-e", r[0].value, r[1], r[2]] for r in (await session.execute(nfse)).all()]
    nfe = (
        select(FisNfe.status, func.count(), func.coalesce(func.sum(FisNfe.valor_total), 0))
        .where(
            FisNfe.deleted_at.is_(None),
            FisNfe.created_at >= _dt_start(ini),
            FisNfe.created_at <= _dt_end(fim),
        )
        .group_by(FisNfe.status)
    )
    rows += [["NF-e", r[0].value, r[1], r[2]] for r in (await session.execute(nfe)).all()]
    return ReportData("Notas emitidas/canceladas", ["tipo", "status", "quantidade", "valor_total"], rows)


async def _apuracao_impostos(session: AsyncSession, params: dict) -> ReportData:
    from app.modules.fiscal.service import ImpostoService

    ini, fim, _ = _parse_params(params)
    ap = await ImpostoService(session).apuracao(ini, fim)
    rows = [[a.get("tipo", ""), a.get("base_calculo", 0), a.get("valor_imposto", 0)] for a in ap]
    return ReportData("Apuração de impostos", ["imposto", "base_calculo", "valor"], rows)


async def _export_contabilidade(session: AsyncSession, params: dict) -> ReportData:
    ini, fim, _ = _parse_params(params)
    rows = []
    nfse = select(FisNfse.numero, FisNfse.autorizada_em, FisNfse.valor_servico, FisNfse.chave_acesso).where(
        FisNfse.status == NfseStatus.AUTORIZADA,
        FisNfse.autorizada_em >= _dt_start(ini),
        FisNfse.autorizada_em <= _dt_end(fim),
    )
    for r in (await session.execute(nfse)).all():
        rows.append(["NFS-e", r[0], r[1].date().isoformat() if r[1] else "", r[2], r[3] or ""])
    nfe = select(FisNfe.numero, FisNfe.autorizada_em, FisNfe.valor_total, FisNfe.chave_acesso).where(
        FisNfe.status == NfeStatus.AUTORIZADA_SEFAZ,
        FisNfe.autorizada_em >= _dt_start(ini),
        FisNfe.autorizada_em <= _dt_end(fim),
    )
    for r in (await session.execute(nfe)).all():
        rows.append(["NF-e", r[0], r[1].date().isoformat() if r[1] else "", r[2], r[3] or ""])
    return ReportData("Exportação contábil", ["tipo", "numero", "data", "valor", "chave"], rows)


async def _divergencias_fiscais(session: AsyncSession, params: dict) -> ReportData:
    rows = []
    rej_nfse = select(FisNfse.numero, FisNfse.rejeicao_motivo, FisNfse.updated_at).where(
        FisNfse.status == NfseStatus.REJEITADA
    )
    for r in (await session.execute(rej_nfse)).all():
        rows.append(["NFS-e", r[0], r[1] or "Rejeitada", r[2].date().isoformat() if r[2] else ""])
    rej_nfe = select(FisNfe.numero, FisNfe.rejeicao_motivo, FisNfe.updated_at).where(
        FisNfe.status == NfeStatus.REJEITADA
    )
    for r in (await session.execute(rej_nfe)).all():
        rows.append(["NF-e", r[0], r[1] or "Rejeitada", r[2].date().isoformat() if r[2] else ""])
    canc = select(
        FisCancelamento.documento_tipo,
        FisCancelamento.documento_id,
        FisCancelamento.motivo,
        FisCancelamento.solicitado_em,
    ).where(FisCancelamento.status == CancelamentoStatus.REJEITADO)
    for r in (await session.execute(canc)).all():
        rows.append([r[0].value, str(r[1])[:8], r[2], r[3].date().isoformat() if r[3] else ""])
    return ReportData("Divergências fiscais", ["tipo", "documento", "motivo", "data"], rows)


# ---------------------------------------------------------------- §11.5 Gerencial
async def _painel_executivo(session: AsyncSession, params: dict) -> ReportData:
    veic = (await session.execute(select(func.count()).select_from(FrotaVeiculo).where(FrotaVeiculo.deleted_at.is_(None)))).scalar_one()
    ativos = (
        await session.execute(
            select(func.count()).select_from(LocContrato).where(LocContrato.status == ContratoStatus.ATIVO)
        )
    ).scalar_one()
    ini, fim, _ = _parse_params(params)
    rec = (
        await session.execute(
            select(func.coalesce(func.sum(LocContrato.valor_final), 0)).where(
                LocContrato.checkin_em >= _dt_start(ini),
                LocContrato.checkin_em <= _dt_end(fim),
            )
        )
    ).scalar_one()
    aberto = (
        await session.execute(
            select(func.coalesce(func.sum(FinContaReceber.valor_saldo), 0)).where(
                FinContaReceber.status.in_([TituloStatus.EM_ABERTO, TituloStatus.VENCIDO])
            )
        )
    ).scalar_one()
    rows = [
        ["Veículos na frota", veic],
        ["Contratos ativos", ativos],
        ["Receita no período", rec],
        ["Inadimplência (saldo CR)", aberto],
    ]
    return ReportData("Painel executivo", ["indicador", "valor"], rows)


async def _comparativo_filiais(session: AsyncSession, params: dict) -> ReportData:
    ini, fim, _ = _parse_params(params)
    stmt = (
        select(
            Filial.name,
            func.coalesce(func.sum(LocContrato.valor_final), 0),
        )
        .join(LocContrato, LocContrato.filial_retirada_id == Filial.id, isouter=True)
        .where(
            LocContrato.deleted_at.is_(None),
            LocContrato.checkin_em >= _dt_start(ini),
            LocContrato.checkin_em <= _dt_end(fim),
        )
        .group_by(Filial.name)
    )
    rows = []
    for nome, rec in (await session.execute(stmt)).all():
        cust = Decimal("0")
        rows.append([nome or "—", rec, cust, _dec(rec) - cust])
    return ReportData("Comparativo entre filiais", ["filial", "receita", "custos", "margem"], rows)


async def _metas_vendedores(session: AsyncSession, params: dict) -> ReportData:
    from app.modules.comercial.models import CrmOportunidade
    from app.modules.cadastros.models_extra import Vendedor

    ini, fim, _ = _parse_params(params)
    stmt = (
        select(
            Vendedor.nome,
            func.count(CrmOportunidade.id),
        )
        .join(CrmOportunidade, CrmOportunidade.vendedor_id == Vendedor.id, isouter=True)
        .where(Vendedor.deleted_at.is_(None))
        .group_by(Vendedor.nome)
    )
    rows = [[r[0], r[1] or 0, 0, 0] for r in (await session.execute(stmt)).all()]
    return ReportData("Metas x realizado (vendedores)", ["vendedor", "oportunidades", "contratos", "receita"], rows)


async def _sazonalidade(session: AsyncSession, params: dict) -> ReportData:
    hoje = date.today()
    rows = []
    for i in range(11, -1, -1):
        ref = hoje.replace(day=1) - timedelta(days=i * 28)
        mes = ref.strftime("%Y-%m")
        rs = (
            await session.execute(
                select(func.count()).select_from(ResReserva).where(
                    func.to_char(ResReserva.created_at, "YYYY-MM") == mes
                )
            )
        ).scalar_one()
        cs = (
            await session.execute(
                select(func.count()).select_from(LocContrato).where(
                    func.to_char(LocContrato.created_at, "YYYY-MM") == mes
                )
            )
        ).scalar_one()
        rev = (
            await session.execute(
                select(func.coalesce(func.sum(LocContrato.valor_final), 0)).where(
                    func.to_char(LocContrato.checkin_em, "YYYY-MM") == mes
                )
            )
        ).scalar_one()
        rows.append([mes, rs, cs, rev])
    return ReportData("Análise de sazonalidade", ["mes", "reservas", "contratos", "receita"], rows)


async def _projecao_demanda(session: AsyncSession, params: dict) -> ReportData:
    hoje = date.today()
    ultimos = []
    for i in range(3, 0, -1):
        mes = (hoje.replace(day=1) - timedelta(days=i * 28)).strftime("%Y-%m")
        cnt = (
            await session.execute(
                select(func.count()).select_from(ResReserva).where(
                    func.to_char(ResReserva.created_at, "YYYY-MM") == mes
                )
            )
        ).scalar_one()
        ultimos.append(cnt or 0)
    media = sum(ultimos) / len(ultimos) if ultimos else 0
    rows = []
    for j in range(1, 4):
        ref = hoje.replace(day=1) + timedelta(days=j * 31)
        rows.append([ref.strftime("%Y-%m"), round(media), round(media * 500, 2)])
    return ReportData("Projeção de demanda", ["mes_projecao", "demanda_estimada", "receita_estimada"], rows)


_GENERATORS = {
    "frota_atual": _frota_atual,
    "rentabilidade_veiculo": _rentabilidade_veiculo,
    "ociosidade_ocupacao": _ociosidade_ocupacao,
    "tco_veiculo": _tco_veiculo,
    "idade_media_frota": _idade_media_frota,
    "vencimentos_documentacao": _vencimentos_documentacao,
    "contratos_periodo": _contratos_periodo,
    "ticket_medio": _ticket_medio,
    "tempo_medio_locacao": _tempo_medio_locacao,
    "taxa_renovacao": _taxa_renovacao,
    "taxa_no_show_cancelamento": _taxa_no_show_cancelamento,
    "ranking_clientes": _ranking_clientes,
    "avarias_responsabilizacao": _avarias_responsabilizacao,
    "multas_relatorio": _multas_relatorio,
    "dre_simplificado": _dre_simplificado,
    "fluxo_caixa": _fluxo_caixa,
    "inadimplencia_aging": _inadimplencia_aging,
    "faturamento_segmento": _faturamento_segmento,
    "comissoes_pagas": _comissoes_pagas,
    "conciliacao_resumo": _conciliacao_resumo,
    "notas_periodo": _notas_periodo,
    "apuracao_impostos": _apuracao_impostos,
    "export_contabilidade": _export_contabilidade,
    "divergencias_fiscais": _divergencias_fiscais,
    "painel_executivo": _painel_executivo,
    "comparativo_filiais": _comparativo_filiais,
    "metas_vendedores": _metas_vendedores,
    "sazonalidade": _sazonalidade,
    "projecao_demanda": _projecao_demanda,
}
