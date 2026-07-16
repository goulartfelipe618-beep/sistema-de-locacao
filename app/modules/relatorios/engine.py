"""Motor de renderização PDF/CSV/XLSX para relatórios."""

from __future__ import annotations

import csv
import hashlib
import io
from typing import Any

from app.core.templating import templates


def render_csv(columns: list[str], rows: list[list[Any]]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(columns)
    for row in rows:
        writer.writerow(["" if v is None else v for v in row])
    return buf.getvalue().encode("utf-8-sig")


def render_xlsx(columns: list[str], rows: list[list[Any]]) -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Relatorio"
    ws.append(columns)
    for row in rows:
        ws.append(["" if v is None else v for v in row])
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def render_pdf_html(titulo: str, columns: list[str], rows: list[list[Any]], summary: dict) -> bytes:
    html = templates.env.get_template("relatorios/report_print.html").render(
        titulo=titulo,
        columns=columns,
        rows=rows,
        summary=summary,
    )
    try:
        from xhtml2pdf import pisa

        out = io.BytesIO()
        pisa.CreatePDF(html, dest=out, encoding="utf-8")
        return out.getvalue()
    except Exception:
        return html.encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


CONTENT_TYPES = {
    "pdf": "application/pdf",
    "csv": "text/csv; charset=utf-8",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
