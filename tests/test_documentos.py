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
    assert len(TEMPLATES) >= 14
    assert "contrato_locacao" in TEMPLATES_BY_ID
    assert "reserva_confirmacao" in TEMPLATES_BY_ID
    assert "danfe" in TEMPLATES_BY_ID
    assert "danfse" in TEMPLATES_BY_ID
    assert TEMPLATES_BY_ID["relatorio_analitico"].pesado is True


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
