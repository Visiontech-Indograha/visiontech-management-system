"""
app/services/pdf_service.py
Render dokumen SK: HTML (Jinja2) → PDF (WeasyPrint), dok 02 A-13. PDF hanya tampilan; sumber kebenaran
adalah snapshot + tanda tangannya (A-09). WeasyPrint butuh pustaka sistem (Pango) — tersedia di image
Linux/Docker; bila tidak ada, galat 503 yang jelas (bukan 500).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.errors import AppError

_ENV = Environment(loader=FileSystemLoader(Path(__file__).resolve().parent.parent / "templates"),
                   autoescape=select_autoescape(["html"]))
KIND_LABEL = {"INITIAL_ORDER": "SK", "REVISION": "Revisi SK", "ADDENDUM": "Adendum"}


def render_plan_document_html(document: Any, signatures: list[dict[str, Any]]) -> str:
    snapshot = document.snapshot if isinstance(document.snapshot, dict) else json.loads(document.snapshot)
    return _ENV.get_template("plan_document.html").render(
        doc=document, kind_label=KIND_LABEL.get(document.kind, document.kind),
        issued_at=f"{document.issued_at:%d-%m-%Y %H:%M}", plan=snapshot.get("plan", {}),
        team=snapshot.get("team", []), days=snapshot.get("days", []),
        attachments=snapshot.get("attachments", []), signatures=signatures,
        sha256=bytes(document.snapshot_sha256).hex())


def html_to_pdf(html: str) -> bytes:
    try:
        from weasyprint import HTML
    except (ImportError, OSError):
        raise AppError("PDF_UNAVAILABLE", "Layanan PDF belum tersedia di server ini.", status=503) from None
    pdf: bytes = HTML(string=html).write_pdf()
    return pdf
