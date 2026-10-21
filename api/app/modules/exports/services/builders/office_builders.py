"""
app/modules/exports/services/builders/office_builders.py
Excel (rekap BoQ & uang makan) dan PowerPoint (slide progres) — docs/35 §8.
"""
from __future__ import annotations

import io
from collections.abc import Sequence
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet
from pptx import Presentation
from pptx.presentation import Presentation as PptxPresentation
from pptx.util import Cm, Pt

from app.modules.exports.services.builders.model import COMPANY, CompletionReport, PeriodicReport, qty, tgl
from app.shared.documents.docx_kit import LOGO

_HEAD = PatternFill("solid", fgColor="1E293B")


def _sheet(ws: Worksheet, title: str, subtitle: str, headers: Sequence[str], rows: Sequence[Sequence[Any]],
           widths: Sequence[int]) -> None:
    ws["A1"], ws["A2"] = title, subtitle
    ws["A1"].font, ws["A2"].font = Font(bold=True, size=13), Font(italic=True, color="64748B")
    for col, h in enumerate(headers, start=1):
        cell = ws.cell(row=4, column=col, value=h)
        cell.font, cell.fill = Font(bold=True, color="FFFFFF"), _HEAD
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    for r, row in enumerate(rows, start=5):
        for c, value in enumerate(row, start=1):
            ws.cell(row=r, column=c, value=value).alignment = Alignment(vertical="top", wrap_text=True)
    for col, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(col)].width = w
    ws.freeze_panes = "A5"


def _xlsx(wb: Workbook) -> bytes:
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def completion_xlsx(r: CompletionReport) -> bytes:
    o = r.order
    sub = f"{o.get('client_name') or '-'} · {o.get('project_title') or '-'} · {r.number}"
    wb = Workbook()
    _sheet(wb.active, "Bill of Quantity", sub,
           ["No", "Kode", "Material", "Satuan", "Estimasi", "Aktual", "Selisih", "Kategori", "Catatan"],
           [(i, b.get("material_code"), b.get("material_name"), b.get("unit"), float(b.get("estimated_qty") or 0),
             float(b.get("actual_qty") or 0), float(b.get("actual_qty") or 0) - float(b.get("estimated_qty") or 0),
             b.get("category"), b.get("notes")) for i, b in enumerate(r.bom, start=1)],
           [5, 12, 36, 9, 10, 10, 10, 16, 30])
    wb.active.title = "BoQ"
    _sheet(wb.create_sheet("Titik"), "Realisasi per Titik", sub,
           ["No", "Tanggal", "Tim", "Titik", "Lokasi", "Fase", "Target", "Realisasi", "Progres %", "Status", "Remark"],
           [(i, p.work_date, p.team_name, p.title, p.location, p.phase_label, p.target, p.completed, p.progress,
             p.status_label, p.notes) for i, p in enumerate(r.points, start=1)],
           [5, 12, 18, 30, 24, 13, 9, 10, 10, 14, 36])
    return _xlsx(wb)


def periodic_xlsx(r: PeriodicReport) -> bytes:
    sub = f"Divisi {r.division_name} · {tgl(r.start)} s.d. {tgl(r.end)}"
    wb = Workbook()
    _sheet(wb.active, "Rekap Jadwal Harian", sub,
           ["Tanggal", "Tim", "Lokasi", "Status", "Item", "Selesai", "Digeser", "Rata-rata progres %", "Pekerjaan"],
           [(d.work_date, d.team_name, d.site_name, d.status, d.items, d.items_done, d.items_shifted, d.avg_progress,
             d.titles) for d in r.days],
           [12, 20, 24, 12, 7, 8, 8, 12, 60])
    wb.active.title = "Jadwal"
    _sheet(wb.create_sheet("BoQ"), "Bill of Quantity", sub,
           ["Order", "Klien", "Pekerjaan", "Kode", "Material", "Satuan", "Estimasi", "Aktual", "Selisih"],
           [(b.order_number, b.client_name, b.project_title, b.material_code, b.material_name, b.unit,
             b.estimated_qty, b.actual_qty, b.actual_qty - b.estimated_qty) for b in r.boq],
           [14, 22, 28, 12, 32, 9, 10, 10, 10])
    meal_rows: list[Sequence[Any]] = [(m.employee_no, m.full_name, m.in_city_days, m.out_city_days, m.total_amount,
                                       m.pending_days) for m in r.meal]
    meal_rows.append(("", "TOTAL", sum(m.in_city_days for m in r.meal), sum(m.out_city_days for m in r.meal),
                      sum(m.total_amount for m in r.meal), sum(m.pending_days for m in r.meal)))
    _sheet(wb.create_sheet("Uang Makan"), "Rekap Uang Makan (absensi sah)", sub,
           ["NIK", "Nama", "Hari dalam kota", "Hari luar kota", "Total (Rp)", "Menunggu OM (hari)"],
           meal_rows, [14, 30, 14, 14, 16, 16])
    return _xlsx(wb)


# ── PowerPoint ──────────────────────────────────────────────────────────────
def _deck() -> PptxPresentation:
    prs = Presentation()
    prs.slide_width, prs.slide_height = Cm(33.867), Cm(19.05)  # 16:9
    return prs


def _title_slide(prs: PptxPresentation, title: str, subtitle: str) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = title
    slide.placeholders[1].text = subtitle
    if LOGO.exists():
        slide.shapes.add_picture(str(LOGO), Cm(1.2), Cm(1.0), height=Cm(2.0))


def _bullets(prs: PptxPresentation, title: str, lines: Sequence[str]) -> Any:
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = title
    body = slide.placeholders[1].text_frame
    body.clear()
    for i, line in enumerate(lines or ["-"]):
        p = body.paragraphs[0] if i == 0 else body.add_paragraph()
        p.text = line
        p.font.size = Pt(16)
    return slide


def _table(prs: PptxPresentation, title: str, headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    slide.shapes.title.text = title
    shape = slide.shapes.add_table(len(rows) + 1, len(headers), Cm(1.2), Cm(4.0), Cm(31.4), Cm(1.0 * (len(rows) + 1)))
    table = shape.table
    for c, h in enumerate(headers):
        table.cell(0, c).text = h
    for r_i, row in enumerate(rows, start=1):
        for c, v in enumerate(row):
            table.cell(r_i, c).text = "-" if v in (None, "") else str(v)
    for row in table.rows:
        for cell in row.cells:
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(11)


def _pptx(prs: PptxPresentation) -> bytes:
    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


def completion_pptx(r: CompletionReport) -> bytes:
    o = r.order
    prs = _deck()
    _title_slide(prs, o.get("project_title") or "Laporan Pekerjaan",
                 f"{COMPANY} · {o.get('client_name') or '-'} · {r.number}")
    done = sum(1 for p in r.points if p.status == "DONE")
    _bullets(prs, "Ringkasan", [
        f"Periode: {tgl(o.get('start_work_date'))} s.d. {tgl(o.get('end_work_date'))}",
        f"Titik selesai: {done} dari {len(r.points)}",
        f"Volume: {qty(o.get('completed_target_unit'))} / {qty(o.get('total_target_unit'))} "
        f"{o.get('unit_measure') or ''}",
        f"Ringkasan: {o.get('summary_notes') or '-'}",
        *([f"Kendala: {o['obstacles']}"] if o.get("obstacles") else []),
    ])
    for start in range(0, len(r.points), 10):
        _table(prs, "Progres per Titik", ["Tanggal", "Titik", "Fase", "Realisasi", "Status"], [
            (tgl(p.work_date), p.title, p.phase_label, f"{qty(p.completed)} / {qty(p.target)}", p.status_label)
            for p in r.points[start:start + 10]
        ])
    for p in r.points:
        if not p.photos:
            continue
        slide = _bullets(prs, p.title, [f"{p.phase_label} · {p.status_label}", f"Remark: {p.notes or '-'}"])
        for i, ph in enumerate(p.photos[:2]):
            slide.shapes.add_picture(io.BytesIO(ph.image), Cm(14.5 + i * 9.6), Cm(5.0), width=Cm(9.0))
    if r.bom:
        _table(prs, "Material (BoM)", ["Material", "Estimasi", "Aktual", "Satuan"], [
            (b.get("material_name"), qty(b.get("estimated_qty")), qty(b.get("actual_qty")), b.get("unit"))
            for b in r.bom[:12]
        ])
    return _pptx(prs)


def periodic_pptx(r: PeriodicReport) -> bytes:
    prs = _deck()
    _title_slide(prs, f"Laporan Mingguan Divisi {r.division_name}", f"{COMPANY} · {tgl(r.start)} s.d. {tgl(r.end)}")
    total = sum(d.items for d in r.days)
    done = sum(d.items_done for d in r.days)
    _bullets(prs, "Ringkasan", [
        f"Jadwal harian: {len(r.days)}",
        f"Item selesai: {done} dari {total}",
        f"Item digeser / menunggu geser: {sum(d.items_shifted for d in r.days)}",
        f"Uang makan (absensi sah): Rp {sum(m.total_amount for m in r.meal):,.0f}".replace(",", "."),
    ])
    for start in range(0, len(r.days), 10):
        _table(prs, "Jadwal per Hari", ["Tanggal", "Tim", "Lokasi", "Status", "Selesai / Item", "Progres %"], [
            (tgl(d.work_date), d.team_name, d.site_name, d.status, f"{d.items_done} / {d.items}", d.avg_progress)
            for d in r.days[start:start + 10]
        ])
    return _pptx(prs)
