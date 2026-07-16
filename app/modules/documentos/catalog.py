"""Catálogo de templates PDF do motor (§16)."""

from __future__ import annotations

from dataclasses import dataclass

from app.shared.enums import DocFamilia


@dataclass(frozen=True, slots=True)
class TemplateDef:
    """Definição de um template transacional/analítico."""

    template_id: str
    template_path: str
    titulo: str
    familia: DocFamilia
    entidade_tipo: str
    permission: str
    sincrono: bool = True
    pesado: bool = False


TEMPLATES: tuple[TemplateDef, ...] = (
    TemplateDef(
        "reserva_confirmacao",
        "documentos/reserva_confirmacao.html",
        "Confirmação de Reserva",
        DocFamilia.TRANSACIONAL,
        "reserva",
        "reservas.reserva.visualizar",
    ),
    TemplateDef(
        "reserva_voucher",
        "documentos/reserva_voucher.html",
        "Voucher de Reserva",
        DocFamilia.TRANSACIONAL,
        "reserva",
        "reservas.reserva.visualizar",
    ),
    TemplateDef(
        "cotacao",
        "documentos/cotacao.html",
        "Cotação / Orçamento",
        DocFamilia.TRANSACIONAL,
        "cotacao",
        "reservas.cotacao.visualizar",
    ),
    TemplateDef(
        "contrato_locacao",
        "documentos/contrato_locacao.html",
        "Contrato de Locação",
        DocFamilia.TRANSACIONAL,
        "contrato",
        "locacoes.contrato.visualizar",
    ),
    TemplateDef(
        "vistoria_checkout",
        "documentos/vistoria.html",
        "Termo de Vistoria (Check-out)",
        DocFamilia.TRANSACIONAL,
        "contrato",
        "locacoes.checkout.visualizar",
    ),
    TemplateDef(
        "vistoria_checkin",
        "documentos/vistoria.html",
        "Termo de Devolução (Check-in)",
        DocFamilia.TRANSACIONAL,
        "contrato",
        "locacoes.checkin.visualizar",
    ),
    TemplateDef(
        "laudo_avaria",
        "documentos/laudo_avaria.html",
        "Laudo de Avaria",
        DocFamilia.TRANSACIONAL,
        "avaria",
        "locacoes.avaria.visualizar",
    ),
    TemplateDef(
        "ordem_servico",
        "documentos/ordem_servico.html",
        "Ordem de Serviço",
        DocFamilia.TRANSACIONAL,
        "ordem_servico",
        "manutencao.os.visualizar",
    ),
    TemplateDef(
        "ficha_veiculo",
        "documentos/ficha_veiculo.html",
        "Ficha Técnica do Veículo",
        DocFamilia.TRANSACIONAL,
        "veiculo",
        "frota.veiculo.visualizar",
    ),
    TemplateDef(
        "proposta_comercial",
        "documentos/proposta_comercial.html",
        "Proposta Comercial",
        DocFamilia.TRANSACIONAL,
        "proposta",
        "comercial.proposta.visualizar",
    ),
    TemplateDef(
        "recibo_pagamento",
        "documentos/recibo_pagamento.html",
        "Recibo de Pagamento",
        DocFamilia.TRANSACIONAL,
        "conta_receber",
        "financeiro.receber.visualizar",
    ),
    TemplateDef(
        "danfe",
        "documentos/danfe.html",
        "DANFE — NF-e",
        DocFamilia.TRANSACIONAL,
        "nfe",
        "fiscal.nfe.visualizar",
    ),
    TemplateDef(
        "danfse",
        "documentos/danfse.html",
        "DANFSE — NFS-e",
        DocFamilia.TRANSACIONAL,
        "nfse",
        "fiscal.nfse.visualizar",
    ),
    TemplateDef(
        "relatorio_analitico",
        "documentos/relatorio_analitico.html",
        "Relatório Analítico",
        DocFamilia.ANALITICO,
        "relatorio",
        "relatorios.historico.visualizar",
        sincrono=False,
        pesado=True,
    ),
    TemplateDef(
        "recibo_caucao",
        "documentos/recibo_caucao.html",
        "Recibo de Caução",
        DocFamilia.TRANSACIONAL,
        "contrato",
        "locacoes.contrato.visualizar",
    ),
    TemplateDef(
        "boleto_fatura",
        "documentos/boleto_fatura.html",
        "Boleto / Fatura",
        DocFamilia.TRANSACIONAL,
        "fatura",
        "financeiro.faturamento.visualizar",
    ),
    TemplateDef(
        "doc_vencimentos",
        "documentos/doc_vencimentos.html",
        "Vencimentos de Documentação",
        DocFamilia.ANALITICO,
        "tenant",
        "frota.documentacao.visualizar",
    ),
    TemplateDef(
        "ficha_cliente",
        "documentos/ficha_cliente.html",
        "Ficha Cadastral do Cliente",
        DocFamilia.TRANSACIONAL,
        "cliente",
        "cadastros.cliente.visualizar",
    ),
    TemplateDef(
        "extrato_cliente",
        "documentos/extrato_cliente.html",
        "Extrato de Relacionamento",
        DocFamilia.ANALITICO,
        "cliente",
        "cadastros.cliente.visualizar",
    ),
    TemplateDef(
        "multa_condutor",
        "documentos/multa_condutor.html",
        "Indicação de Condutor (Multa)",
        DocFamilia.TRANSACIONAL,
        "multa",
        "locacoes.multa.visualizar",
    ),
    TemplateDef(
        "auditoria_export",
        "documentos/auditoria_export.html",
        "Trilha de Auditoria (Exportação)",
        DocFamilia.ANALITICO,
        "tenant",
        "auditoria.trilha.visualizar",
        sincrono=False,
        pesado=True,
    ),
)

TEMPLATES_BY_ID: dict[str, TemplateDef] = {t.template_id: t for t in TEMPLATES}
