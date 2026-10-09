"""
app/services/pdf_service.py
Render dokumen SK: HTML (Jinja2) → PDF (WeasyPrint), dok 02 A-13. PDF hanya tampilan; sumber kebenaran
adalah snapshot + tanda tangannya (A-09). WeasyPrint butuh pustaka sistem (Pango) — tersedia di image
Linux/Docker; bila tidak ada, galat 503 yang jelas (bukan 500).
"""
from __future__ import annotations

import base64
import json
from datetime import date, timedelta
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
KIND_LABEL = {"INITIAL_ORDER": "Rencana Kerja", "REVISION": "Revisi", "ADDENDUM": "Revisi",
              "PERSONNEL_ADDENDUM": "Revisi"}


def kind_label_of(kind: str, version: int) -> str:
    """"Rencana Kerja" untuk versi awal; revisi diberi nomor urut ("Revisi ke-N", N = versi - 1)."""
    base = KIND_LABEL.get(kind, kind)
    return base if kind == "INITIAL_ORDER" else f"{base} ke-{max(int(version) - 1, 1)}"


CATEGORY_LABEL = {"INSTALASI": "Instalasi", "PEMELIHARAAN": "Pemeliharaan", "PERBAIKAN": "Perbaikan",
                  "SURVEI": "Survei", "LAINNYA": "Lainnya"}
DOCUMENT_STATUS_LABEL = {"AWAITING_ACCEPTANCE": "Menunggu tanda tangan", "EFFECTIVE": "Berlaku",
                         "SUPERSEDED": "Tidak berlaku", "REJECTED": "Ditolak", "WITHDRAWN": "Ditarik"}


_WEEKDAYS = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
_SHORT_MONTHS = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


def _compact_dates(isos: list[str]) -> str:
    """['2026-11-02','2026-11-03','2026-12-01'] → '2, 3 Nov 2026; 1 Des 2026'."""
    groups: dict[tuple[int, int], list[int]] = {}
    for iso in sorted(set(isos)):
        y, m, d = (int(x) for x in iso[:10].split("-"))
        groups.setdefault((y, m), []).append(d)
    return "; ".join(f"{', '.join(map(str, ds))} {_SHORT_MONTHS[m - 1]} {y}" for (y, m), ds in groups.items())


def _plan_view(plan: dict[str, Any], team: list[dict[str, Any]], days: list[dict[str, Any]]) -> dict[str, Any]:
    """Data tampilan dokumen dari snapshot (dokumen terbit) atau detail (pratinjau draf): baris jadwal per hari
    (jenis, lokasi, detail, pekerja), hari libur, dan jumlah hari bertugas tiap anggota tim."""
    names = {str(m.get("employee_id")): str(m.get("full_name")) for m in team}
    leader = next((str(m["full_name"]) for m in team if m.get("role_in_plan") == "LEADER"), None)
    members = [str(m["full_name"]) for m in team if m.get("role_in_plan") == "MEMBER"]
    duty: dict[str, list[str]] = {}
    rows = []
    for no, d in enumerate(days, start=1):
        iso = str(d["work_date"])[:10]
        if d.get("members") is not None:                 # snapshot dokumen: nama
            workers = [str(n) for n in d["members"]]
        elif d.get("member_employee_ids") is not None:   # detail draf: id
            workers = [names.get(str(i), str(i)) for i in d["member_employee_ids"]]
        else:                                            # tanpa daftar khusus = seluruh tim
            workers = members
        others = [w for w in workers if w != leader]
        for w in ([leader] if leader else []) + others:
            duty.setdefault(w, []).append(iso)
        tasks = []
        for t in d.get("tasks", []):
            if isinstance(t, str):
                tasks.append({"title": t, "description": "", "files": []})
            else:
                files = [f if isinstance(f, str) else str(f.get("file_name", "")) for f in t.get("files") or []]
                tasks.append({"title": t.get("title", ""), "description": t.get("description") or "", "files": files})
        y, m, dd = (int(x) for x in iso.split("-"))
        rows.append({
            "no": no, "date": iso, "weekday": _WEEKDAYS[date(y, m, dd).weekday()],
            "work_type": d.get("work_type_name") or plan.get("work_type_name") or "-",
            "work_type_custom": bool(d.get("work_type_name")),
            "location": d.get("site_name") or plan.get("location_text") or "-",
            "location_custom": bool(d.get("site_name")),
            "tasks": tasks, "workers": others,
        })
    start, end = str(plan.get("period_start") or "")[:10], str(plan.get("period_end") or "")[:10]
    holidays: list[str] = []
    if start and end:
        given = {r["date"] for r in rows}
        cur, last = date.fromisoformat(start), date.fromisoformat(end)
        while cur <= last and len(holidays) < 366:
            if cur.isoformat() not in given:
                holidays.append(cur.isoformat())
            cur += timedelta(days=1)
    team_rows = [{**m, "days": len(duty.get(str(m.get("full_name")), [])),
                  "dates": _compact_dates(duty.get(str(m.get("full_name")), []))} for m in team]
    return {"rows": rows, "holidays": holidays, "holidays_text": _compact_dates(holidays), "team_rows": team_rows,
            "work_days": len(rows)}


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
        doc=document, logo=_LOGO, kind_label=kind_label_of(document.kind, document.version),
        issued_at=wib_text(document.issued_at), plan=snapshot.get("plan", {}),
        team=snapshot.get("team", []), days=snapshot.get("days", []), assets=snapshot.get("assets", []),
        attachments=snapshot.get("attachments", []), signatures=signatures, categories=CATEGORY_LABEL,
        status_label=DOCUMENT_STATUS_LABEL.get(str(status)) if status else None,
        sha256=bytes(document.snapshot_sha256).hex(), preview=False,
        **_plan_view(snapshot.get("plan", {}), snapshot.get("team", []), snapshot.get("days", [])))


def render_plan_preview_html(snapshot: dict[str, Any]) -> str:
    """Pratinjau A4 draf SK ("Sunting SK", flowchart SK2-C) — format sama dengan dokumen terbit, tanpa TTD."""
    plan = snapshot.get("plan", {})
    doc = {"number": plan.get("number"), "title": plan.get("title"), "version": plan.get("revision", 1)}
    return _ENV.get_template("plan_document.html").render(
        doc=doc, logo=_LOGO, kind_label="Rencana Kerja", issued_at=None, plan=plan, team=snapshot.get("team", []),
        days=snapshot.get("days", []), assets=snapshot.get("assets", []),
        attachments=snapshot.get("attachments", []), signatures=[], categories=CATEGORY_LABEL,
        status_label="Draf", sha256=None, preview=True,
        **_plan_view(plan, snapshot.get("team", []), snapshot.get("days", [])))


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
