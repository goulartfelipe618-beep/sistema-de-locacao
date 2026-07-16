"""Testes de integrações §12: registry, rate limit, fiscal cert factory."""

from __future__ import annotations

import hashlib
import hmac

from app.modules.fiscal.adapters.certificado import CertBundle, assinar_xml
from app.modules.fiscal.adapters.simulador_nfe import SimuladorSefaz
from app.modules.fiscal.adapters.simulador_nfse import SimuladorNfse
from app.modules.integracoes.adapters.registry import (
    MercadoPagoAdapter,
    PagSeguroAdapter,
    SerasaAdapter,
    get_payment_adapter,
)
from app.modules.integracoes.outbound import OUTBOUND_EVENTOS


def test_outbound_eventos_cadastrados() -> None:
    assert "reserva.confirmada" in OUTBOUND_EVENTOS
    assert "contrato.encerrado" in OUTBOUND_EVENTOS


def test_registry_mercadopago_valida_credencial() -> None:
    gw = get_payment_adapter("mercadopago")
    assert isinstance(gw, MercadoPagoAdapter)
    assert gw.testar_conexao(credenciais={"access_token": "APP_USR-12345678"}) is True
    assert gw.testar_conexao(credenciais={}) is False


def test_registry_pagseguro_valida_credencial() -> None:
    gw = get_payment_adapter("pagseguro")
    assert isinstance(gw, PagSeguroAdapter)
    assert gw.testar_conexao(credenciais={"email": "a@b.com", "token": "xyz"}) is True


def test_registry_serasa_exige_credencial() -> None:
    adapter = SerasaAdapter()
    try:
        adapter.consultar_score(documento="123", tipo_pessoa="pf", credenciais={})
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_assinar_xml_com_cert_bundle_fake() -> None:
    """Assinatura falha com PFX inválido; simulador segue sem cert."""
    xml = "<NFe>teste</NFe>"
    try:
        assinar_xml(xml, CertBundle(pfx_bytes=b"invalid", password="x", subject="CN=Test"))
        signed = True
    except Exception:
        signed = False
    assert signed is False


def test_factory_sem_sessao_retorna_simulador_types() -> None:
    """Tipos de retorno dos simuladores (referência para factory async)."""
    assert SimuladorSefaz().nome == "simulador"
    assert SimuladorNfse().nome == "simulador"


def test_outbound_hmac_format() -> None:
    from app.modules.integracoes.outbound import OutboundWebhookService

    svc = OutboundWebhookService.__new__(OutboundWebhookService)
    sig = svc._sign(b'{"evento":"test"}', "secret")
    expected = hmac.new(b"secret", b'{"evento":"test"}', hashlib.sha256).hexdigest()
    assert sig == expected
