"""
app/services/pdf_service.py
Render dokumen SK: HTML (Jinja2) → PDF (WeasyPrint), dok 02 A-13. PDF hanya tampilan; sumber kebenaran
adalah snapshot + tanda tangannya (A-09). WeasyPrint butuh pustaka sistem (Pango) — tersedia di image
Linux/Docker; bila tidak ada, galat 503 yang jelas (bukan 500).
"""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.errors import AppError
from app.core.time import wib_text

_TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
_ENV = Environment(loader=FileSystemLoader(_TEMPLATES), autoescape=select_autoescape(["html"]))
_ENV.filters["wib"] = wib_text
# Logo kop SK sebagai data URI: WeasyPrint tidak perlu mengambil berkas/URL dari luar.
_LOGO = "data:image/png;base64," + base64.b64encode(
    (_TEMPLATES / "assets" / "logo-visiontech.png").read_bytes()).decode("ascii")
KIND_LABEL = {"INITIAL_ORDER": "SK", "REVISION": "Revisi SK", "ADDENDUM": "Adendum"}


def render_plan_document_html(document: Any, signatures: list[dict[str, Any]]) -> str:
    snapshot = document.snapshot if isinstance(document.snapshot, dict) else json.loads(document.snapshot)
    return _ENV.get_template("plan_document.html").render(
        doc=document, logo=_LOGO, kind_label=KIND_LABEL.get(document.kind, document.kind),
        issued_at=wib_text(document.issued_at), plan=snapshot.get("plan", {}),
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
