"""Templat PDF resmi (M8): logo kop & QR verifikasi tertanam sebagai data URI (WeasyPrint tak mengambil URL luar)."""

from __future__ import annotations

import base64
from datetime import UTC, datetime

from app.modules.exports.services.builders.model import qty, tgl
from app.shared.documents.pdf_service import LOGO_DATA_URI, qr_data_uri, render_html


def test_completion_pdf_template_embeds_logo_and_qr() -> None:
    qr = qr_data_uri("http://localhost:5173/verify/work-completion/x?h=" + "ab" * 32)
    assert base64.b64decode(qr.split(",", 1)[1]).startswith(b"\x89PNG")
    order = {"client_name": "PHR", "project_title": "CCTV", "signature_hash": "ab" * 32}
    html = render_html("completion_report.html", o=order, number="PHR-01", points=[], bom=[], photos=[],
                       generated_at=datetime(2026, 10, 21, tzinfo=UTC), generated_by="pm", tgl=tgl, qty=qty,
                       leader_sig=None, pm_sig=None, qr=qr)
    assert LOGO_DATA_URI in html and qr in html
    assert "ab" * 32 in html
