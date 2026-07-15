"""Módulo Manutenção — ordens de serviço, preventiva, peças/estoque e pneus."""

from app.modules.manutencao.service import (
    EstoqueService,
    OrdemServicoService,
    PecaService,
    PlanoPreventivoService,
    PneuService,
)

__all__ = [
    "EstoqueService",
    "OrdemServicoService",
    "PecaService",
    "PlanoPreventivoService",
    "PneuService",
]
