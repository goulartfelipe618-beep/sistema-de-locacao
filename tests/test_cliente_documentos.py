"""Testes de upload de documentos do cliente."""

from __future__ import annotations

import pytest

from app.core.exceptions import ValidationError
from app.modules.cadastros.cliente_documentos import ClienteDocumentoService


def test_validate_upload_rejects_large_file() -> None:
    with pytest.raises(ValidationError, match="10 MB"):
        ClienteDocumentoService.validate_upload("cnh.pdf", "application/pdf", 11 * 1024 * 1024)


def test_validate_upload_rejects_bad_extension() -> None:
    with pytest.raises(ValidationError, match="Formato"):
        ClienteDocumentoService.validate_upload("virus.exe", "application/octet-stream", 100)


def test_validate_upload_accepts_pdf() -> None:
    ClienteDocumentoService.validate_upload("cnh.pdf", "application/pdf", 1024)
