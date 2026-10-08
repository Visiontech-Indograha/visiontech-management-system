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
_MONTHS = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober",
           "November", "Desember"]


def _tgl(value: Any) -> str:
    """'2026-10-03' / date → '3 Oktober 2026' (dokumen SK)."""
    text = str(value or "")[:10]
    try:
        y, m, d = (int(x) for x in text.split("-"))
        return f"{d} {_MONTHS[m - 1]} {y}"
    except (ValueError, IndexError):
        return text


_ENV.filters["tgl"] = _tgl
# Logo kop SK sebagai data URI: WeasyPrint tidak perlu mengambil berkas/URL dari luar.
_LOGO = "data:image/png;base64," + base64.b64encode(
    (_TEMPLATES / "assets" / "logo-visiontech.png").read_bytes()).decode("ascii")
KIND_LABEL = {"INITIAL_ORDER": "SK", "REVISION": "Revisi SK", "ADDENDUM": "Adendum"}


CATEGORY_LABEL = {"INSTALASI": "Instalasi", "PEMELIHARAAN": "Pemeliharaan", "PERBAIKAN": "Perbaikan",
                  "SURVEI": "Survei", "LAINNYA": "Lainnya"}
DOCUMENT_STATUS_LABEL = {"AWAITING_ACCEPTANCE": "Menunggu tanda tangan", "EFFECTIVE": "Berlaku",
                         "SUPERSEDED": "Tidak berlaku", "REJECTED": "Ditolak", "WITHDRAWN": "Ditarik"}


def render_plan_document_html(document: Any, signatures: list[dict[str, Any]]) -> str:
    """
    Menghasilkan HTML dari sebuah dokumen SK yang sudah ada di sistem.
    Digunakan untuk mencetak PDF yang menjadi sumber kebenaran (source of truth).

    Args:
        document: Baris data dokumen SK dari database.
        signatures: Daftar tanda tangan yang relevan dengan dokumen ini.

    Returns:
        str: String HTML dokumen.
    """
    snapshot = document.snapshot if isinstance(document.snapshot, dict) else json.loads(document.snapshot)
    status = getattr(document, "status", None)
    return _ENV.get_template("plan_document.html").render(
        doc=document, logo=_LOGO, kind_label=KIND_LABEL.get(document.kind, document.kind),
        issued_at=wib_text(document.issued_at), plan=snapshot.get("plan", {}),
        team=snapshot.get("team", []), days=snapshot.get("days", []), assets=snapshot.get("assets", []),
        attachments=snapshot.get("attachments", []), signatures=signatures, categories=CATEGORY_LABEL,
        status_label=DOCUMENT_STATUS_LABEL.get(str(status)) if status else None,
        sha256=bytes(document.snapshot_sha256).hex(), preview=False)


def render_plan_preview_html(snapshot: dict[str, Any]) -> str:
    """Pratinjau A4 draf SK ("Sunting SK", flowchart SK2-C) — format sama dengan dokumen terbit, tanpa TTD."""
    plan = snapshot.get("plan", {})
    doc = {"number": plan.get("number"), "title": plan.get("title"), "version": plan.get("revision", 1)}
    return _ENV.get_template("plan_document.html").render(
        doc=doc, logo=_LOGO, kind_label="SK", issued_at=None, plan=plan, team=snapshot.get("team", []),
        days=snapshot.get("days", []), assets=snapshot.get("assets", []),
        attachments=snapshot.get("attachments", []), signatures=[], categories=CATEGORY_LABEL,
        status_label="Draf", sha256=None, preview=True)


INCIDENT_CATEGORY = {"K3_RINGAN": "K3 ringan", "K3_BERAT": "K3 berat", "K3_LINGKUNGAN": "K3 lingkungan",
                     "K3_HAMPIR": "Hampir celaka", "ASET": "Aset"}
INCIDENT_SEVERITY = {"RENDAH": "Rendah", "SEDANG": "Sedang", "TINGGI": "Tinggi", "KRITIS": "Kritis"}


def render_final_report_html(plan: Any, signatures: list[dict[str, Any]]) -> str:
    """Laporan akhir yang disetujui (R-19, P6-4) — dari snapshot yang ditandatangani, bukan data hidup."""
    snap = plan.snapshot if isinstance(plan.snapshot, dict) else json.loads(plan.snapshot)
    incidents = [{**i, "category": INCIDENT_CATEGORY.get(i["category"], i["category"]),
                  "severity": INCIDENT_SEVERITY.get(i["severity"], i["severity"])} for i in snap.get("incidents", [])]
    return _ENV.get_template("final_report.html").render(
        logo=_LOGO, number=f"{plan.number}-LA", plan=snap.get("plan", {}), team=snap.get("team", []),
        report=snap.get("report", {}), approval=snap.get("approval", {}), incidents=incidents,
        signatures=signatures, sha256=bytes(plan.snapshot_sha256).hex())


def render_bast_html(record: Any) -> str:
    """Berita acara serah terima pengembalian aset (P6-4)."""
    return _ENV.get_template("bast.html").render(logo=_LOGO, r=record)


def html_to_pdf(html: str) -> bytes:
    """
    Mengubah konten HTML menjadi file biner PDF menggunakan pustaka WeasyPrint.

    Args:
        html: Teks HTML mentah.

    Returns:
        bytes: Data biner file PDF.

    Raises:
        AppError: Jika dependensi sistem WeasyPrint tidak ditemukan.
    """
    try:
        from weasyprint import HTML
    except (ImportError, OSError):
        raise AppError("PDF_UNAVAILABLE", "Pembuatan PDF sedang tidak tersedia. Coba lagi nanti atau hubungi admin.",
                       status=503) from None
    pdf: bytes = HTML(string=html).write_pdf()
    return pdf


REPORT_STATUS_LABEL = {"DRAFT": "Draf", "SUBMITTED": "Dikirim", "CHANGES_REQUESTED": "Perlu perbaikan",
                       "APPROVED": "Disetujui"}


def render_report_html(title: str, header: Any, report: Any, *, period: Any, members: list[Any]) -> str:
    """Dokumen A4 laporan harian/mingguan (alur SK v2 PR2) — dibaca di web & HP setelah disetujui PM."""
    status = REPORT_STATUS_LABEL.get(report.status, report.status)
    if report.status == "SUBMITTED" and getattr(report, "resubmitted", False):
        status = "Dikirim ulang"
    return _ENV.get_template("report_document.html").render(
        logo=_LOGO, title=title, plan=header, report=report, status_label=status, period=period,
        members=members, categories=CATEGORY_LABEL)
