"""
app/modules/exports/services/builders/office_builders.py
Excel (rekap rincian volume dan biaya & uang makan) dan PowerPoint (slide progres) — docs/35 §8.
"""
from __future__ import annotations

import io
from collections.abc import Sequence
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet
from pptx.presentation import Presentation as PptxPresentation

from app.modules.exports.services.builders import pptx_theme as theme
from app.modules.exports.services.builders.model import (
    COMPANY,
    AssetLine,
    CompletionReport,
    DailyReport,
    PeriodicReport,
    TeamWeekReport,
    month_label,
    omitted_note,
    plan_status_label,
    qty,
    rupiah,
    tgl,
)
from app.modules.exports.services.builders.survey_template import SurveyDoc

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
    _sheet(wb.active, "Rincian Volume dan Biaya", sub,
           ["No", "Kode", "Material", "Satuan", "Estimasi", "Aktual", "Selisih", "Kategori", "Catatan"],
           [(i, b.get("material_code"), b.get("material_name"), b.get("unit"), float(b.get("estimated_qty") or 0),
             float(b.get("actual_qty") or 0), float(b.get("actual_qty") or 0) - float(b.get("estimated_qty") or 0),
             b.get("category"), b.get("notes")) for i, b in enumerate(r.bom, start=1)],
           [5, 12, 36, 9, 10, 10, 10, 16, 30])
    wb.active.title = "Rincian Volume dan Biaya"
    _sheet(wb.create_sheet("Titik"), "Realisasi per Titik", sub,
           ["No", "Tanggal", "Tim", "Titik", "Lokasi", "Fase", "Target", "Realisasi", "Progres %", "Status", "Remark"],
           [(i, p.work_date, p.team_name, p.title, p.location, p.phase_label, p.target, p.completed, p.progress,
             p.status_label, p.notes) for i, p in enumerate(r.points, start=1)],
           [5, 12, 18, 30, 24, 13, 9, 10, 10, 14, 36])
    return _xlsx(wb)


def periodic_xlsx(r: PeriodicReport) -> bytes:
    sub = f"{r.division_name} · {tgl(r.start)} s.d. {tgl(r.end)}"
    wb = Workbook()
    _sheet(wb.active, "Rekap Jadwal Harian", sub,
           ["Tanggal", "Tim", "Lokasi", "Status", "Item", "Selesai", "Digeser", "Rata-rata progres %", "Pekerjaan"],
           [(d.work_date, d.team_name, d.site_name, plan_status_label(d.status), d.items, d.items_done,
             d.items_shifted, d.avg_progress,
             d.titles) for d in r.days],
           [12, 20, 24, 12, 7, 8, 8, 12, 60])
    wb.active.title = "Jadwal"
    _sheet(wb.create_sheet("Rincian Volume dan Biaya"), "Rincian Volume dan Biaya", sub,
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


# ── PowerPoint (tema: pptx_theme) ────────────────────────────────────────────
def _status_pct(points: Sequence[Any]) -> int:
    if not points:
        return 0
    return round(100 * sum(1.0 if p.status == "DONE" else min(1.0, (p.completed or 0) / (p.target or 1))
                           for p in points) / len(points))


def _phase_rows(points: Sequence[Any]) -> list[tuple[str, int, str]]:
    counts: dict[str, int] = {}
    labels: dict[str, str] = {}
    for p in points:
        counts[p.phase] = counts.get(p.phase, 0) + 1
        labels[p.phase] = p.phase_label
    return [(labels[ph], n, theme.PHASE_COLOR.get(ph, (theme.NAVY, ""))[0]) for ph, n in counts.items()]


def _points_table(prs: PptxPresentation, title: str, kicker: str, points: Sequence[Any], footer: str) -> None:
    for start in range(0, len(points), 12):
        chunk = points[start:start + 12]
        slide = theme.page(prs, title, kicker, footer=footer)
        theme.table(slide, ["Tanggal", "Pekerjaan", "Jenis", "Dikerjakan", "Status"],
                    [(tgl(p.work_date), p.title, p.phase_label, f"{qty(p.completed)} / {qty(p.target)}",
                      p.status_label) for p in chunk],
                    [4.6, 13.5, 4.2, 3.8, 5.2], status_col=4, statuses=[p.status for p in chunk])


def _work_slides(prs: PptxPresentation, points: Sequence[Any], footer: str) -> None:
    for p in points:
        theme.work_slide(
            prs, kicker=f"{tgl(p.work_date)} · {p.location}", title=p.title, phase=p.phase,
            phase_label=p.phase_label, status=p.status, status_label=p.status_label, note=p.notes or "",
            progress=f"Dikerjakan {qty(p.completed)} dari {qty(p.target)}",
            photos=[(ph.label, ph.image) for ph in p.photos], footer=footer,
        )


def _summary(prs: PptxPresentation, points: Sequence[Any], kicker: str, footer: str, side_title: str,
             side_text: str) -> None:
    done = sum(1 for p in points if p.status == "DONE")
    slide = theme.page(prs, "Ringkasan", kicker, footer=footer)
    theme.kpis(slide, [
        (f"{_status_pct(points)}%", "Kemajuan keseluruhan", theme.NAVY),
        (f"{done}/{len(points)}", "Pekerjaan selesai", "1E6B43"),
        (str(len({p.work_date for p in points})), "Hari kerja", "3569A0"),
        (str(sum(len(p.photos) for p in points)), "Foto dokumentasi", "C7892A"),
    ])
    theme.text(slide, 1.3, 8.5, 15, 0.8, "Jenis pekerjaan", size=13, color=theme.NAVY, bold=True)
    theme.bars(slide, _phase_rows(points), x=1.3, y=9.4, w=15.0)
    theme.text(slide, 17.5, 8.5, 15, 0.8, side_title, size=13, color=theme.NAVY, bold=True)
    theme.text(slide, 17.5, 9.4, 15.1, 7.5, side_text, size=12, color=theme.INK)


def _omitted_slide(prs: PptxPresentation, count: int, footer: str) -> None:
    """Catatan bila sebagian foto tidak disertakan (batas jumlah foto per dokumen)."""
    note = omitted_note(count)
    if note:
        slide = theme.page(prs, "Catatan foto", "Dokumentasi", footer=footer)
        theme.text(slide, 1.3, 4.5, 31, 2.0, note, size=16, color=theme.INK)


def completion_pptx(r: CompletionReport, *, badge: str = "Laporan pekerjaan klien",
                    only_points: Sequence[Any] | None = None) -> bytes:
    o = r.order
    points = list(r.points if only_points is None else only_points)
    prs = theme.deck(r.logos)
    footer = f"{o.get('project_title') or 'Laporan pekerjaan'} · {o.get('client_name') or ''}"
    theme.cover(prs, o.get("project_title") or "Laporan Pekerjaan",
                f"{o.get('client_name') or '-'} · {tgl(o.get('start_work_date'))} s.d. {tgl(o.get('end_work_date'))}",
                f"{COMPANY} · No. {r.number}", badge=badge)
    note = f"{o.get('summary_notes') or '-'}"
    if o.get("obstacles"):
        note += f"\n\nKendala: {o['obstacles']}"
    _summary(prs, points, o.get("client_name") or "", footer, "Ringkasan & kendala", note)
    _points_table(prs, "Kemajuan per pekerjaan", "Daftar pekerjaan", points, footer)
    _work_slides(prs, [p for p in points if p.photos], footer)
    _omitted_slide(prs, r.omitted_photos, footer)
    for start in range(0, len(r.bom), 12):
        slide = theme.page(prs, "Daftar material", "Material terpakai", footer=footer)
        theme.table(slide, ["Material", "Rencana", "Terpakai", "Satuan"],
                    [(b.get("material_name"), qty(b.get("estimated_qty")), qty(b.get("actual_qty")), b.get("unit"))
                     for b in r.bom[start:start + 12]], [16.0, 5.0, 5.0, 5.3])
    theme.closing(prs, f"{COMPANY} · {o.get('client_name') or ''}")
    return theme.save(prs)


def bast_pptx(r: CompletionReport) -> bytes:
    return completion_pptx(r, badge="Berita Acara Serah Terima")


def order_sheet_pptx(r: CompletionReport) -> bytes:
    return completion_pptx(r, badge="Surat tugas pekerjaan")


def survey_report_pptx(r: CompletionReport) -> bytes:
    return completion_pptx(r, badge="Laporan survei", only_points=r.survey_points)


def daily_report_pptx(r: DailyReport) -> bytes:
    """Laporan harian satu jadwal (PowerPoint): isi setara dokumen Word-nya."""
    prs = theme.deck(r.logos)
    footer = f"{r.team_name} · {tgl(r.work_date)}"
    members = sorted({m.full_name for m in r.roster if not m.is_leader})
    theme.cover(prs, f"Laporan Harian\n{r.team_name}", f"{tgl(r.work_date)} · {r.division_name}",
                f"{COMPANY} · Ketua tim: {r.leader_name}", badge="Laporan harian", emblem=r.team_name)
    side = [f"Status jadwal: {plan_status_label(r.status)}", f"Lokasi: {r.site_name or '-'}",
            f"Ketua: {r.leader_name}", f"Anggota: {', '.join(members) or '-'}", "",
            f"Laporan ketua tim: {r.summary or 'Belum ada laporan ringkasan dari ketua tim.'}"]
    if r.obstacles:
        side.append(f"Kendala: {r.obstacles}")
    _summary(prs, r.points, r.division_name, footer, "Informasi jadwal & laporan ketua", "\n".join(side))
    _points_table(prs, "Item pekerjaan hari ini", r.team_name, r.points, footer)
    _assets_slide(prs, r.assets, footer)
    _work_slides(prs, r.points, footer)
    _omitted_slide(prs, r.omitted_photos, footer)
    theme.closing(prs, f"{r.team_name} · {COMPANY}")
    return theme.save(prs)


def survey_pptx(d: SurveyDoc) -> bytes:
    """Laporan survei (PowerPoint): sampul, informasi, satu slide per titik (foto + keterangan), rincian."""
    prs = theme.deck()
    title = d.project_title or d.client
    footer = f"Laporan Survei · {d.client}"
    theme.cover(prs, f"Laporan Survei\n{title}", f"{d.client} · {d.date_text}", f"{COMPANY} · {d.team_name}",
                badge="Laporan survei")
    slide = theme.page(prs, "Informasi survei", d.client, footer=footer)
    theme.text(slide, 1.3, 4.0, 31, 4.5,
               "\n".join([f"Tanggal: {d.date_text}", f"Lokasi: {d.location}", f"Tujuan: {d.purpose}",
                          f"Tim: {d.team_name} (ketua: {d.leader_name or '-'})",
                          f"Anggota: {', '.join(d.member_names) or '-'}"]), size=13, color=theme.INK)
    theme.text(slide, 1.3, 9.0, 31, 8.0, "\n\n".join([*d.activities, *d.narrative]), size=12, color=theme.INK)
    for p in d.points:
        extra = [f"Bahan: {n} {qty(q)} {u}" for n, q, u in p.materials] + [f"Kebutuhan: {n}" for n in p.needs]
        note = "; ".join([*p.remarks, *extra]) or "-"
        theme.work_slide(prs, kicker=d.date_text, title=p.name, phase="SURVEY", phase_label="Survei",
                         status="DONE" if p.status == "EXISTING" else "IN_PROGRESS",
                         status_label="Sudah terpasang" if p.status == "EXISTING" else "Usulan baru", note=note,
                         progress=d.location, photos=[(ph.slot, ph.image) for ph in p.photos], footer=footer)
    for start in range(0, len(d.bom), 12):
        slide = theme.page(prs, "Rincian volume dan biaya (estimasi)", "Material", footer=footer)
        theme.table(slide, ["No", "Material", "Jumlah", "Satuan", "Kelompok"],
                    [(start + i, n, qty(q), u, g) for i, (n, q, u, g) in enumerate(d.bom[start:start + 12], start=1)],
                    [2.0, 14.0, 4.5, 4.5, 6.3])
    _omitted_slide(prs, d.omitted_photos, footer)
    theme.closing(prs, f"{COMPANY} · {d.client}")
    return theme.save(prs)


def periodic_pptx(r: PeriodicReport) -> bytes:
    prs = theme.deck()
    footer = f"Laporan mingguan {r.division_name} · {tgl(r.start)} s.d. {tgl(r.end)}"
    theme.cover(prs, f"Laporan Mingguan\n{r.division_name}", f"{tgl(r.start)} s.d. {tgl(r.end)}", COMPANY,
                badge="Rekap divisi")
    total = sum(d.items for d in r.days)
    done = sum(d.items_done for d in r.days)
    slide = theme.page(prs, "Ringkasan minggu ini", "Divisi", footer=footer)
    theme.kpis(slide, [
        (str(len(r.days)), "Jadwal tim", theme.NAVY),
        (f"{done}/{total}", "Pekerjaan selesai", "1E6B43"),
        (str(sum(d.items_shifted for d in r.days)), "Pindah hari", "C7892A"),
        (f"Rp {sum(m.total_amount for m in r.meal):,.0f}".replace(",", "."), "Uang makan", "3569A0"),
    ])
    for start in range(0, len(r.days), 12):
        slide = theme.page(prs, "Jadwal per hari", "Semua tim", footer=footer)
        theme.table(slide, ["Tanggal", "Tim", "Lokasi", "Selesai", "Kemajuan"],
                    [(tgl(d.work_date), d.team_name, d.site_name, f"{d.items_done} / {d.items}", f"{d.avg_progress}%")
                     for d in r.days[start:start + 12]], [4.6, 7.5, 11.0, 4.0, 4.2])
    for start in range(0, len(r.boq), 12):
        slide = theme.page(prs, "Material per pekerjaan klien", "Rekap material", footer=footer)
        theme.table(slide, ["No. kerja", "Pekerjaan", "Material", "Rencana", "Satuan"],
                    [(b.order_number or "-", b.project_title, b.material_name, qty(b.estimated_qty), b.unit)
                     for b in r.boq[start:start + 12]], [4.6, 10.0, 10.0, 3.6, 3.1])
    theme.closing(prs, f"{COMPANY} · {r.division_name}")
    return theme.save(prs)


def _assets_slide(prs: PptxPresentation, assets: Sequence[AssetLine], footer: str) -> None:
    """Satu slide tabel kendaraan & alat tim pada minggu itu; tanpa aset → tanpa slide."""
    for start in range(0, len(assets), 14):
        chunk = assets[start:start + 14]
        slide = theme.page(prs, "Kendaraan & alat minggu ini", footer=footer)
        theme.table(slide, ["Tanggal", "Jenis", "Nama / kode", "Pemegang", "Status"],
                    [(tgl(a.work_date), a.kind, f"{a.name} ({a.code})" if a.code else a.name, a.holder or "-",
                      a.status or "-") for a in chunk],
                    [3.6, 3.0, 6.4, 3.8, 3.2])


def team_week_pptx(r: TeamWeekReport) -> bytes:
    """Laporan mingguan tim: sampul, ringkasan (kartu angka + jenis), tabel semua pekerjaan, satu slide per
    pekerjaan (foto, keterangan, status), penutup."""
    prs = theme.deck(r.logos)
    footer = f"{r.team_name} · {tgl(r.start)} s.d. {tgl(r.end)}"
    leader = next((m.full_name for m in r.roster if m.is_leader), "-")
    members = [m.full_name for m in r.roster if not m.is_leader]
    theme.cover(prs, f"Laporan Mingguan\n{r.team_name}", f"{tgl(r.start)} s.d. {tgl(r.end)} · {r.division_name}",
                f"{COMPANY} · Ketua tim: {leader}", badge="Laporan tim", emblem=r.team_name)
    _summary(prs, r.points, r.division_name, footer, "Anggota tim",
             "\n".join([f"Ketua: {leader}", *[f"• {m}" for m in members]]))
    _points_table(prs, "Semua pekerjaan minggu ini", r.team_name, r.points, footer)
    _assets_slide(prs, r.assets, footer)
    _work_slides(prs, r.points, footer)
    _omitted_slide(prs, r.omitted_photos, footer)
    theme.closing(prs, f"{r.team_name} · {COMPANY}")
    return theme.save(prs)


def monthly_pptx(r: PeriodicReport) -> bytes:
    """Laporan bulanan divisi (PowerPoint): isi setara versi Word-nya."""
    prs = theme.deck()
    footer = f"Laporan bulanan {r.division_name} · {month_label(r.start)}"
    theme.cover(prs, f"Laporan Bulanan\n{r.division_name}",
                f"{month_label(r.start)} · {tgl(r.start)} s.d. {tgl(r.end)}", COMPANY, badge="Laporan bulanan")
    total = sum(d.items for d in r.days)
    done = sum(d.items_done for d in r.days)
    slide = theme.page(prs, "Ringkasan bulan ini", "Divisi", footer=footer)
    theme.kpis(slide, [
        (str(len(r.days)), "Jadwal tim", theme.NAVY),
        (f"{done}/{total}", "Pekerjaan selesai", "1E6B43"),
        (str(sum(d.items_shifted for d in r.days)), "Pindah hari", "C7892A"),
        (rupiah(sum(m.total_amount for m in r.meal)), "Uang makan", "3569A0"),
    ])
    for start in range(0, len(r.days), 12):
        slide = theme.page(prs, "Jadwal tim per hari", "Semua tim", footer=footer)
        theme.table(slide, ["Tanggal", "Tim", "Lokasi", "Selesai", "Kemajuan"],
                    [(tgl(d.work_date), d.team_name, d.site_name, f"{d.items_done} / {d.items}", f"{d.avg_progress}%")
                     for d in r.days[start:start + 12]], [4.6, 7.5, 11.0, 4.0, 4.2])
    for start in range(0, len(r.boq), 12):
        slide = theme.page(prs, "Rincian material per pekerjaan klien", "Material", footer=footer)
        theme.table(slide, ["No. kerja", "Pekerjaan", "Material", "Rencana", "Satuan"],
                    [(b.order_number or "-", b.project_title, b.material_name, qty(b.estimated_qty), b.unit)
                     for b in r.boq[start:start + 12]], [4.6, 10.0, 10.0, 3.6, 3.1])
    for start in range(0, len(r.meal), 12):
        slide = theme.page(prs, "Uang makan", "Karyawan", footer=footer)
        theme.table(slide, ["NIK", "Nama", "Dalam kota", "Luar kota", "Total"],
                    [(m.employee_no, m.full_name, m.in_city_days, m.out_city_days, rupiah(m.total_amount))
                     for m in r.meal[start:start + 12]], [4.6, 11.0, 5.0, 5.0, 6.0])
    theme.closing(prs, f"{COMPANY} · {r.division_name}")
    return theme.save(prs)
