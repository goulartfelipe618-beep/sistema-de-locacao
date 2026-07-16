"""Renderização HTML → PDF (§16)."""

from __future__ import annotations

import hashlib
import io
from typing import Any

from app.core.templating import templates


def render_html(template_path: str, context: dict[str, Any]) -> str:
    """Renderiza template Jinja2 para HTML."""
    return templates.env.get_template(template_path).render(**context)


def html_to_pdf(html: str) -> bytes:
    """Converte HTML em bytes PDF via xhtml2pdf."""
    try:
        from xhtml2pdf import pisa

        out = io.BytesIO()
        pisa.CreatePDF(html, dest=out, encoding="utf-8")
        data = out.getvalue()
        if data.startswith(b"%PDF"):
            return data
    except Exception:
        pass
    return html.encode("utf-8")


def render_pdf(template_path: str, context: dict[str, Any]) -> bytes:
    """Pipeline completo: template → HTML → PDF."""
    html = render_html(template_path, context)
    return html_to_pdf(html)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
