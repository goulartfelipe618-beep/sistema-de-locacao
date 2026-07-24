"""Testes do módulo Fiscal (§10): transições, impostos, XML, prazos e adapters."""

from __future__ import annotations

from decimal import Decimal

from app.core.rbac import PERMISSIONS_BY_CODE
from app.modules.fiscal.adapters.simulador_nfe import SimuladorSefaz, _chave_44
from app.modules.fiscal.adapters.simulador_nfse import SimuladorNfse
from app.modules.fiscal.service import (
    _DEFAULT_ALIQUOTAS,
    _DEFAULT_PRAZO_HORAS,
    NFE_TRANSITIONS,
    NFSE_TRANSITIONS,
    XmlService,
    _money,
)
from app.shared.enums import (
    FiscalDocumentoTipo,
    ImpostoTipo,
    NfeStatus,
    NfseStatus,
)
from app.web.navigation import build_menu
from tests.test_navigation import _make_user

FISCAL_PERMS = {
    "fiscal.nfse.visualizar",
    "fiscal.nfe.visualizar",
    "fiscal.xml.visualizar",
    "fiscal.cancelamentos.visualizar",
    "fiscal.impostos.visualizar",
}

_NFE_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<nfeProc versao="4.00"><NFe><infNFe Id="NFe'
    + "1" * 44
    + '">'
    "<emit><CNPJ>12345678000199</CNPJ></emit>"
    "<total><ICMSTot><vNF>1500.50</vNF></ICMSTot></total>"
    "</infNFe></NFe></nfeProc>"
)


# ------------------------------------------------------------- Numeração
def test_numeracao_formats() -> None:
    assert f"{1:06d}" == "000001"
    assert f"EVT-{7:06d}" == "EVT-000007"


# --------------------------------------------------------- Máquina de estados
def test_nfse_transicoes_terminais() -> None:
    assert NfseStatus.AUTORIZADA in NFSE_TRANSITIONS[NfseStatus.A_EMITIR]
    assert NFSE_TRANSITIONS[NfseStatus.CANCELADA] == set()
    # Autorizada só pode ir para cancelada.
    assert NFSE_TRANSITIONS[NfseStatus.AUTORIZADA] == {NfseStatus.CANCELADA}


def test_nfe_transicoes_terminais() -> None:
    assert NfeStatus.AUTORIZADA_SEFAZ in NFE_TRANSITIONS[NfeStatus.A_EMITIR]
    assert NFE_TRANSITIONS[NfeStatus.CANCELADA] == set()
    assert NFE_TRANSITIONS[NfeStatus.DENEGADA] == set()
    # Rejeitada pode voltar para a_emitir (reprocessamento).
    assert NfeStatus.A_EMITIR in NFE_TRANSITIONS[NfeStatus.REJEITADA]


# ----------------------------------------------------------- Impostos
def test_money_quantize() -> None:
    assert _money(Decimal("10")) == Decimal("10.00")
    assert _money(Decimal("10.1")) == Decimal("10.10")


def test_iss_calculo_default() -> None:
    percentual = _DEFAULT_ALIQUOTAS[ImpostoTipo.ISS]
    valor = _money(Decimal("1000") * percentual / Decimal(100))
    assert percentual == Decimal("5")
    assert valor == Decimal("50.00")


# ----------------------------------------------------------- Prazos
def test_prazo_default_cancelamento() -> None:
    assert _DEFAULT_PRAZO_HORAS[FiscalDocumentoTipo.NFSE] == 24
    assert _DEFAULT_PRAZO_HORAS[FiscalDocumentoTipo.NFE] == 24


# ----------------------------------------------------------- XML
def test_xml_hash_deterministico_e_dedup() -> None:
    svc = XmlService(session=None)  # type: ignore[arg-type]
    conteudo = "<a><b>x</b></a>"
    h1 = svc._hash(conteudo)
    h2 = svc._hash(conteudo)
    assert h1 == h2
    assert len(h1) == 64
    # Conteúdo diferente → hash diferente (base do dedup no-overwrite).
    assert svc._hash("<a><b>y</b></a>") != h1


def test_xml_validar_schema_basico() -> None:
    svc = XmlService(session=None)  # type: ignore[arg-type]
    assert svc.validar_schema_basico("<NFe><infNFe/></NFe>") is True
    assert svc.validar_schema_basico("<NFe><infNFe></NFe>") is False  # malformado
    assert svc.validar_schema_basico("<x/>", tags_obrigatorias=["y"]) is False


def test_xml_parse_nfe_recebida() -> None:
    svc = XmlService(session=None)  # type: ignore[arg-type]
    chave, cnpj, valor = svc._parse_nfe_recebida(_NFE_XML)
    assert chave == "1" * 44
    assert cnpj == "12345678000199"
    assert valor == Decimal("1500.50")


# ----------------------------------------------------------- Adapters
def test_simulador_nfse_autoriza_e_gera_chave() -> None:
    r = SimuladorNfse().emitir(
        numero="000001",
        serie="A",
        cnpj_prestador="12345678000199",
        tomador_nome="Cliente Teste",
        municipio_ibge="3550308",
        valor_servico=Decimal("500"),
        aliquota_iss=Decimal("5"),
        valor_iss=Decimal("25"),
        discriminacao="Locação",
    )
    assert r.autorizada is True
    assert r.chave_acesso and len(r.chave_acesso) == 44
    assert r.protocolo
    assert "<CompNfse>" in r.xml


def test_simulador_nfse_rejeita_valor_zero() -> None:
    r = SimuladorNfse().emitir(
        numero="000002",
        serie="A",
        cnpj_prestador="12345678000199",
        tomador_nome="Cliente",
        municipio_ibge="3550308",
        valor_servico=Decimal("0"),
        aliquota_iss=Decimal("5"),
        valor_iss=Decimal("0"),
        discriminacao="x",
    )
    assert r.autorizada is False
    assert r.chave_acesso is None
    assert r.rejeicao_motivo


def test_simulador_sefaz_autoriza_com_itens() -> None:
    from app.modules.fiscal.adapters.nfe_port import NfeItemPayload

    r = SimuladorSefaz().emitir(
        numero="000001",
        serie="1",
        cnpj_emitente="12345678000199",
        destinatario_nome="Comprador",
        destinatario_doc="00011122233",
        natureza_operacao="Venda",
        valor_total=Decimal("50000"),
        itens=[
            NfeItemPayload(
                descricao="Veículo XYZ",
                quantidade=Decimal("1"),
                valor_total=Decimal("50000"),
                ncm="87032100",
                cfop="5551",
            )
        ],
    )
    assert r.autorizada is True
    assert r.chave_acesso and len(r.chave_acesso) == 44 and r.chave_acesso.isdigit()
    assert "<nfeProc" in r.xml


def test_simulador_sefaz_rejeita_sem_itens() -> None:
    r = SimuladorSefaz().emitir(
        numero="000002",
        serie="1",
        cnpj_emitente="12345678000199",
        destinatario_nome="Comprador",
        destinatario_doc=None,
        natureza_operacao="Venda",
        valor_total=Decimal("0"),
        itens=[],
    )
    assert r.autorizada is False
    assert r.chave_acesso is None


def test_chave_44_helper() -> None:
    chave = _chave_44()
    assert len(chave) == 44 and chave.isdigit()


# ----------------------------------------------------------- Permissões / Menu
def test_fiscal_permissions_registradas() -> None:
    for code in FISCAL_PERMS:
        assert code in PERMISSIONS_BY_CODE
    assert "fiscal.nfse.cancelar" in PERMISSIONS_BY_CODE
    assert "fiscal.nfe.cancelar" in PERMISSIONS_BY_CODE


def test_menu_fiscal_enabled() -> None:
    menu = build_menu(_make_user(FISCAL_PERMS), fiscal_emissao_habilitada=True)
    section = next(s for s in menu if s["label"] == "Fiscal")
    by_label = {i["label"]: i for i in section["children"]}
    for label, url in (
        ("NFS-e", "/fiscal/nfse"),
        ("NF-e", "/fiscal/nfe"),
        ("XML", "/fiscal/xml"),
        ("Cancelamentos", "/fiscal/cancelamentos"),
        ("Impostos", "/fiscal/impostos"),
    ):
        assert by_label[label]["enabled"] is True
        assert by_label[label]["url"] == url


def test_menu_fiscal_partial_permissions() -> None:
    menu = build_menu(_make_user({"fiscal.nfse.visualizar"}), fiscal_emissao_habilitada=True)
    section = next(s for s in menu if s["label"] == "Fiscal")
    labels = {i["label"] for i in section["children"]}
    assert labels == {"NFS-e"}


def test_menu_fiscal_hidden_when_emissao_disabled() -> None:
    perms = FISCAL_PERMS | {
        "dashboard.painel.visualizar",
        "relatorios.frota.visualizar",
        "relatorios.fiscal.visualizar",
    }
    menu = build_menu(_make_user(perms), fiscal_emissao_habilitada=False)
    labels = [s["label"] for s in menu]
    assert "Fiscal" not in labels
    rel = next(s for s in menu if s["label"] == "Relatórios")
    rel_labels = {item["label"] for item in rel["children"]}
    assert "Fiscal" not in rel_labels
