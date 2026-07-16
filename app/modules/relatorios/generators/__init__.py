"""Geradores de relatórios — reexportação."""

from app.modules.relatorios.data import ReportData
from app.modules.relatorios.generators.run import gerar

__all__ = ["ReportData", "gerar"]
