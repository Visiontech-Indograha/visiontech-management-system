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


def render_html(template: str, *, logos: list[str] | None = None, **context: Any) -> str:
    """HTML dari templat. `logos` (data URI) = logo kop berurutan; kosong → logo Visiontech bawaan."""
    return _ENV.get_template(template).render(logos=logos or [LOGO_DATA_URI], **context)


def html_to_pdf(html: str) -> bytes:
    try:
        from weasyprint import HTML

        return bytes(HTML(string=html).write_pdf())
    except (ImportError, OSError, RuntimeError, ValueError):
        import re

        from PIL import Image as PILImage
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer

        from app.shared.documents.branding import VISIONTECH_LOGO

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4)
        clean_text = re.sub(r'<[^>]+>', ' ', html)
        styles = getSampleStyleSheet()
        story = []
        if VISIONTECH_LOGO.exists():
            try:
                pil_img = PILImage.open(VISIONTECH_LOGO)
                w, h = pil_img.size
                if w > 0 and h > 0:
                    aspect = h / float(w)
                    target_w = 4.8 * 28.3465
                    target_h = target_w * aspect
                    story.append(Image(str(VISIONTECH_LOGO), width=target_w, height=target_h))
                    story.append(Spacer(1, 10))
            except (OSError, ValueError):
                pass
        story.append(Paragraph('<b>Dokumen Resmi PT Visiontech Indograha</b>', styles['Heading1']))
        story.append(Spacer(1, 10))
        for pline in clean_text.splitlines()[:50]:
            if pline.strip():
                story.append(Paragraph(pline.strip()[:200], styles['Normal']))
        doc.build(story)
        return buf.getvalue()
