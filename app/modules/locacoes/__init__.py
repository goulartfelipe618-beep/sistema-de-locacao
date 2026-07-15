"""Módulo Locações — contratos, check-out/in, renovações, multas e avarias (§6)."""

from app.modules.locacoes.service import (
    AvariaService,
    CheckinService,
    CheckoutService,
    ContratoService,
    EncerramentoService,
    MultaService,
    RenovacaoService,
    CONTRATO_TRANSITIONS,
)

__all__ = [
    "CONTRATO_TRANSITIONS",
    "ContratoService",
    "CheckoutService",
    "CheckinService",
    "RenovacaoService",
    "EncerramentoService",
    "MultaService",
    "AvariaService",
]
