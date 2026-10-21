"""
app/modules/exports/services/builders/docx_builders.py
Word resmi (docs/35 §8): Berita Acara Serah Terima (BAST) & Survey Report.

Survey Report mengikuti kerangka laporan "Survey Report New CCTV MGT Minas" (2026-09): kop Visiontech & klien,
tanggal/lokasi/tujuan, tabel jadwal, uraian aktivitas & tim, layout titik, hitungan instalasi per titik,
dokumentasi per titik (foto + remark), Bill of Material estimasi, penutup & penanda tangan.
"""
from __future__ import annotations

from app.modules.exports.services.builders.model import COMPANY, CompletionReport, qty, tgl
from app.shared.documents import docx_kit as kit


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


def bast_docx(r: CompletionReport) -> bytes:
    o = r.order
    doc = kit.new_document()
    kit.letterhead(doc, COMPANY, "Berita Acara Serah Terima Pekerjaan", f"Nomor: {r.number}", o.get("client_name"))

    kit.heading(doc, "1. Informasi Pekerjaan")
    kit.info_table(doc, [
        ("Klien", o.get("client_name")),
        ("Pekerjaan", o.get("project_title")),
        ("Divisi / PM", f"{o.get('division_name') or '-'} / {o.get('pm_name') or '-'}"),
        ("Lokasi", o.get("site_address")),
        ("Periode", f"{tgl(o.get('start_work_date'))} s.d. {tgl(o.get('end_work_date'))}"),
        ("Realisasi volume",
         f"{qty(o.get('completed_target_unit'))} / {qty(o.get('total_target_unit'))} {o.get('unit_measure') or ''}"),
    ])

    kit.heading(doc, "2. Rincian Pekerjaan per Titik")
    kit.grid(doc, ["No", "Tanggal", "Titik / Pekerjaan", "Fase", "Realisasi", "Status"], [
        (i, tgl(p.work_date), f"{p.title}\n{p.location}" if p.location else p.title, p.phase_label,
         f"{qty(p.completed)} / {qty(p.target)}", p.status_label)
        for i, p in enumerate(r.points, start=1)
    ], [1, 3, 6, 2.4, 2.4, 2.4])

    kit.heading(doc, "3. Realisasi Material (BoM)")
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

    photos = r.all_photos
    if photos:
        kit.heading(doc, "5. Dokumentasi")
        kit.picture_pair(doc, photos[:12])

    kit.heading(doc, "Pengesahan")
    kit.para(doc, "Dengan ditandatanganinya berita acara ini, pekerjaan di atas dinyatakan telah diserahterimakan.")
    kit.signatures(doc, _signature_blocks(r))
    _integrity(doc, r)
    return kit.to_bytes(doc)


def survey_report_docx(r: CompletionReport) -> bytes:
    o = r.order
    points = r.survey_points
    doc = kit.new_document()
    kit.letterhead(doc, COMPANY, "Survey Report", o.get("project_title"), o.get("client_name"))

    dates = sorted({p.work_date for p in points})
    kit.heading(doc, "1. Informasi Survei")
    kit.info_table(doc, [
        ("Tanggal", ", ".join(tgl(d) for d in dates) if dates else "-"),
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

    kit.heading(doc, "7. Bill of Material (Estimasi)")
    if r.bom:
        kit.grid(doc, ["No", "Kode", "Material", "Qty", "Satuan", "Kategori"], [
            (i, b.get("material_code"), b.get("material_name"), qty(b.get("estimated_qty")), b.get("unit"),
             b.get("category")) for i, b in enumerate(r.bom, start=1)
        ], [1, 2.5, 7, 1.8, 2, 3])
    else:
        kit.para(doc, "Bill of Material belum disusun.", italic=True)

    kit.heading(doc, "8. Penutup")
    kit.para(doc, o.get("summary_notes") or "Demikian laporan survei ini dibuat sebagai dasar perencanaan pekerjaan.")
    kit.signatures(doc, _signature_blocks(r))
    _integrity(doc, r)
    return kit.to_bytes(doc)
