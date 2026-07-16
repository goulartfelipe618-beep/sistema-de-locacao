"""Porta para provedores de assinatura eletrônica (§16)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class SignatureProviderPort(Protocol):
    """Contrato para integração futura com ICP-Brasil / Clicksign / D4Sign."""

    def embed_signature(self, pdf_bytes: bytes, signature_image_b64: str) -> bytes:
        """Embute assinatura capturada no PDF final."""


class CanvasSignatureProvider:
    """Implementação inicial: assinatura simples em canvas (base64 PNG)."""

    def embed_signature(self, pdf_bytes: bytes, signature_image_b64: str) -> bytes:
        return pdf_bytes
