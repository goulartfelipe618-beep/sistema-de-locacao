"""Catálogo de relatórios pré-definidos (§11.1–11.5)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.shared.enums import RelCategoria


@dataclass(frozen=True, slots=True)
class ReportDef:
    codigo: str
    titulo: str
    descricao: str
    categoria: RelCategoria
    pesado: bool = False
    suporta_custom: bool = False
    colunas_disponiveis: tuple[str, ...] = ()
    filtros: tuple[str, ...] = ("periodo_inicio", "periodo_fim", "filial_id")


def _def(
    codigo: str,
    titulo: str,
    descricao: str,
    categoria: RelCategoria,
    *,
    pesado: bool = False,
    suporta_custom: bool = False,
    colunas: tuple[str, ...] = (),
) -> ReportDef:
    return ReportDef(
        codigo=codigo,
        titulo=titulo,
        descricao=descricao,
        categoria=categoria,
        pesado=pesado,
        suporta_custom=suporta_custom,
        colunas_disponiveis=colunas,
    )


REPORT_CATALOG: dict[str, ReportDef] = {
    # §11.1 Frota
    "frota_atual": _def(
        "frota_atual",
        "Frota atual",
        "Posição da frota por status, filial e categoria.",
        RelCategoria.FROTA,
        colunas=("status", "filial", "categoria", "quantidade"),
    ),
    "rentabilidade_veiculo": _def(
        "rentabilidade_veiculo",
        "Rentabilidade por veículo",
        "Receita de locação menos custos de manutenção por veículo.",
        RelCategoria.FROTA,
        pesado=True,
        suporta_custom=True,
        colunas=("placa", "receita", "custo_manutencao", "margem"),
    ),
    "ociosidade_ocupacao": _def(
        "ociosidade_ocupacao",
        "Ociosidade / ocupação",
        "Taxa de ocupação por veículo ou categoria no período.",
        RelCategoria.FROTA,
        pesado=True,
        colunas=("placa", "categoria", "dias_locados", "dias_disponiveis", "taxa_ocupacao"),
    ),
    "tco_veiculo": _def(
        "tco_veiculo",
        "TCO por veículo",
        "Custo total de propriedade (aquisição + manutenção).",
        RelCategoria.FROTA,
        colunas=("placa", "valor_aquisicao", "custo_manutencao", "tco"),
    ),
    "idade_media_frota": _def(
        "idade_media_frota",
        "Idade média da frota",
        "Idade média por categoria e filial.",
        RelCategoria.FROTA,
        colunas=("filial", "categoria", "idade_media_anos", "quantidade"),
    ),
    "vencimentos_documentacao": _def(
        "vencimentos_documentacao",
        "Vencimentos de documentação",
        "Documentos de veículos a vencer no período.",
        RelCategoria.FROTA,
        colunas=("placa", "tipo", "vencimento", "status"),
    ),
    # §11.2 Locação
    "contratos_periodo": _def(
        "contratos_periodo",
        "Contratos por período",
        "Contratos agrupados por status, filial e canal.",
        RelCategoria.LOCACAO,
        suporta_custom=True,
        colunas=("numero", "status", "filial", "cliente", "valor_final", "retirada"),
    ),
    "ticket_medio": _def(
        "ticket_medio",
        "Ticket médio",
        "Valor médio por contrato encerrado no período.",
        RelCategoria.LOCACAO,
        colunas=("filial", "contratos", "ticket_medio"),
    ),
    "tempo_medio_locacao": _def(
        "tempo_medio_locacao",
        "Tempo médio de locação",
        "Média de dias entre check-out e check-in.",
        RelCategoria.LOCACAO,
        colunas=("filial", "contratos", "dias_medio"),
    ),
    "taxa_renovacao": _def(
        "taxa_renovacao",
        "Taxa de renovação",
        "Renovações (aditivos) sobre contratos ativos/encerrados.",
        RelCategoria.LOCACAO,
        colunas=("filial", "contratos_base", "renovacoes", "taxa_pct"),
    ),
    "taxa_no_show_cancelamento": _def(
        "taxa_no_show_cancelamento",
        "No-show e cancelamentos",
        "Taxa de no-show e cancelamento sobre reservas.",
        RelCategoria.LOCACAO,
        colunas=("origem", "total", "no_show", "canceladas", "taxa_pct"),
    ),
    "ranking_clientes": _def(
        "ranking_clientes",
        "Ranking de clientes",
        "Clientes por volume e receita no período.",
        RelCategoria.LOCACAO,
        colunas=("cliente", "contratos", "receita_total"),
    ),
    "avarias_responsabilizacao": _def(
        "avarias_responsabilizacao",
        "Avarias e responsabilização",
        "Avarias por responsabilidade e status.",
        RelCategoria.LOCACAO,
        colunas=("responsabilidade", "status", "quantidade", "valor_estimado"),
    ),
    "multas_relatorio": _def(
        "multas_relatorio",
        "Multas e infrações",
        "Multas por status e valor repassado.",
        RelCategoria.LOCACAO,
        colunas=("status", "quantidade", "valor_total", "valor_repassado"),
    ),
    # §11.3 Financeiro
    "dre_simplificado": _def(
        "dre_simplificado",
        "DRE simplificado",
        "Receita de locação menos custos operacionais e despesas.",
        RelCategoria.FINANCEIRO,
        pesado=True,
        colunas=("conta", "valor"),
    ),
    "fluxo_caixa": _def(
        "fluxo_caixa",
        "Fluxo de caixa",
        "Entradas e saídas de caixa por dia.",
        RelCategoria.FINANCEIRO,
        colunas=("data", "entradas", "saidas", "saldo_dia"),
    ),
    "inadimplencia_aging": _def(
        "inadimplencia_aging",
        "Inadimplência (aging)",
        "Títulos a receber por faixa de atraso.",
        RelCategoria.FINANCEIRO,
        colunas=("faixa", "quantidade", "valor"),
    ),
    "faturamento_segmento": _def(
        "faturamento_segmento",
        "Faturamento por filial",
        "Receita por filial no período.",
        RelCategoria.FINANCEIRO,
        colunas=("filial", "contratos", "receita"),
    ),
    "comissoes_pagas": _def(
        "comissoes_pagas",
        "Comissões pagas",
        "Pagamentos de comissão a vendedores/parceiros.",
        RelCategoria.FINANCEIRO,
        colunas=("beneficiario", "valor", "vencimento", "status"),
    ),
    "conciliacao_resumo": _def(
        "conciliacao_resumo",
        "Conciliação bancária",
        "Linhas conciliadas vs pendentes por conta.",
        RelCategoria.FINANCEIRO,
        colunas=("conta", "conciliado", "pendente", "divergente"),
    ),
    # §11.4 Fiscal
    "notas_periodo": _def(
        "notas_periodo",
        "Notas emitidas/canceladas",
        "NFS-e e NF-e por status no período.",
        RelCategoria.FISCAL,
        colunas=("tipo", "status", "quantidade", "valor_total"),
    ),
    "apuracao_impostos": _def(
        "apuracao_impostos",
        "Apuração de impostos",
        "ISS e ICMS apurados no período.",
        RelCategoria.FISCAL,
        colunas=("imposto", "base_calculo", "valor"),
    ),
    "export_contabilidade": _def(
        "export_contabilidade",
        "Exportação contábil",
        "Documentos fiscais padronizados para contabilidade.",
        RelCategoria.FISCAL,
        pesado=True,
        colunas=("tipo", "numero", "data", "valor", "chave"),
    ),
    "divergencias_fiscais": _def(
        "divergencias_fiscais",
        "Divergências fiscais",
        "Documentos rejeitados e cancelamentos não confirmados.",
        RelCategoria.FISCAL,
        colunas=("tipo", "documento", "motivo", "data"),
    ),
    # §11.5 Gerencial
    "painel_executivo": _def(
        "painel_executivo",
        "Painel executivo",
        "KPIs consolidados de frota, locação e financeiro.",
        RelCategoria.GERENCIAL,
        pesado=True,
        colunas=("indicador", "valor"),
    ),
    "comparativo_filiais": _def(
        "comparativo_filiais",
        "Comparativo entre filiais",
        "Receita, custos e margem por filial.",
        RelCategoria.GERENCIAL,
        pesado=True,
        colunas=("filial", "receita", "custos", "margem"),
    ),
    "metas_vendedores": _def(
        "metas_vendedores",
        "Metas x realizado (vendedores)",
        "Contratos/reservas por vendedor.",
        RelCategoria.GERENCIAL,
        colunas=("vendedor", "oportunidades", "contratos", "receita"),
    ),
    "sazonalidade": _def(
        "sazonalidade",
        "Análise de sazonalidade",
        "Reservas e contratos por mês (últimos 12 meses).",
        RelCategoria.GERENCIAL,
        colunas=("mes", "reservas", "contratos", "receita"),
    ),
    "projecao_demanda": _def(
        "projecao_demanda",
        "Projeção de demanda",
        "Projeção simples com base na média dos últimos 3 meses.",
        RelCategoria.GERENCIAL,
        colunas=("mes_projecao", "demanda_estimada", "receita_estimada"),
    ),
}

CATEGORIA_LABELS: dict[RelCategoria, str] = {
    RelCategoria.FROTA: "Frota",
    RelCategoria.LOCACAO: "Locação",
    RelCategoria.FINANCEIRO: "Financeiro",
    RelCategoria.FISCAL: "Fiscal",
    RelCategoria.GERENCIAL: "Gerencial",
}


def list_by_categoria(categoria: RelCategoria) -> list[ReportDef]:
    return [r for r in REPORT_CATALOG.values() if r.categoria == categoria]


def get_report(codigo: str) -> ReportDef | None:
    return REPORT_CATALOG.get(codigo)
