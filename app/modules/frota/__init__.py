"""Módulo Frota — veículos e cadastros mestres (categorias, marcas, modelos...)."""

from app.modules.frota.service import (
    AcessoriosService,
    CategoriasService,
    CombustiveisService,
    DocumentoService,
    FotoService,
    MarcasService,
    ModelosService,
    TelemetriaService,
    VeiculoService,
)

__all__ = [
    "AcessoriosService",
    "CategoriasService",
    "CombustiveisService",
    "DocumentoService",
    "FotoService",
    "MarcasService",
    "ModelosService",
    "TelemetriaService",
    "VeiculoService",
]
