"""
app/modules/exports/services/builders/pdf_builders.py
PDF resmi BAST dengan QR verifikasi (docs/35 §8). Hanya untuk order yang sudah disahkan PM.
"""
from __future__ import annotations

from app.modules.exports.services.builders.model import CompletionReport, qty, tgl
from app.shared.documents.branding import COMPANY_BOX_PX, fit_contain_png
from app.shared.documents.pdf_service import data_uri, html_to_pdf, qr_data_uri, render_html


def completion_pdf(r: CompletionReport) -> bytes:
    photos = [(label, data_uri(image)) for label, image in r.all_photos[:12]]
    html = render_html(
        "completion_report.html",
        o=r.order, number=r.number, points=r.points, bom=r.bom, photos=photos,
        generated_at=r.generated_at, generated_by=r.generated_by, tgl=tgl, qty=qty,
        leader_sig=data_uri(r.leader_signature, "image/png") if r.leader_signature else None,
        pm_sig=data_uri(r.pm_signature, "image/png") if r.pm_signature else None,
        qr=qr_data_uri(r.verify_url) if r.verify_url else None,
        logos=[data_uri(fit_contain_png(logo, COMPANY_BOX_PX), "image/png") for logo in r.logos if logo],
    )
    return html_to_pdf(html)
