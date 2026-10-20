"""Kop PDF SK memuat logo Visiontech (temuan uji: PDF belum berlogo). Logo disematkan sebagai
data URI agar WeasyPrint tidak perlu mengambil berkas/URL dari luar."""
from __future__ import annotations

import base64
from datetime import UTC, datetime
from types import SimpleNamespace

from app.shared.documents.pdf_service import render_plan_document_html


def _doc() -> SimpleNamespace:
    return SimpleNamespace(
        title="Perawatan CCTV", number="SK-202609-01", kind="INITIAL_ORDER", version=1,
        issued_at=datetime(2026, 9, 26, 3, 0, tzinfo=UTC),
        snapshot={"plan": {"location_text": "Dumai", "period_start": "2026-09-26", "period_end": "2026-09-26"}},
        snapshot_sha256=b"\x01" * 32,
    )


def test_pdf_header_embeds_logo_png() -> None:
    html = render_plan_document_html(_doc(), [])
    marker = 'src="data:image/png;base64,'
    assert marker in html
    encoded = html.split(marker, 1)[1].split('"', 1)[0]
    assert base64.b64decode(encoded).startswith(b"\x89PNG")
    assert 'alt="Visiontech Indograha"' in html
