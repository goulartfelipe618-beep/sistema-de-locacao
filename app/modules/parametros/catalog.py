"""Catálogo de parâmetros configuráveis do ERP (§14.5).

Valores padrão ficam aqui; overrides por tenant/filial são persistidos em
``parametros_sistema``.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.shared.enums import ParametroCategoria, ParametroTipo


@dataclass(frozen=True, slots=True)
class ParamDef:
    """Definição estática de um parâmetro."""

    chave: str
    categoria: ParametroCategoria
    label: str
    descricao: str
    tipo: ParametroTipo
    valor_padrao: Any
    unidade: str | None = None


PARAM_CATALOG: tuple[ParamDef, ...] = (
    # ---- Geral / Numeração ----
    ParamDef(
        chave="geral.prefixo_reserva",
        categoria=ParametroCategoria.GERAL,
        label="Prefixo de reservas",
        descricao="Prefixo da numeração sequencial de reservas (ex.: RES-2026-000123).",
        tipo=ParametroTipo.STRING,
        valor_padrao="RES",
    ),
    ParamDef(
        chave="geral.prefixo_contrato",
        categoria=ParametroCategoria.GERAL,
        label="Prefixo de contratos",
        descricao="Prefixo da numeração sequencial de contratos de locação.",
        tipo=ParametroTipo.STRING,
        valor_padrao="CT",
    ),
    ParamDef(
        chave="geral.prefixo_os",
        categoria=ParametroCategoria.GERAL,
        label="Prefixo de ordens de serviço",
        descricao="Prefixo da numeração sequencial de OS.",
        tipo=ParametroTipo.STRING,
        valor_padrao="OS",
    ),
    ParamDef(
        chave="geral.prefixo_proposta",
        categoria=ParametroCategoria.GERAL,
        label="Prefixo de propostas comerciais",
        descricao="Prefixo da numeração sequencial de propostas.",
        tipo=ParametroTipo.STRING,
        valor_padrao="PROP",
    ),
    ParamDef(
        chave="geral.dashboard_refresh_minutos",
        categoria=ParametroCategoria.GERAL,
        label="Atualização do Dashboard (minutos)",
        descricao="Intervalo de materialização/atualização dos KPIs do Dashboard via Celery Beat.",
        tipo=ParametroTipo.INT,
        valor_padrao=15,
        unidade="min",
    ),
    # ---- Cadastros ----
    ParamDef(
        chave="cadastros.dias_bloqueio_inadimplencia",
        categoria=ParametroCategoria.CADASTROS,
        label="Dias para bloqueio por inadimplência",
        descricao="Após N dias de título vencido, bloqueia novas reservas do cliente.",
        tipo=ParametroTipo.INT,
        valor_padrao=30,
        unidade="dias",
    ),
    ParamDef(
        chave="cadastros.dias_alerta_cnh",
        categoria=ParametroCategoria.CADASTROS,
        label="Dias de alerta CNH (lista)",
        descricao="Dias antes do vencimento da CNH para disparar alertas (separados por vírgula).",
        tipo=ParametroTipo.STRING,
        valor_padrao="30,15,7",
    ),
    # ---- Reservas ----
    ParamDef(
        chave="reservas.buffer_horas",
        categoria=ParametroCategoria.RESERVAS,
        label="Buffer entre locações (horas)",
        descricao="Tempo mínimo entre devolução e próximo check-out do mesmo veículo.",
        tipo=ParametroTipo.INT,
        valor_padrao=2,
        unidade="h",
    ),
    ParamDef(
        chave="reservas.overbooking_percentual",
        categoria=ParametroCategoria.RESERVAS,
        label="Overbooking permitido (%)",
        descricao="Percentual acima da frota física por categoria; 0 desabilita overbooking.",
        tipo=ParametroTipo.DECIMAL,
        valor_padrao=Decimal("0"),
        unidade="%",
    ),
    # ---- Locações ----
    ParamDef(
        chave="locacoes.politica_combustivel_padrao",
        categoria=ParametroCategoria.LOCACOES,
        label="Política de combustível padrão",
        descricao="Política aplicada em novos contratos (ex.: devolver_tanque_cheio, mesmo_nivel).",
        tipo=ParametroTipo.STRING,
        valor_padrao="devolver_tanque_cheio",
    ),
    # ---- Manutenção ----
    ParamDef(
        chave="manutencao.os_valor_aprovacao",
        categoria=ParametroCategoria.MANUTENCAO,
        label="Valor-limite OS (aprovação)",
        descricao="OS acima deste valor exige aprovação de gestor (workflow).",
        tipo=ParametroTipo.DECIMAL,
        valor_padrao=Decimal("5000.00"),
        unidade="R$",
    ),
    ParamDef(
        chave="manutencao.preventiva_percentual_alerta",
        categoria=ParametroCategoria.MANUTENCAO,
        label="Preventiva — alerta (%)",
        descricao="Percentual de uso/km para alertar preventiva próxima do vencimento.",
        tipo=ParametroTipo.INT,
        valor_padrao=90,
        unidade="%",
    ),
    # ---- Financeiro ----
    ParamDef(
        chave="financeiro.ciclo_faturamento",
        categoria=ParametroCategoria.FINANCEIRO,
        label="Ciclo de faturamento padrão",
        descricao="Periodicidade padrão de fechamento (mensal, quinzenal, semanal).",
        tipo=ParametroTipo.STRING,
        valor_padrao="mensal",
    ),
    ParamDef(
        chave="financeiro.dia_fechamento",
        categoria=ParametroCategoria.FINANCEIRO,
        label="Dia de fechamento",
        descricao="Dia do mês (1–28) para fechamento de faturamento mensal.",
        tipo=ParametroTipo.INT,
        valor_padrao=1,
    ),
    # ---- Automações ----
    ParamDef(
        chave="automacoes.regua_cobranca_dias",
        categoria=ParametroCategoria.AUTOMACOES,
        label="Régua de cobrança (dias)",
        descricao="Dias relativos ao vencimento para notificações (ex.: -3,0,1,7).",
        tipo=ParametroTipo.STRING,
        valor_padrao="-3,0,1,7",
    ),
    ParamDef(
        chave="automacoes.dias_alerta_documento",
        categoria=ParametroCategoria.AUTOMACOES,
        label="Alertas documentação veículo (dias)",
        descricao="Dias antes do vencimento de CRLV/seguro/licenciamento para alertas.",
        tipo=ParametroTipo.STRING,
        valor_padrao="30,15,7",
    ),
    ParamDef(
        chave="workflows.limite_desconto_percentual",
        categoria=ParametroCategoria.AUTOMACOES,
        label="Limite desconto sem aprovação (%)",
        descricao="Descontos acima deste percentual exigem workflow de aprovação.",
        tipo=ParametroTipo.DECIMAL,
        valor_padrao=Decimal("10"),
        unidade="%",
    ),
    # ---- Auditoria ----
    ParamDef(
        chave="auditoria.retencao_anos",
        categoria=ParametroCategoria.AUDITORIA,
        label="Retenção da trilha (anos)",
        descricao="Período mínimo de retenção dos registros de auditoria.",
        tipo=ParametroTipo.INT,
        valor_padrao=5,
        unidade="anos",
    ),
)

CATALOG_BY_KEY: dict[str, ParamDef] = {p.chave: p for p in PARAM_CATALOG}

CATEGORIA_LABELS: dict[ParametroCategoria, str] = {
    ParametroCategoria.GERAL: "Geral / Numeração",
    ParametroCategoria.CADASTROS: "Cadastros",
    ParametroCategoria.RESERVAS: "Reservas",
    ParametroCategoria.LOCACOES: "Locações",
    ParametroCategoria.MANUTENCAO: "Manutenção",
    ParametroCategoria.FINANCEIRO: "Financeiro",
    ParametroCategoria.AUTOMACOES: "Automações / Workflows",
    ParametroCategoria.AUDITORIA: "Auditoria",
}
