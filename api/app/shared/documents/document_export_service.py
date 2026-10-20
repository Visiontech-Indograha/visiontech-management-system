"""
app/shared/documents/document_export_service.py
Layanan pembangkit dan ekspor dokumen multi-format untuk Rencana Kerja (Weekly & Daily Plan).
Mendukung 4 format standar: PDF, Word (DOCX), Excel (XLSX), dan PowerPoint (PPTX).
"""

from __future__ import annotations

import io
from typing import Any

from app.core.errors import AppError
from app.shared.documents.pdf_service import html_to_pdf, render_plan_preview_html


class DocumentExportService:
    """Layanan ekspor dokumen otomatis dari sistem template Visiontech."""

    @staticmethod
    def export_pdf(detail: dict[str, Any]) -> bytes:
        """Menghasilkan file PDF dari template resmi perusahaan via WeasyPrint."""
        html = render_plan_preview_html(detail)
        return html_to_pdf(html)

    @staticmethod
    def export_docx(detail: dict[str, Any]) -> bytes:
        """Menghasilkan file Word DOCX rencana kerja lengkap."""
        try:
            import docx
            from docx.enum.table import WD_TABLE_ALIGNMENT
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            from docx.shared import Inches, Pt, RGBColor
        except ImportError as err:
            raise AppError("DEPENDENCY_MISSING", "Pustaka python-docx tidak tersedia.", status=503) from err

        doc = docx.Document()

        # Set page margins
        for section in doc.sections:
            section.top_margin = Inches(0.8)
            section.bottom_margin = Inches(0.8)
            section.left_margin = Inches(0.8)
            section.right_margin = Inches(0.8)

        plan = detail.get("plan", {})
        team = detail.get("team", [])
        days = detail.get("days", [])

        # Header Kop Perusahaan
        title_p = doc.add_paragraph()
        title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_corp = title_p.add_run("PT VISIONTECH INDOGRAHA\n")
        run_corp.bold = True
        run_corp.font.size = Pt(14)
        run_corp.font.color.rgb = RGBColor(30, 41, 59)

        run_sub = title_p.add_run("SURAT PERINTAH KERJA (SPK) & RENCANA KERJA OPERASIONAL\n")
        run_sub.bold = True
        run_sub.font.size = Pt(12)
        run_sub.font.color.rgb = RGBColor(71, 85, 105)

        run_num = title_p.add_run(f"Nomor: {plan.get('number') or 'DRAFT-PLAN'}\n")
        run_num.font.size = Pt(10)
        run_num.font.italic = True

        doc.add_paragraph().paragraph_format.space_after = Pt(6)

        # Informasi Ringkasan Proyek
        doc.add_heading("1. Informasi Rencana Kerja", level=2)
        info_table = doc.add_table(rows=5, cols=2)
        info_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        info_table.autofit = True

        cat_str = f"{plan.get('category_label') or plan.get('category') or '-'} / {plan.get('work_type_name') or '-'}"
        period_str = f"{plan.get('period_start') or ''} s.d. {plan.get('period_end') or ''}"
        zone_str = "Luar Kota" if plan.get("is_out_of_town") else "Dalam Kota"
        status_zone = f"{plan.get('status') or 'DRAFT'} | {zone_str}"

        rows_data = [
            ("Judul Pekerjaan", plan.get("title") or "-"),
            ("Kategori / Tipe", cat_str),
            ("Lokasi Pelaksanaan", plan.get("location_text") or "-"),
            ("Periode Pekerjaan", period_str),
            ("Status / Zona", status_zone),
        ]

        for i, (label, val) in enumerate(rows_data):
            cell_lbl = info_table.rows[i].cells[0]
            cell_val = info_table.rows[i].cells[1]
            cell_lbl.text = label
            cell_lbl.paragraphs[0].runs[0].bold = True
            cell_val.text = str(val)

        doc.add_paragraph().paragraph_format.space_after = Pt(6)

        # Tim Pelaksana
        doc.add_heading("2. Personel & Tim Pelaksana", level=2)
        if team:
            team_table = doc.add_table(rows=1, cols=3)
            team_table.alignment = WD_TABLE_ALIGNMENT.CENTER
            hdr = team_table.rows[0].cells
            hdr[0].text = "Peran"
            hdr[1].text = "Nama Lengkap"
            hdr[2].text = "Nomor Karyawan / Telepon"
            for c in hdr:
                c.paragraphs[0].runs[0].bold = True

            for m in team:
                row_cells = team_table.add_row().cells
                row_cells[0].text = "Ketua Tim" if m.get("role_in_plan") == "LEADER" else "Anggota Tim"
                row_cells[1].text = m.get("full_name") or "-"
                row_cells[2].text = m.get("employee_number") or m.get("phone") or "-"
        else:
            doc.add_paragraph("Tidak ada personel teralokasi.")

        doc.add_paragraph().paragraph_format.space_after = Pt(6)

        # Jadwal Harian & Rincian Tugas
        doc.add_heading("3. Jadwal & Rincian Penugasan Harian", level=2)
        if days:
            sched_table = doc.add_table(rows=1, cols=4)
            sched_table.alignment = WD_TABLE_ALIGNMENT.CENTER
            hdr = sched_table.rows[0].cells
            hdr[0].text = "Tanggal"
            hdr[1].text = "Lokasi & Titik"
            hdr[2].text = "Tipe Pekerjaan"
            hdr[3].text = "Uraian Tugas"
            for c in hdr:
                c.paragraphs[0].runs[0].bold = True

            for d in days:
                row_cells = sched_table.add_row().cells
                row_cells[0].text = str(d.get("work_date") or "")[:10]
                row_cells[1].text = d.get("site_name") or plan.get("location_text") or "-"
                row_cells[2].text = d.get("work_type_name") or plan.get("work_type_name") or "-"

                tasks_text = []
                for t in d.get("tasks", []):
                    title = t if isinstance(t, str) else t.get("title", "")
                    if title:
                        tasks_text.append(f"• {title}")
                row_cells[3].text = "\n".join(tasks_text) if tasks_text else "-"
        else:
            doc.add_paragraph("Belum ada rincian tugas harian yang terjadwal.")

        doc.add_paragraph().paragraph_format.space_after = Pt(12)

        # Lembar Tanda Tangan
        sign_p = doc.add_paragraph()
        sign_p.add_run("Disahkan oleh:\n\n\n\n_______________________\nProject Manager (PM)").bold = True

        buffer = io.BytesIO()
        doc.save(buffer)
        return buffer.getvalue()

    @staticmethod
    def export_xlsx(detail: dict[str, Any]) -> bytes:
        """Menghasilkan file Excel XLSX matriks penugasan dan volume kerja."""
        try:
            import openpyxl
            from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
            from openpyxl.utils import get_column_letter
        except ImportError as err:
            raise AppError("DEPENDENCY_MISSING", "Pustaka openpyxl tidak tersedia.", status=503) from err

        wb = openpyxl.Workbook()
        ws_info = wb.active
        ws_info.title = "Ringkasan Rencana"

        plan = detail.get("plan", {})
        team = detail.get("team", [])
        days = detail.get("days", [])

        # Styles
        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        subhdr_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
        bold_font = Font(name="Calibri", size=11, bold=True)
        thin_border = Border(
            left=Side(style="thin", color="CBD5E1"),
            right=Side(style="thin", color="CBD5E1"),
            top=Side(style="thin", color="CBD5E1"),
            bottom=Side(style="thin", color="CBD5E1"),
        )

        # Title Sheet 1
        ws_info.merge_cells("A1:D1")
        ws_info["A1"] = "PT VISIONTECH INDOGRAHA - RENCANA KERJA OPERASIONAL"
        ws_info["A1"].font = Font(name="Calibri", size=14, bold=True, color="0F172A")
        ws_info["A1"].alignment = Alignment(horizontal="center", vertical="center")

        ws_info.merge_cells("A2:D2")
        period_txt = f"{plan.get('period_start')} s.d. {plan.get('period_end')}"
        ws_info["A2"] = f"Nomor: {plan.get('number') or 'DRAFT'} | Periode: {period_txt}"
        ws_info["A2"].font = Font(name="Calibri", size=10, italic=True)
        ws_info["A2"].alignment = Alignment(horizontal="center")

        # Table Metadata
        metadata = [
            ("Judul Pekerjaan", plan.get("title") or "-"),
            ("Kategori", plan.get("category_label") or plan.get("category") or "-"),
            ("Tipe Pekerjaan", plan.get("work_type_name") or "-"),
            ("Lokasi Kerja", plan.get("location_text") or "-"),
            ("Status", plan.get("status") or "DRAFT"),
            ("Zona Tugas", "Luar Kota" if plan.get("is_out_of_town") else "Dalam Kota"),
            ("Total Hari Kerja", len(days)),
            ("Jumlah Personel", len(team)),
        ]

        ws_info.append([])
        for label, val in metadata:
            row_idx = ws_info.max_row + 1
            ws_info.cell(row=row_idx, column=1, value=label).font = bold_font
            ws_info.cell(row=row_idx, column=1).fill = subhdr_fill
            ws_info.cell(row=row_idx, column=2, value=str(val))
            ws_info.cell(row=row_idx, column=1).border = thin_border
            ws_info.cell(row=row_idx, column=2).border = thin_border

        # Sheet 2: Jadwal Harian
        ws_sched = wb.create_sheet(title="Jadwal & Tugas")
        headers_sched = ["No", "Tanggal", "Tipe Pekerjaan", "Titik Lokasi", "Petugas Bertugas", "Daftar Tugas"]
        ws_sched.append(headers_sched)

        for col_idx, _h in enumerate(headers_sched, start=1):
            cell = ws_sched.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = thin_border

        for idx, d in enumerate(days, start=1):
            tasks_str = ", ".join(
                (t if isinstance(t, str) else t.get("title", ""))
                for t in d.get("tasks", [])
            )
            workers_str = ", ".join(str(w) for w in (d.get("members") or [])) or "Semua Tim"
            row_data = [
                idx,
                str(d.get("work_date") or "")[:10],
                d.get("work_type_name") or plan.get("work_type_name") or "-",
                d.get("site_name") or plan.get("location_text") or "-",
                workers_str,
                tasks_str or "-",
            ]
            ws_sched.append(row_data)
            for c_idx in range(1, len(row_data) + 1):
                ws_sched.cell(row=ws_sched.max_row, column=c_idx).border = thin_border

        # Sheet 3: Tim & Aset
        ws_team = wb.create_sheet(title="Tim & Kendaraan")
        headers_team = ["Peran", "Nama Lengkap", "Kontak / Nomor Karyawan"]
        ws_team.append(headers_team)
        for col_idx, _h in enumerate(headers_team, start=1):
            cell = ws_team.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = thin_border

        for m in team:
            row_data = [
                "Ketua Tim" if m.get("role_in_plan") == "LEADER" else "Anggota",
                m.get("full_name") or "-",
                m.get("phone") or m.get("employee_number") or "-",
            ]
            ws_team.append(row_data)
            for c_idx in range(1, len(row_data) + 1):
                ws_team.cell(row=ws_team.max_row, column=c_idx).border = thin_border

        # Auto-adjust column widths
        for sheet in wb.worksheets:
            for col in sheet.columns:
                max_len = max(len(str(cell.value or "")) for cell in col)
                col_letter = get_column_letter(col[0].column)
                sheet.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 45)

        buffer = io.BytesIO()
        wb.save(buffer)
        return buffer.getvalue()

    @staticmethod
    def export_pptx(detail: dict[str, Any]) -> bytes:
        """Menghasilkan file PowerPoint PPTX presentasi rencana kerja."""
        try:
            from pptx import Presentation
            from pptx.dml.color import RGBColor
            from pptx.util import Inches, Pt
        except ImportError as err:
            raise AppError("DEPENDENCY_MISSING", "Pustaka python-pptx tidak tersedia.", status=503) from err

        prs = Presentation()
        # Set 16:9 widescreen
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)

        plan = detail.get("plan", {})
        team = detail.get("team", [])
        days = detail.get("days", [])

        # Color Palette
        navy = RGBColor(15, 23, 42)  # type: ignore[no-untyped-call]
        blue = RGBColor(2, 132, 199)  # type: ignore[no-untyped-call]
        gray = RGBColor(100, 116, 139)  # type: ignore[no-untyped-call]

        # Slide 1: Cover Slide
        blank_slide_layout = prs.slide_layouts[6]
        slide1 = prs.slides.add_slide(blank_slide_layout)

        tx_box = slide1.shapes.add_textbox(Inches(1.5), Inches(2.0), Inches(10.33), Inches(3.5))
        tf = tx_box.text_frame
        tf.word_wrap = True

        p1 = tf.paragraphs[0]
        p1.text = "PT VISIONTECH INDOGRAHA"
        p1.font.size = Pt(20)
        p1.font.bold = True
        p1.font.color.rgb = blue

        p2 = tf.add_paragraph()
        p2.text = plan.get("title") or "Rencana Kerja Operasional"
        p2.font.size = Pt(36)
        p2.font.bold = True
        p2.font.color.rgb = navy
        p2.space_before = Pt(12)

        p3 = tf.add_paragraph()
        period_txt = f"{plan.get('period_start')} s.d. {plan.get('period_end')}"
        p3.text = f"Nomor: {plan.get('number') or 'DRAFT'} | Periode: {period_txt}"
        p3.font.size = Pt(16)
        p3.font.color.rgb = gray
        p3.space_before = Pt(12)

        # Slide 2: Ringkasan Proyek & Alokasi Tim
        slide2 = prs.slides.add_slide(blank_slide_layout)

        # Header Title
        title_box = slide2.shapes.add_textbox(Inches(1.0), Inches(0.8), Inches(11.33), Inches(1.0))
        p = title_box.text_frame.paragraphs[0]
        p.text = "Susunan Tim & Parameter Proyek"
        p.font.size = Pt(26)
        p.font.bold = True
        p.font.color.rgb = navy

        # Info Box Left
        left_box = slide2.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(5.5), Inches(4.5))
        tf_l = left_box.text_frame
        tf_l.word_wrap = True
        p_l = tf_l.paragraphs[0]
        p_l.text = "Parameter Pekerjaan"
        p_l.font.size = Pt(18)
        p_l.font.bold = True
        p_l.font.color.rgb = blue

        params = [
            f"Kategori: {plan.get('category_label') or plan.get('category') or '-'}",
            f"Tipe Pekerjaan: {plan.get('work_type_name') or '-'}",
            f"Lokasi: {plan.get('location_text') or '-'}",
            f"Status: {plan.get('status') or 'DRAFT'}",
            f"Zona: {'Luar Kota (>30km)' if plan.get('is_out_of_town') else 'Dalam Kota'}",
        ]
        for param in params:
            p_item = tf_l.add_paragraph()
            p_item.text = f"• {param}"
            p_item.font.size = Pt(14)
            p_item.font.color.rgb = navy
            p_item.space_before = Pt(8)

        # Info Box Right (Team)
        right_box = slide2.shapes.add_textbox(Inches(7.0), Inches(2.0), Inches(5.5), Inches(4.5))
        tf_r = right_box.text_frame
        tf_r.word_wrap = True
        p_r = tf_r.paragraphs[0]
        p_r.text = "Alokasi Tim Lapangan"
        p_r.font.size = Pt(18)
        p_r.font.bold = True
        p_r.font.color.rgb = blue

        for m in team:
            p_m = tf_r.add_paragraph()
            role = "Ketua Tim" if m.get("role_in_plan") == "LEADER" else "Anggota"
            p_m.text = f"• [{role}] {m.get('full_name') or '-'}"
            p_m.font.size = Pt(14)
            p_m.font.color.rgb = navy
            p_m.space_before = Pt(8)

        # Slide 3: Matriks Jadwal Pelaksanaan
        slide3 = prs.slides.add_slide(blank_slide_layout)
        t3_box = slide3.shapes.add_textbox(Inches(1.0), Inches(0.8), Inches(11.33), Inches(1.0))
        p3 = t3_box.text_frame.paragraphs[0]
        p3.text = "Jadwal & Agenda Pelaksanaan Harian"
        p3.font.size = Pt(26)
        p3.font.bold = True
        p3.font.color.rgb = navy

        # Agenda Content
        agenda_box = slide3.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(11.33), Inches(4.8))
        tf_ag = agenda_box.text_frame
        tf_ag.word_wrap = True

        for idx, d in enumerate(days[:6], start=1):  # Display up to 6 key days
            p_d = tf_ag.add_paragraph() if idx > 1 else tf_ag.paragraphs[0]
            work_date = str(d.get("work_date") or "")[:10]
            site = d.get("site_name") or plan.get("location_text") or "-"
            wtype = d.get("work_type_name") or plan.get("work_type_name") or "-"
            tasks_list = [t if isinstance(t, str) else t.get("title", "") for t in d.get("tasks", [])]
            tasks = ", ".join(tasks_list) or "Operasional"
            p_d.text = f"Hari ke-{idx} ({work_date}): {wtype} @ {site} — {tasks}"
            p_d.font.size = Pt(14)
            p_d.font.color.rgb = navy
            p_d.space_before = Pt(10)

        # Slide 4: Standar SOP & HSE
        slide4 = prs.slides.add_slide(blank_slide_layout)
        t4_box = slide4.shapes.add_textbox(Inches(1.0), Inches(0.8), Inches(11.33), Inches(1.0))
        p4 = t4_box.text_frame.paragraphs[0]
        p4.text = "Standarisasi K3 & Kepatuhan Dokumentasi"
        p4.font.size = Pt(26)
        p4.font.bold = True
        p4.font.color.rgb = navy

        hse_box = slide4.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(11.33), Inches(4.5))
        tf_hse = hse_box.text_frame
        tf_hse.word_wrap = True

        hse_points = [
            "Seluruh staf wajib menggunakan APD Lengkap (Helm, Rompi, Safety Shoes, Body Harness jika > 1.8m).",
            "Validasi presensi GPS dan biometrik wajah wajib dilakukan saat kedatangan di site klien.",
            "Wajib mengambil foto dokumentasi sesuai standarisasi 'Image Requirement' (sebelum, proses, selesai).",
            "Inspeksi armada dan perkakas kerja wajib dilaporkan sebelum mobilisasi ke lokasi proyek.",
            "Laporan harian dan form approval diselesaikan oleh Ketua Tim sebelum kepulangan dari site.",
        ]
        for idx, pt in enumerate(hse_points):
            p_pt = tf_hse.add_paragraph() if idx > 0 else tf_hse.paragraphs[0]
            p_pt.text = f"{idx + 1}. {pt}"
            p_pt.font.size = Pt(15)
            p_pt.font.color.rgb = navy
            p_pt.space_before = Pt(12)

        buffer = io.BytesIO()
        prs.save(buffer)
        return buffer.getvalue()

    @staticmethod
    def export_completion_docx(detail: dict[str, Any]) -> bytes:
        """Menghasilkan berkas Word DOCX Berita Acara Penyelesaian Pekerjaan (BAST) & Bill of Materials (BoM)."""
        try:
            import docx
            from docx.enum.table import WD_TABLE_ALIGNMENT
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            from docx.shared import Inches, Pt, RGBColor
        except ImportError as err:
            raise AppError("DEPENDENCY_MISSING", "Pustaka python-docx tidak tersedia.", status=503) from err

        doc = docx.Document()

        for section in doc.sections:
            section.top_margin = Inches(0.8)
            section.bottom_margin = Inches(0.8)
            section.left_margin = Inches(0.8)
            section.right_margin = Inches(0.8)

        # Header Kop Perusahaan
        title_p = doc.add_paragraph()
        title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_corp = title_p.add_run("PT VISIONTECH INDOGRAHA\n")
        run_corp.bold = True
        run_corp.font.size = Pt(14)
        run_corp.font.color.rgb = RGBColor(30, 41, 59)

        run_sub = title_p.add_run("BERITA ACARA SERAH TERIMA & REALISASI MATERIAL (BAST & BoM)\n")
        run_sub.bold = True
        run_sub.font.size = Pt(12)
        run_sub.font.color.rgb = RGBColor(71, 85, 105)

        order_no = detail.get("order_number") or detail.get("completion_id") or "DRAFT-COMPLETION"
        run_num = title_p.add_run(f"Nomor Order / BAST: {order_no}\n")
        run_num.font.size = Pt(10)
        run_num.font.italic = True

        doc.add_paragraph().paragraph_format.space_after = Pt(6)

        # 1. Informasi Order & Pelaksanaan
        doc.add_heading("1. Informasi Order Proyek & Kontrak", level=2)
        info_table = doc.add_table(rows=6, cols=2)
        info_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        info_table.autofit = True

        dates_str = f"{detail.get('start_work_date') or '-'} s.d. {detail.get('end_work_date') or '-'}"
        vol_str = (
            f"{detail.get('completed_target_unit', 0)} / {detail.get('total_target_unit', 0)} "
            f"{detail.get('unit_measure', 'Unit')}"
        )

        rows_data = [
            ("Nama Klien / Perusahaan", detail.get("client_name") or "-"),
            ("Judul Proyek / SPK", detail.get("project_title") or "-"),
            ("Divisi Pelaksana / PM", f"{detail.get('division_name') or '-'} / {detail.get('pm_name') or '-'}"),
            ("Lokasi Pelaksanaan", detail.get("site_address") or "-"),
            ("Linimasa Pelaksanaan", dates_str),
            ("Realisasi Volume Pekerjaan", f"{vol_str} ({detail.get('order_status', 'COMPLETED')})"),
        ]

        for i, (label, val) in enumerate(rows_data):
            cell_lbl = info_table.rows[i].cells[0]
            cell_val = info_table.rows[i].cells[1]
            cell_lbl.text = label
            cell_lbl.paragraphs[0].runs[0].bold = True
            cell_val.text = str(val)

        doc.add_paragraph().paragraph_format.space_after = Pt(6)

        # 2. Bill of Materials (BoM)
        doc.add_heading("2. Bill of Materials (BoM) Realisasi Pemakaian Material", level=2)
        bom_items = detail.get("bom_items") or []
        if bom_items:
            bom_table = doc.add_table(rows=1, cols=6)
            bom_table.alignment = WD_TABLE_ALIGNMENT.CENTER
            bom_table.autofit = True

            headers = ["No", "Kode", "Nama Material", "Estimasi", "Aktual", "Kategori / Catatan"]
            hdr_cells = bom_table.rows[0].cells
            for idx, h in enumerate(headers):
                hdr_cells[idx].text = h
                hdr_cells[idx].paragraphs[0].runs[0].bold = True

            for idx, it in enumerate(bom_items, start=1):
                row_cells = bom_table.add_row().cells
                row_cells[0].text = str(idx)
                row_cells[1].text = str(it.get("material_code") or "-")
                row_cells[2].text = str(it.get("material_name") or "-")
                row_cells[3].text = f"{it.get('estimated_qty', 0)} {it.get('unit', '')}"
                row_cells[4].text = f"{it.get('actual_qty', 0)} {it.get('unit', '')}"
                cat_notes = f"{it.get('category') or '-'}"
                if it.get("notes"):
                    cat_notes += f" ({it.get('notes')})"
                row_cells[5].text = cat_notes
        else:
            p_empty = doc.add_paragraph()
            run_empty = p_empty.add_run("Tidak ada daftar bon material (BoM) khusus yang terlampir.")
            run_empty.italic = True

        doc.add_paragraph().paragraph_format.space_after = Pt(6)

        # 3. Catatan & Kendala Lapangan
        doc.add_heading("3. Ringkasan Pekerjaan & Kendala Lapangan", level=2)
        summary_txt = detail.get("summary_notes") or "Pekerjaan terlaksana sesuai spesifikasi teknis dan SOP."
        doc.add_paragraph(f"Ringkasan: {summary_txt}")
        if detail.get("obstacles"):
            doc.add_paragraph(f"Kendala Lapangan: {detail.get('obstacles')}")

        doc.add_paragraph().paragraph_format.space_after = Pt(6)

        # 4. Lembar Pengesahan Tanda Tangan
        doc.add_heading("4. Lembar Pengesahan & Validasi Integritas", level=2)
        sig_table = doc.add_table(rows=3, cols=2)
        sig_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        sig_table.autofit = True

        cell_l_hdr = sig_table.rows[0].cells[0]
        cell_r_hdr = sig_table.rows[0].cells[1]
        cell_l_hdr.text = "Diselesaikan Oleh (Ketua Tim / Teknisi Lapangan):"
        cell_l_hdr.paragraphs[0].runs[0].bold = True
        cell_r_hdr.text = "Disetujui Oleh (Project Manager / OM):"
        cell_r_hdr.paragraphs[0].runs[0].bold = True

        ldr_signer = detail.get("leader_signer_name") or "( Belum Bertanda Tangan )"
        pm_signer = detail.get("pm_signer_name") or "( Belum Bertanda Tangan )"

        cell_l_body = sig_table.rows[1].cells[0]
        cell_r_body = sig_table.rows[1].cells[1]
        cell_l_body.text = f"\n\n\n\n{ldr_signer}\nTanggal: {detail.get('leader_signed_at') or '-'}"
        cell_r_body.text = f"\n\n\n\n{pm_signer}\nTanggal: {detail.get('pm_signed_at') or '-'}"

        cell_l_ftr = sig_table.rows[2].cells[0]
        cell_r_ftr = sig_table.rows[2].cells[1]
        sig_hash = detail.get("signature_hash") or "INTEGRITY-PENDING"
        order_stat = detail.get("order_status", "COMPLETED")
        cell_l_ftr.text = f"Status: TERVERIFIKASI SISTEM VMS\nHash: {str(sig_hash)[:16]}..."
        cell_l_ftr.paragraphs[0].runs[0].font.size = Pt(8)
        cell_r_ftr.text = f"Status Dokumen: RESMI ({order_stat})\nHash: {str(sig_hash)[:16]}..."
        cell_r_ftr.paragraphs[0].runs[0].font.size = Pt(8)

        buffer = io.BytesIO()
        doc.save(buffer)
        return buffer.getvalue()
