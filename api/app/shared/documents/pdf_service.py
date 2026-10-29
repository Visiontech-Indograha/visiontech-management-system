"""
app/shared/documents/pdf_service.py
HTML (Jinja2) → PDF (WeasyPrint) untuk dokumen resmi. PDF hanya tampilan; sumber kebenaran tetap data + sidik
SHA-256-nya. WeasyPrint butuh pustaka sistem (Pango) — tersedia di image Linux/Docker; bila tidak ada, galat 503
yang jelas (bukan 500).
"""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any

import qrcode
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.errors import AppError
from app.core.time import wib_text

_TEMPLATES = Path(__file__).resolve().parent / "templates"
_ENV = Environment(loader=FileSystemLoader(_TEMPLATES), autoescape=select_autoescape(["html"]))
_ENV.filters["wib"] = wib_text
# Logo kop sebagai data URI: WeasyPrint tidak perlu mengambil berkas/URL dari luar.
LOGO_DATA_URI = "data:image/png;base64," + base64.b64encode(
    (_TEMPLATES / "assets" / "logo-visiontech.png").read_bytes()
).decode("ascii")


def data_uri(image: bytes, mime: str = "image/jpeg") -> str:
    return f"data:{mime};base64," + base64.b64encode(image).decode("ascii")


def qr_data_uri(text: str) -> str:
    """QR (PNG) untuk tautan verifikasi dokumen."""
    buf = io.BytesIO()
    qrcode.make(text, box_size=6, border=2).save(buf, format="PNG")
    return data_uri(buf.getvalue(), "image/png")


def render_html(template: str, *, logo: str | None = None, **context: Any) -> str:
    """HTML dari templat. `logo` (data URI) menggantikan logo default kop."""
    return _ENV.get_template(template).render(logo=logo or LOGO_DATA_URI, **context)


def html_to_pdf(html: str) -> bytes:
    """HTML → PDF. Pustaka sistem WeasyPrint tidak ada → AppError 503 `PDF_UNAVAILABLE`."""
    try:
        from weasyprint import HTML
    except (ImportError, OSError):
        raise AppError(
            "PDF_UNAVAILABLE", "Pembuatan PDF sedang tidak tersedia. Coba lagi nanti atau hubungi admin.", status=503
        ) from None
    pdf: bytes = HTML(string=html).write_pdf()
    return pdf
