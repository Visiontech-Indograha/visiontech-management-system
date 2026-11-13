"""
app/modules/exports/services/builders/docx_builders.py
Word resmi (docs/35 §8): Berita Acara Serah Terima & Laporan Survei.

Laporan Survei mengikuti kerangka laporan survei "New CCTV MGT Minas" (2026-09): kop Visiontech & klien,
tanggal/lokasi/tujuan, tabel jadwal, uraian aktivitas & tim, layout titik, hitungan instalasi per titik,
dokumentasi per titik (foto + remark), rincian volume dan biaya estimasi, penutup & penanda tangan.
"""
from __future__ import annotations

import io
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from docx.document import Document as DocxDocument
from docx.shared import Cm

from app.modules.exports.services.builders.model import (
    COMPANY,
    AssetLine,
    CompletionReport,
    DailyReport,
    PeriodicReport,
    ReportPoint,
    TeamWeekReport,
    coord_text,
    month_label,
    omitted_note,
    plan_status_label,
    qty,
    rupiah,
    tgl,
)
from app.shared.documents import docx_kit as kit
from app.shared.documents.static_map import STATUS_LABEL


def _signature_blocks(r: CompletionReport) -> list[tuple[str, str, str, bytes | None]]:
    o = r.order
    return [
        ("Dibuat oleh (Ketua Tim)", o.get("leader_signer_name") or "( ................ )",
         tgl(o.get("leader_signed_at")) if o.get("leader_signed_at") else "Belum ditandatangani", r.leader_signature),
        ("Disetujui oleh (Project Manager)", o.get("pm_signer_name") or o.get("pm_name") or "( ................ )",
         tgl(o.get("pm_signed_at")) if o.get("pm_signed_at") else "Belum ditandatangani", r.pm_signature),
    ]


def _integrity(doc: object, r: CompletionReport) -> None:
    h = r.order.get("signature_hash")
    text = (f"Sidik dokumen (SHA-256): {h}" if h else "Dokumen belum disahkan PM — bukan dokumen resmi.")
    if r.verify_url and h:
        text += f"\nVerifikasi: {r.verify_url}"
    kit.para(doc, text, italic=True, size=8)  # type: ignore[arg-type]


def _schedule_days(order: dict[str, Any], points: list[ReportPoint]) -> list[date]:
    """Seluruh tanggal jadwal order: rentang start..end order ditambah tanggal item (urut, tanpa duplikat)."""
    days: set[date] = {p.work_date for p in points if p.work_date}
    start, end = order.get("start_work_date"), order.get("end_work_date")
    if isinstance(start, date) and isinstance(end, date) and start <= end and (end - start).days <= 62:
        days.update(start + timedelta(days=n) for n in range((end - start).days + 1))
    return sorted(days)


def _daily_summary(doc: DocxDocument, points: list[ReportPoint], start_no: int, days: list[date] | None = None) -> None:
    """Ringkasan laporan harian per tanggal jadwal: tim, item, progres, catatan, alasan tunda.
    `days` = semua tanggal jadwal order (tanggal tanpa item tetap tampil)."""
    kit.heading(doc, f"{start_no}. Ringkasan Laporan Harian")
    if not points and not days:
        kit.para(doc, "Belum ada laporan harian.", italic=True)
        return
    by_day: dict[date, list[ReportPoint]] = defaultdict(list)
    for p in points:
        by_day[p.work_date].append(p)
    for day in sorted(set(by_day) | set(days or [])):
        rows = by_day.get(day, [])
        if not rows:
            kit.para(doc, f"{tgl(day)} - Tidak ada pekerjaan tercatat.")
            continue
        teams = ", ".join(sorted({p.team_name for p in rows if p.team_name})) or "-"
        kit.para(doc, f"{tgl(day)} - Tim: {teams}")
        kit.grid(
            doc,
            ["Item", "Status", "Progres", "Catatan"],
            [
                (
                    p.title,
                    p.status_label,
                    f"{qty(p.completed)} / {qty(p.target)} ({qty(p.progress)}%)",
                    "; ".join(x for x in (p.notes, f"Tunda: {p.delay_reason}" if p.delay_reason else None) if x),
                )
                for p in rows
            ],
            [6, 3, 3.5, 4.5],
        )


def _map_section(doc: DocxDocument, r: CompletionReport, no: int) -> None:
    """Halaman peta lokasi: citra satelit dengan penanda bernomor (sama dengan nomor pada tabel)."""
    kit.heading(doc, f"{no}. Peta Lokasi")
    if not r.has_coordinates:
        kit.para(doc, "Koordinat lokasi belum diisi.", italic=True)
        return
    if r.map_image:
        doc.add_paragraph().add_run().add_picture(io.BytesIO(r.map_image), width=Cm(16.5))
        kit.para(
            doc,
            f"Hijau = {STATUS_LABEL['EXISTING']}, biru = {STATUS_LABEL['PROPOSED']}. "
            "Nomor sesuai urutan titik pada tabel.",
            italic=True,
            size=8,
        )
    else:
        kit.para(doc, "Peta tidak tersedia (tanpa koneksi ke citra satelit).", italic=True)


def _work_period(order: dict[str, Any], points: list[ReportPoint]) -> str:
    """Periode kerja: tanggal order; bila kosong, rentang tanggal item; bila keduanya kosong → belum ditetapkan."""
    start, end = order.get("start_work_date"), order.get("end_work_date")
    if not (start or end) and points:
        dates = [p.work_date for p in points if p.work_date]
        start, end = (min(dates), max(dates)) if dates else (None, None)
    if not (start or end):
        return "Belum ditetapkan"
    return f"{tgl(start)} s.d. {tgl(end)}"


def order_sheet_docx(r: CompletionReport) -> bytes:
    """Surat tugas / lembar order: dibuat PM dari data order, tanpa tanda tangan."""
    o = r.order
    doc = kit.new_document()
    kit.letterhead(doc, COMPANY, "Surat Tugas Pekerjaan", f"Nomor order: {r.number}", o.get("client_name"),
                   logos=r.logos)

    kit.heading(doc, "1. Data Order")
    kit.info_table(
        doc,
        [
            ("Klien", o.get("client_name")),
            ("Proyek / Judul pekerjaan", o.get("project_title")),
            ("Divisi", o.get("division_name")),
            ("Project Manager", o.get("pm_name")),
            ("Lokasi", o.get("site_address")),
            ("Koordinat lokasi", coord_text(o.get("site_lat"), o.get("site_lng"))),
            ("Jadwal kerja", _work_period(o, r.points)),
            ("Target volume", f"{qty(o.get('total_target_unit'))} {o.get('unit_measure') or ''}".strip()),
        ],
    )

    kit.heading(doc, "2. Ruang Lingkup Pekerjaan")
    if r.points:
        kit.grid(
            doc,
            ["No", "Titik / Pekerjaan", "Lokasi", "Fase", "Target", "Tanggal rencana"],
            [
                (i, p.title, p.location, p.phase_label, qty(p.target), tgl(p.work_date))
                for i, p in enumerate(r.points, start=1)
            ],
            [1, 6, 4, 2.5, 2, 3],
        )
    else:
        kit.para(doc, "Rincian titik belum dibuat.", italic=True)

    kit.heading(doc, "3. Rincian Material Perkiraan")
    if r.bom:
        kit.grid(
            doc,
            ["No", "Kode", "Material", "Estimasi", "Satuan"],
            [
                (i, b.get("material_code"), b.get("material_name"), qty(b.get("estimated_qty")), b.get("unit"))
                for i, b in enumerate(r.bom, start=1)
            ],
            [1, 2.5, 8, 3, 2.5],
        )
    else:
        kit.para(doc, "Belum ada rincian material.", italic=True)

    kit.heading(doc, "4. Catatan")
    kit.para(doc, o.get("summary_notes") or "Pekerjaan dilaksanakan sesuai lingkup dan jadwal di atas.")
    kit.para(
        doc,
        f"Diterbitkan oleh {r.generated_by} pada {tgl(r.generated_at)}. Dokumen ini tidak memerlukan tanda tangan.",
        italic=True,
        size=8,
    )
    return kit.to_bytes(doc)


_DOC_PHOTOS = 12  # foto yang dimuat di bagian dokumentasi satu dokumen


def _photo_note(doc: DocxDocument, count: int) -> None:
    note = omitted_note(count)
    if note:
        kit.para(doc, note, italic=True, size=9)


def _assets_table(doc: DocxDocument, assets: list[AssetLine], *, with_date: bool) -> None:
    """Tabel kendaraan & alat yang dipinjam; kosong → kalimat keterangan (bukan tabel kosong)."""
    if not assets:
        kit.para(doc, "Tidak ada kendaraan atau alat yang dipinjam.", italic=True)
        return
    headers = ["No", "Jenis", "Nama / kode", "Pemegang", "Status"]
    if with_date:
        headers.insert(1, "Tanggal")
    rows = []
    for i, a in enumerate(assets, start=1):
        name = f"{a.name}\n{a.code}" if a.code else a.name
        row: list[Any] = [i, a.kind, name, a.holder or "-", a.status or "-"]
        if with_date:
            row.insert(1, tgl(a.work_date))
        rows.append(tuple(row))
    widths = [1, 3, 2.6, 5, 3, 3] if with_date else [1, 2.6, 6, 4, 3]
    kit.grid(doc, headers, rows, widths)


def daily_report_docx(r: DailyReport) -> bytes:
    """Laporan harian satu jadwal (cetak per hari): header jadwal, tabel item, foto, laporan ketua."""
    doc = kit.new_document()
    kit.letterhead(doc, COMPANY, "Laporan Harian Tim", tgl(r.work_date), r.team_name, logos=r.logos)

    kit.heading(doc, "1. Informasi Jadwal")
    kit.info_table(
        doc,
        [
            ("Tanggal kerja", tgl(r.work_date)),
            ("Tim / Divisi", f"{r.team_name} / {r.division_name}"),
            ("Ketua tim", r.leader_name),
            ("Lokasi", r.site_name),
            ("Status jadwal", plan_status_label(r.status)),
            ("Anggota", ", ".join(sorted({m.full_name for m in r.roster if not m.is_leader})) or "-"),
        ],
    )

    kit.heading(doc, "2. Item Pekerjaan")
    if r.points:
        kit.grid(
            doc,
            ["No", "Pekerjaan", "Status", "Progres", "Catatan / alasan tunda"],
            [
                (
                    i,
                    f"{p.title}\n{p.location}" if p.location else p.title,
                    p.status_label,
                    f"{qty(p.completed)} / {qty(p.target)} ({qty(p.progress)}%)",
                    "; ".join(x for x in (p.notes, f"Tunda: {p.delay_reason}" if p.delay_reason else None) if x),
                )
                for i, p in enumerate(r.points, start=1)
            ],
            [1, 6, 2.6, 3, 5],
        )
    else:
        kit.para(doc, "Belum ada item pekerjaan pada jadwal ini.", italic=True)

    kit.heading(doc, "3. Kendaraan & Alat")
    _assets_table(doc, r.assets, with_date=False)

    kit.heading(doc, "4. Laporan Ketua Tim")
    kit.para(doc, r.summary or "Belum ada laporan ringkasan dari ketua tim.")
    if r.obstacles:
        kit.para(doc, f"Kendala: {r.obstacles}")

    photos = [(f"{p.title} - {ph.label}", ph.image) for p in r.points for ph in p.photos]
    if photos:
        kit.heading(doc, "5. Dokumentasi")
        kit.picture_pair(doc, photos[:_DOC_PHOTOS])
    _photo_note(doc, r.omitted_photos + max(0, len(photos) - _DOC_PHOTOS))

    kit.para(
        doc,
        f"Dicetak oleh {r.generated_by} pada {tgl(r.generated_at)}"
        + (f"; laporan dikirim {tgl(r.report_submitted_at)}" if r.report_submitted_at else ""),
        italic=True,
        size=8,
    )
    return kit.to_bytes(doc)


def bast_docx(r: CompletionReport) -> bytes:
    o = r.order
    doc = kit.new_document()
    kit.letterhead(doc, COMPANY, "Berita Acara Serah Terima Pekerjaan", f"Nomor: {r.number}", o.get("client_name"),
                   logos=r.logos)

    kit.heading(doc, "1. Informasi Pekerjaan")
    kit.info_table(doc, [
        ("Klien", o.get("client_name")),
        ("Pekerjaan", o.get("project_title")),
        ("Divisi / PM", f"{o.get('division_name') or '-'} / {o.get('pm_name') or '-'}"),
        ("Lokasi", o.get("site_address")),
        ("Periode", f"{tgl(o.get('start_work_date'))} s.d. {tgl(o.get('end_work_date'))}"),
        ("Realisasi volume",
         f"{qty(o.get('completed_target_unit'))} / {qty(o.get('total_target_unit'))} {o.get('unit_measure') or ''}"),
        ("Koordinat lokasi", coord_text(o.get("site_lat"), o.get("site_lng"))),
    ])

    kit.heading(doc, "2. Rincian Pekerjaan per Titik")
    kit.grid(doc, ["No", "Tanggal", "Titik / Pekerjaan", "Fase", "Realisasi", "Status"], [
        (i, tgl(p.work_date), f"{p.title}\n{p.location}" if p.location else p.title, p.phase_label,
         f"{qty(p.completed)} / {qty(p.target)}", p.status_label)
        for i, p in enumerate(r.points, start=1)
    ], [1, 3, 6, 2.4, 2.4, 2.4])

    kit.heading(doc, "3. Realisasi Material")
    if r.bom:
        kit.grid(doc, ["No", "Kode", "Material", "Estimasi", "Aktual", "Satuan"], [
            (i, b.get("material_code"), b.get("material_name"), qty(b.get("estimated_qty")),
             qty(b.get("actual_qty")), b.get("unit")) for i, b in enumerate(r.bom, start=1)
        ], [1, 2.5, 7, 2.2, 2.2, 2.2])
    else:
        kit.para(doc, "Tidak ada material yang dicatat.", italic=True)

    kit.heading(doc, "4. Ringkasan & Kendala")
    kit.para(doc, o.get("summary_notes") or "Pekerjaan telah dilaksanakan sesuai lingkup.")
    if o.get("obstacles"):
        kit.para(doc, f"Kendala: {o['obstacles']}")

    _daily_summary(doc, r.points, start_no=5, days=_schedule_days(o, r.points))
    _map_section(doc, r, no=6)

    photos = r.all_photos
    if photos:
        kit.heading(doc, "7. Dokumentasi")
        kit.picture_pair(doc, photos[:_DOC_PHOTOS])
    _photo_note(doc, r.omitted_photos + max(0, len(photos) - _DOC_PHOTOS))

    kit.heading(doc, "Pengesahan")
    kit.para(doc, "Dengan ditandatanganinya berita acara ini, pekerjaan di atas dinyatakan telah diserahterimakan.")
    kit.signatures(doc, _signature_blocks(r))
    _integrity(doc, r)
    return kit.to_bytes(doc)


def survey_report_docx(r: CompletionReport) -> bytes:
    o = r.order
    points = r.survey_points
    doc = kit.new_document()
    kit.letterhead(doc, COMPANY, "Laporan Survei", o.get("project_title"), o.get("client_name"),
                   logos=r.logos)

    dates = r.survey_dates
    kit.heading(doc, "1. Informasi Survei")
    kit.info_table(doc, [
        ("Tanggal", ", ".join(tgl(d) for d in dates)),
        ("Lokasi", o.get("site_address") or (points[0].location if points else None)),
        ("Klien", o.get("client_name")),
        ("Tujuan", f"Survei lokasi untuk {o.get('project_title') or 'pekerjaan'}: menentukan posisi titik, "
                   "kebutuhan instalasi, dan estimasi material."),
        ("Nomor order", r.number),
    ])

    kit.heading(doc, "2. Jadwal Survei")
    kit.grid(doc, ["No", "Tanggal", "Tim", "Titik", "Lokasi"], [
        (i, tgl(p.work_date), p.team_name, p.title, p.location or "-") for i, p in enumerate(points, start=1)
    ], [1, 3.2, 3.5, 6, 3.5])

    kit.heading(doc, "3. Uraian Aktivitas & Tim")
    kit.para(doc, f"Tim melakukan survei pada {len(points)} titik: pengecekan posisi, jalur kabel, sumber daya, dan "
                  "kondisi lingkungan sekitar setiap titik.")
    if r.roster:
        kit.grid(doc, ["No", "Nama", "NIK", "Peran", "Tim"], [
            (i, m.full_name, m.employee_no, "Ketua Tim" if m.is_leader else "Anggota", m.team_name)
            for i, m in enumerate(r.roster, start=1)
        ], [1, 5.5, 3, 3, 4.5])

    kit.heading(doc, "4. Layout Titik")
    kit.grid(doc, ["Titik", "Lokasi", "Koordinat"], [
        (p.title, p.location or "-",
         f"{p.lat:.6f}, {p.lng:.6f}" if p.lat is not None and p.lng is not None else "-") for p in points
    ], [5, 7, 5])

    kit.heading(doc, "5. Kebutuhan Instalasi per Titik")
    rows = [(p.title, b.get("material_name"), qty(b.get("estimated_qty")), b.get("unit"), b.get("notes"))
            for p in points for b in p.bom]
    if rows:
        kit.grid(doc, ["Titik", "Material / Pekerjaan", "Qty", "Satuan", "Keterangan"], rows, [4, 5.5, 1.8, 2, 4])
    else:
        kit.para(doc, "Belum ada kebutuhan material yang dicatat per titik.", italic=True)

    kit.heading(doc, "6. Dokumentasi per Titik")
    for i, p in enumerate(points, start=1):
        kit.para(doc, f"6.{i} {p.title}" + (f" — {p.location}" if p.location else ""))
        if p.photos:
            kit.picture_pair(doc, [(ph.label, ph.image) for ph in p.photos])
        kit.para(doc, f"Keterangan: {p.notes or '-'}", size=9.5)
    _photo_note(doc, r.omitted_photos)

    kit.heading(doc, "7. Rincian Volume dan Biaya (Estimasi)")
    if r.bom:
        kit.grid(doc, ["No", "Kode", "Material", "Qty", "Satuan", "Kategori"], [
            (i, b.get("material_code"), b.get("material_name"), qty(b.get("estimated_qty")), b.get("unit"),
             b.get("category")) for i, b in enumerate(r.bom, start=1)
        ], [1, 2.5, 7, 1.8, 2, 3])
    else:
        kit.para(doc, "Rincian volume dan biaya belum disusun.", italic=True)

    kit.heading(doc, "8. Penutup")
    kit.para(doc, o.get("summary_notes") or "Demikian laporan survei ini dibuat sebagai dasar perencanaan pekerjaan.")
    kit.signatures(doc, _signature_blocks(r))
    _integrity(doc, r)
    return kit.to_bytes(doc)


def team_week_docx(r: TeamWeekReport) -> bytes:
    """Laporan mingguan tim (Word): isi setara slide mingguan: ringkasan, anggota, semua pekerjaan, kendaraan & alat,
    dokumentasi."""
    doc = kit.new_document()
    period = f"{tgl(r.start)} s.d. {tgl(r.end)}"
    kit.letterhead(doc, COMPANY, "Laporan Mingguan Tim", period, r.team_name, logos=r.logos)
    leader = next((m.full_name for m in r.roster if m.is_leader), "-")
    members = sorted({m.full_name for m in r.roster if not m.is_leader})
    done = sum(1 for p in r.points if p.status == "DONE")

    kit.heading(doc, "1. Informasi Minggu Ini")
    kit.info_table(doc, [
        ("Periode", period),
        ("Tim / Divisi", f"{r.team_name} / {r.division_name}"),
        ("Ketua tim", leader),
        ("Anggota", ", ".join(members) or "-"),
        ("Pekerjaan selesai", f"{done} dari {len(r.points)}"),
    ])

    kit.heading(doc, "2. Semua Pekerjaan")
    kit.grid(doc, ["No", "Tanggal", "Pekerjaan", "Jenis", "Dikerjakan", "Status", "Keterangan"], [
        (i, tgl(p.work_date), f"{p.title}\n{p.location}" if p.location else p.title, p.phase_label,
         f"{qty(p.completed)} / {qty(p.target)}", p.status_label,
         "; ".join(x for x in (p.notes, f"Tunda: {p.delay_reason}" if p.delay_reason else None) if x))
        for i, p in enumerate(r.points, start=1)
    ], [1, 2.4, 4.6, 2, 2.2, 2.2, 3.4])

    kit.heading(doc, "3. Kendaraan & Alat")
    _assets_table(doc, r.assets, with_date=True)

    photos = [(f"{p.title} - {ph.label}", ph.image) for p in r.points for ph in p.photos]
    if photos:
        kit.heading(doc, "4. Dokumentasi")
        kit.picture_pair(doc, photos[:_DOC_PHOTOS * 4])
    _photo_note(doc, r.omitted_photos + max(0, len(photos) - _DOC_PHOTOS * 4))
    kit.para(doc, f"Dicetak oleh {r.generated_by} pada {tgl(r.generated_at)}", italic=True, size=8)
    return kit.to_bytes(doc)


def progress_docx(r: CompletionReport) -> bytes:
    """Laporan kemajuan pekerjaan (Word): isi setara slide progres order."""
    o = r.order
    doc = kit.new_document()
    kit.letterhead(doc, COMPANY, "Laporan Kemajuan Pekerjaan", f"Nomor: {r.number}", o.get("client_name"),
                   logos=r.logos)
    done = sum(1 for p in r.points if p.status == "DONE")
    kit.heading(doc, "1. Ringkasan")
    kit.info_table(doc, [
        ("Klien", o.get("client_name")),
        ("Pekerjaan", o.get("project_title")),
        ("Periode", f"{tgl(o.get('start_work_date'))} s.d. {tgl(o.get('end_work_date'))}"),
        ("Pekerjaan selesai", f"{done} dari {len(r.points)}"),
    ])
    kit.heading(doc, "2. Kemajuan per Pekerjaan")
    kit.grid(doc, ["No", "Tanggal", "Pekerjaan", "Jenis", "Dikerjakan", "Status"], [
        (i, tgl(p.work_date), f"{p.title}\n{p.location}" if p.location else p.title, p.phase_label,
         f"{qty(p.completed)} / {qty(p.target)}", p.status_label) for i, p in enumerate(r.points, start=1)
    ], [1, 2.6, 6, 2.4, 2.6, 2.4])
    kit.heading(doc, "3. Material")
    if r.bom:
        kit.grid(doc, ["No", "Material", "Rencana", "Terpakai", "Satuan"], [
            (i, b.get("material_name"), qty(b.get("estimated_qty")), qty(b.get("actual_qty")), b.get("unit"))
            for i, b in enumerate(r.bom, start=1)
        ], [1, 8, 2.6, 2.6, 2.4])
    else:
        kit.para(doc, "Tidak ada material yang dicatat.", italic=True)
    kit.heading(doc, "4. Ringkasan & Kendala")
    kit.para(doc, o.get("summary_notes") or "-")
    if o.get("obstacles"):
        kit.para(doc, f"Kendala: {o['obstacles']}")
    photos = r.all_photos
    if photos:
        kit.heading(doc, "5. Dokumentasi")
        kit.picture_pair(doc, photos[:_DOC_PHOTOS])
    _photo_note(doc, r.omitted_photos + max(0, len(photos) - _DOC_PHOTOS))
    kit.para(doc, f"Dicetak oleh {r.generated_by} pada {tgl(r.generated_at)}", italic=True, size=8)
    return kit.to_bytes(doc)


def monthly_docx(r: PeriodicReport) -> bytes:
    """Laporan bulanan divisi (Word): agregat satu bulan kalender: ringkasan, jadwal tim, material, uang makan."""
    doc = kit.new_document()
    kit.letterhead(doc, COMPANY, "Laporan Bulanan Divisi", month_label(r.start), r.division_name)
    total = sum(d.items for d in r.days)
    done = sum(d.items_done for d in r.days)
    kit.heading(doc, "1. Ringkasan Bulan Ini")
    kit.info_table(doc, [
        ("Divisi", r.division_name),
        ("Bulan", month_label(r.start)),
        ("Periode", f"{tgl(r.start)} s.d. {tgl(r.end)}"),
        ("Jadwal tim", str(len(r.days))),
        ("Pekerjaan selesai", f"{done} dari {total}"),
        ("Pekerjaan pindah hari", str(sum(d.items_shifted for d in r.days))),
        ("Total uang makan", rupiah(sum(m.total_amount for m in r.meal))),
    ])
    kit.heading(doc, "2. Jadwal Tim per Hari")
    if r.days:
        kit.grid(doc, ["No", "Tanggal", "Tim", "Lokasi", "Selesai", "Kemajuan"], [
            (i, tgl(d.work_date), d.team_name, d.site_name, f"{d.items_done} / {d.items}", f"{d.avg_progress}%")
            for i, d in enumerate(r.days, start=1)
        ], [1, 2.8, 4, 5, 2.4, 2.4])
    else:
        kit.para(doc, "Tidak ada jadwal tim pada bulan ini.", italic=True)
    kit.heading(doc, "3. Rincian Material per Pekerjaan Klien")
    if r.boq:
        kit.grid(doc, ["No", "No. kerja", "Pekerjaan", "Material", "Rencana", "Satuan"], [
            (i, b.order_number or "-", b.project_title, b.material_name, qty(b.estimated_qty), b.unit)
            for i, b in enumerate(r.boq, start=1)
        ], [1, 2.6, 4.4, 4.4, 2, 2])
    else:
        kit.para(doc, "Tidak ada rincian material pada bulan ini.", italic=True)
    kit.heading(doc, "4. Uang Makan")
    if r.meal:
        kit.grid(doc, ["No", "NIK", "Nama", "Hari dalam kota", "Hari luar kota", "Total"], [
            (i, m.employee_no, m.full_name, m.in_city_days, m.out_city_days, rupiah(m.total_amount))
            for i, m in enumerate(r.meal, start=1)
        ], [1, 2.4, 4.6, 2.6, 2.6, 3])
    else:
        kit.para(doc, "Tidak ada uang makan pada bulan ini.", italic=True)
    kit.para(doc, f"Dicetak oleh {r.generated_by} pada {tgl(r.generated_at)}", italic=True, size=8)
    return kit.to_bytes(doc)
