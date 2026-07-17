"""Testes do Motor de PDF (§16)."""

from __future__ import annotations

from app.core.rbac import PERMISSIONS_BY_CODE
from app.modules.documentos.catalog import TEMPLATES, TEMPLATES_BY_ID
from app.modules.documentos.pdf_engine import html_to_pdf, render_html, sha256_bytes
from app.web.navigation import build_menu
from tests.test_navigation import _make_user


def test_permissoes_documentos_registradas() -> None:
    assert "documentos.historico.visualizar" in PERMISSIONS_BY_CODE


def test_catalogo_templates_completo() -> None:
    assert len(TEMPLATES) >= 26
    assert "contrato_locacao" in TEMPLATES_BY_ID
    assert "reserva_confirmacao" in TEMPLATES_BY_ID
    assert "danfe" in TEMPLATES_BY_ID
    assert "danfse" in TEMPLATES_BY_ID
    assert "recibo_caucao" in TEMPLATES_BY_ID
    assert "boleto_fatura" in TEMPLATES_BY_ID
    assert "doc_vencimentos" in TEMPLATES_BY_ID
    assert "ficha_cliente" in TEMPLATES_BY_ID
    assert "extrato_cliente" in TEMPLATES_BY_ID
    assert "multa_condutor" in TEMPLATES_BY_ID
    assert "auditoria_export" in TEMPLATES_BY_ID
    assert "termo_responsabilidade" in TEMPLATES_BY_ID
    assert "aditivo_contratual" in TEMPLATES_BY_ID
    assert "declaracao_quitacao" in TEMPLATES_BY_ID
    assert "certidao_regularidade_frota" in TEMPLATES_BY_ID
    assert "fechamento_caixa" in TEMPLATES_BY_ID
    assert TEMPLATES_BY_ID["relatorio_analitico"].pesado is True
    assert TEMPLATES_BY_ID["auditoria_export"].pesado is True


def test_pdf_engine_renderiza_template_novo() -> None:
    html = render_html(
        "documentos/recibo_caucao.html",
        {
            "doc_titulo": "Recibo de Caução",
            "empresa_nome": "Locadora X",
            "empresa_razao": "Locadora X LTDA",
            "empresa_cnpj": "00000000000100",
            "empresa_email": "a@b.com",
            "empresa_phone": "11999999999",
            "watermark": None,
            "contrato": type("C", (), {"numero": "CT-001"})(),
            "cliente_nome": "João",
            "veiculo_label": "ABC1D23",
            "filial_nome": "Matriz",
            "valor_caucao": 500,
            "forma_pagamento": "Cartão",
        },
    )
    assert "Recibo de Caução" in html
    assert "João" in html


def test_pdf_engine_renderiza_html() -> None:
    html = render_html(
        "documentos/base_pdf.html",
        {
            "doc_titulo": "Teste",
            "empresa_nome": "Locadora X",
            "empresa_razao": "Locadora X LTDA",
            "empresa_cnpj": "00000000000100",
            "empresa_email": "a@b.com",
            "empresa_phone": "11999999999",
            "watermark": None,
        },
    )
    assert "Locadora X" in html
    blob = html_to_pdf(html)
    assert len(blob) > 50
    assert sha256_bytes(blob)


def test_menu_documentos_pdf_habilitado() -> None:
    menu = build_menu(
        _make_user(
            {
                "dashboard.painel.visualizar",
                "documentos.historico.visualizar",
            }
        )
    )
    rel = next(s for s in menu if s["label"] == "Relatórios")
    doc = next(item for item in rel["children"] if item["label"] == "Documentos PDF")
    assert doc["enabled"] is True
