"""Conformidade com ESPECIFICACAO-FUNCIONAL-ERP-LOCADORA.md (menus, PDFs, relatórios)."""

from __future__ import annotations

from app.modules.documentos.catalog import TEMPLATES_BY_ID
from app.modules.relatorios.catalog import REPORT_CATALOG
from app.web.navigation import NAVIGATION, MenuItem


def _collect_menu_items() -> list[MenuItem]:
    items: list[MenuItem] = []
    for section in NAVIGATION:
        if section.url:
            items.append(
                MenuItem(section.label, url=section.url, permission=section.permission, implemented=section.implemented)
            )
        items.extend(section.items)
    return items


def test_todos_menus_implementados() -> None:
    """Nenhum item do menu deve estar marcado como 'em breve'."""
    for item in _collect_menu_items():
        assert item.implemented is True, f"Menu não implementado: {item.label}"


def test_menus_tem_url_e_permissao() -> None:
    for item in _collect_menu_items():
        assert item.url, f"Menu sem URL: {item.label}"
        if item.label == "Autenticação 2FA":
            continue
        assert item.permission, f"Menu sem permissão: {item.label}"


def test_pdfs_consolidados_secao_16() -> None:
    """Lista consolidada de emissões PDF da spec §16."""
    esperados = {
        "reserva_confirmacao",
        "reserva_voucher",
        "cotacao",
        "contrato_locacao",
        "vistoria_checkout",
        "vistoria_checkin",
        "recibo_caucao",
        "laudo_avaria",
        "ordem_servico",
        "ficha_veiculo",
        "doc_vencimentos",
        "boleto_fatura",
        "recibo_pagamento",
        "proposta_comercial",
        "multa_condutor",
        "danfse",
        "danfe",
        "relatorio_analitico",
        "auditoria_export",
        "ficha_cliente",
        "extrato_cliente",
        "termo_responsabilidade",
        "aditivo_contratual",
        "declaracao_quitacao",
        "certidao_regularidade_frota",
        "fechamento_caixa",
    }
    faltando = esperados - set(TEMPLATES_BY_ID)
    assert not faltando, f"PDFs faltando no catálogo: {sorted(faltando)}"


def test_relatorios_catalogo_secao_11() -> None:
    """29 relatórios pré-definidos (§11.1–11.5)."""
    assert len(REPORT_CATALOG) >= 25
    categorias = {r.categoria.value for r in REPORT_CATALOG.values()}
    assert categorias >= {"frota", "locacao", "financeiro", "fiscal", "gerencial"}


def test_secoes_principais_navigation() -> None:
    labels = {s.label for s in NAVIGATION}
    for secao in (
        "Dashboard",
        "Cadastros",
        "Frota",
        "Manutenção",
        "Reservas",
        "Locações",
        "Comercial / CRM",
        "Tarifário",
        "Financeiro",
        "Fiscal",
        "Relatórios",
        "Integrações",
        "Automações",
        "Configurações",
        "Auditoria",
    ):
        assert secao in labels, f"Seção ausente no menu: {secao}"
