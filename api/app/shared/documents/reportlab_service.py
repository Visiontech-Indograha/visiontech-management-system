"""
app/shared/documents/reportlab_service.py
Generator dokumen PDF murni Python (ReportLab) yang 100% mandiri, bebas ketergantungan pustaka C (Pango/GTK)
sehingga berjalan stabil tanpa error di sistem operasi Windows lokal, Linux, maupun Docker.
"""
from __future__ import annotations

import io
from typing import Any

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.shared.documents.branding import visiontech_logo


def _tgl(value: Any) -> str:
    if not value:
        return "-"
    if hasattr(value, "strftime"):
        return str(value.strftime("%d/%m/%Y"))
    return str(value)


def _qty(value: Any) -> str:
    try:
        number = float(value or 0)
        return f"{number:.0f}" if number.is_integer() else f"{number:.2f}".rstrip("0").replace(".", ",")
    except (ValueError, TypeError):
        return str(value)

NAVY = colors.HexColor("#0F2744")
SLATE_BORDER = colors.HexColor("#CBD5E1")
LIGHT_BG = colors.HexColor("#F8FAFC")
DARK_TEXT = colors.HexColor("#1E293B")
MUTED_TEXT = colors.HexColor("#64748B")
GREEN_DONE = colors.HexColor("#166534")


class NumberedCanvas(canvas.Canvas):  # type: ignore[misc]
    """Canvas yang menghitung total halaman secara otomatis (dua lintasan)."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._saved_page_states: list[Any] = []

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_footer(num_pages)
            super().showPage()
        super().save()

    def draw_footer(self, page_count: int) -> None:
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(MUTED_TEXT)
        footer_text = f"Halaman {self._pageNumber} dari {page_count} — PT Visiontech Indograha"
        self.drawRightString(A4[0] - 1.5 * cm, 1.0 * cm, footer_text)
        self.restoreState()


def _get_styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "DocTitle",
            parent=sample["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=NAVY,
            alignment=1,  # Center
        ),
        "subtitle": ParagraphStyle(
            "DocSubTitle",
            parent=sample["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=MUTED_TEXT,
            alignment=1,
        ),
        "title_left": ParagraphStyle(
            "DocTitleLeft",
            parent=sample["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=NAVY,
            alignment=0,
        ),
        "subtitle_left": ParagraphStyle(
            "DocSubTitleLeft",
            parent=sample["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
            textColor=MUTED_TEXT,
            alignment=0,
        ),
        "h2": ParagraphStyle(
            "SectionH2",
            parent=sample["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=14,
            textColor=NAVY,
            spaceBefore=8,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=sample["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=DARK_TEXT,
        ),
        "body_bold": ParagraphStyle(
            "BodyBold",
            parent=sample["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=DARK_TEXT,
        ),
        "cell": ParagraphStyle(
            "Cell",
            parent=sample["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
            textColor=DARK_TEXT,
        ),
        "cell_bold": ParagraphStyle(
            "CellBold",
            parent=sample["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=10,
            textColor=DARK_TEXT,
        ),
        "cell_header": ParagraphStyle(
            "CellHeader",
            parent=sample["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=10,
            textColor=colors.white,
        ),
        "caption": ParagraphStyle(
            "Caption",
            parent=sample["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=9,
            textColor=MUTED_TEXT,
            alignment=1,
        ),
    }


def _safe_image(raw_bytes: bytes | None, max_w: float, max_h: float) -> Image | None:
    if not raw_bytes:
        return None
    try:
        pil_img = PILImage.open(io.BytesIO(raw_bytes))
        w, h = pil_img.size
        if w <= 0 or h <= 0:
            return None
        aspect = h / float(w)
        target_w = max_w
        target_h = target_w * aspect
        if target_h > max_h:
            target_h = max_h
            target_w = target_h / aspect
        return Image(io.BytesIO(raw_bytes), width=target_w, height=target_h)
    except (OSError, ValueError, KeyError):
        return None


def build_completion_pdf_reportlab(r: Any) -> bytes:
    """Membangun PDF Berita Acara Serah Terima (BAST) resmi dengan ReportLab."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    styles = _get_styles()
    story: list[Any] = []

    # 1. KOP SURAT
    vms_logo_bytes = (
        r.logos[0]
        if (r.logos and len(r.logos) > 0 and r.logos[0])
        else visiontech_logo()
    )
    logo_img = _safe_image(vms_logo_bytes, max_w=4.8 * cm, max_h=1.4 * cm)
    team_logo_bytes = r.logos[1] if (r.logos and len(r.logos) > 1) else None
    team_logo_img = _safe_image(team_logo_bytes, max_w=3.5 * cm, max_h=1.3 * cm) if team_logo_bytes else None

    company_info = [
        Paragraph("<b>PT VISIONTECH INDOGRAHA</b>", styles["title_left"]),
        Paragraph(
            "Telecommunication, Networking, Civil & MEP Contractor Solutions<br/>"
            "Email: operational@visiontech.co.id | Dokumen Berita Acara Resmi",
            styles["subtitle_left"],
        ),
    ]

    if team_logo_img:
        header_data = [[logo_img or "", company_info, team_logo_img]]
        header_table = Table(header_data, colWidths=[4.8 * cm, 9.7 * cm, 3.5 * cm])
        header_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (0, 0), "LEFT"),
            ("ALIGN", (1, 0), (1, 0), "LEFT"),
            ("ALIGN", (2, 0), (2, 0), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
        ]))
    else:
        header_data = [[logo_img or "", company_info]]
        header_table = Table(header_data, colWidths=[4.8 * cm, 13.2 * cm])
        header_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (0, 0), "LEFT"),
            ("ALIGN", (1, 0), (1, 0), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
        ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=NAVY, spaceAfter=8, spaceBefore=4))

    # 2. JUDUL DOKUMEN
    story.append(Paragraph("<b>BERITA ACARA SERAH TERIMA PEKERJAAN (BAST)</b>", styles["title"]))
    order_no = r.order.get("order_number") or r.order.get("spk_number") or "-"
    story.append(Paragraph(f"Nomor Referensi: <b>{order_no}</b>", styles["subtitle"]))
    story.append(Spacer(1, 8))

    # 3. TABEL INFORMASI PROYEK & KLIEN
    client_name = r.order.get("client_name") or "-"
    project_title = r.order.get("project_title") or "-"
    site_address = r.order.get("site_address") or "-"
    start_date = _tgl(r.order.get("start_work_date"))
    end_date = _tgl(r.order.get("end_work_date"))

    meta_data = [
        [
            Paragraph("<b>Pemberi Tugas / Klien:</b>", styles["cell_bold"]),
            Paragraph(str(client_name), styles["cell"]),
            Paragraph("<b>Tanggal Mulai:</b>", styles["cell_bold"]),
            Paragraph(start_date, styles["cell"]),
        ],
        [
            Paragraph("<b>Nama Pekerjaan:</b>", styles["cell_bold"]),
            Paragraph(str(project_title), styles["cell"]),
            Paragraph("<b>Tanggal Selesai:</b>", styles["cell_bold"]),
            Paragraph(end_date, styles["cell"]),
        ],
        [
            Paragraph("<b>Lokasi / Alamat:</b>", styles["cell_bold"]),
            Paragraph(str(site_address), styles["cell"]),
            Paragraph("<b>Status Verifikasi:</b>", styles["cell_bold"]),
            Paragraph("<font color='#166534'><b>SELESAI (DISAHKAN)</b></font>", styles["cell"]),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[4.0 * cm, 5.5 * cm, 3.5 * cm, 5.0 * cm])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
        ("BOX", (0, 0), (-1, -1), 0.5, SLATE_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, SLATE_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # 4. TABEL REALISASI TITIK PEKERJAAN
    story.append(Paragraph("<b>1. Rincian Realisasi Titik Pekerjaan</b>", styles["h2"]))
    points_header = [
        Paragraph("No", styles["cell_header"]),
        Paragraph("Titik / Item Pekerjaan", styles["cell_header"]),
        Paragraph("Fase", styles["cell_header"]),
        Paragraph("Target", styles["cell_header"]),
        Paragraph("Selesai", styles["cell_header"]),
        Paragraph("Status", styles["cell_header"]),
    ]
    points_rows = [points_header]
    for idx, p in enumerate(r.points, start=1):
        points_rows.append([
            Paragraph(str(idx), styles["cell"]),
            Paragraph(f"<b>{p.title}</b><br/>{p.location or ''}", styles["cell"]),
            Paragraph(p.phase_label, styles["cell"]),
            Paragraph(_qty(p.target), styles["cell"]),
            Paragraph(_qty(p.completed), styles["cell"]),
            Paragraph(f"<font color='#166534'><b>{p.status_label}</b></font>", styles["cell"]),
        ])
    if len(points_rows) == 1:
        points_rows.append([Paragraph("-", styles["cell"])] * 6)

    pt_table = Table(points_rows, colWidths=[1.0 * cm, 7.5 * cm, 3.0 * cm, 2.0 * cm, 2.0 * cm, 2.5 * cm])
    pt_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("BOX", (0, 0), (-1, -1), 0.5, SLATE_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, SLATE_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
    ]))
    story.append(pt_table)
    story.append(Spacer(1, 10))

    # 5. TABEL BILL OF MATERIALS (BOM TERPASANG)
    if r.bom:
        story.append(Paragraph("<b>2. Material & Komponen Terpasang (BoM)</b>", styles["h2"]))
        bom_header = [
            Paragraph("No", styles["cell_header"]),
            Paragraph("Nama Material / Perangkat", styles["cell_header"]),
            Paragraph("Kategori", styles["cell_header"]),
            Paragraph("Jumlah", styles["cell_header"]),
            Paragraph("Satuan", styles["cell_header"]),
        ]
        bom_rows = [bom_header]
        for idx, b in enumerate(r.bom, start=1):
            bom_rows.append([
                Paragraph(str(idx), styles["cell"]),
                Paragraph(str(b.get("material_name") or b.get("name") or "-"), styles["cell"]),
                Paragraph(str(b.get("category") or "MATERIAL"), styles["cell"]),
                Paragraph(_qty(b.get("qty") or 0), styles["cell"]),
                Paragraph(str(b.get("unit") or "unit"), styles["cell"]),
            ])
        bom_table = Table(bom_rows, colWidths=[1.0 * cm, 8.5 * cm, 3.5 * cm, 2.5 * cm, 2.5 * cm])
        bom_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("BOX", (0, 0), (-1, -1), 0.5, SLATE_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, SLATE_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ]))
        story.append(bom_table)
        story.append(Spacer(1, 10))

    # 6. DOKUMENTASI FOTO REALISASI (Grid 2 Kolom)
    photos = r.all_photos[:12]
    if photos:
        story.append(Paragraph("<b>3. Dokumentasi Foto Lapangan</b>", styles["h2"]))
        photo_cells: list[list[Any]] = []
        row: list[Any] = []
        for label, img_bytes in photos:
            rendered_img = _safe_image(img_bytes, max_w=8.5 * cm, max_h=5.5 * cm)
            cell_content: list[Any] = []
            if rendered_img:
                cell_content.append(rendered_img)
            cell_content.append(Paragraph(label or "Foto Dokumentasi", styles["caption"]))
            row.append(cell_content)
            if len(row) == 2:
                photo_cells.append(row)
                row = []
        if row:
            row.append([Paragraph("", styles["caption"])])
            photo_cells.append(row)

        photo_table = Table(photo_cells, colWidths=[9.0 * cm, 9.0 * cm])
        photo_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(KeepTogether(photo_table))
        story.append(Spacer(1, 12))

    # 7. BLOK TANDA TANGAN (3 Pihak: Tim, PM, Klien)
    leader_sig_img = _safe_image(r.leader_signature, max_w=4.5 * cm, max_h=2.2 * cm)
    pm_sig_img = _safe_image(r.pm_signature, max_w=4.5 * cm, max_h=2.2 * cm)

    sig_data = [
        [
            Paragraph("Dikerjakan Oleh,<br/><b>Ketua Tim Lapangan</b>", styles["cell_bold"]),
            Paragraph("Disetujui Oleh,<br/><b>Project Manager</b>", styles["cell_bold"]),
            Paragraph("Diterima & Disahkan,<br/><b>Perwakilan Klien / Pengawas</b>", styles["cell_bold"]),
        ],
        [
            leader_sig_img or Spacer(1, 2.2 * cm),
            pm_sig_img or Spacer(1, 2.2 * cm),
            Spacer(1, 2.2 * cm),
        ],
        [
            Paragraph("(................................................)", styles["cell"]),
            Paragraph("(................................................)", styles["cell"]),
            Paragraph("(................................................)", styles["cell"]),
        ],
    ]
    sig_table = Table(sig_data, colWidths=[6.0 * cm, 6.0 * cm, 6.0 * cm])
    sig_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(KeepTogether(sig_table))

    doc.build(story, canvasmaker=NumberedCanvas)
    return buf.getvalue()


def build_survey_pdf_reportlab(data: Any) -> bytes:
    """Membangun PDF Laporan Hasil Survei Lapangan langsung siap cetak/preview."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    styles = _get_styles()
    story: list[Any] = []

    # 1. KOP SURAT
    vms_logo_bytes = (data.logos.get("company") if data.logos else None) or visiontech_logo()
    logo_img = _safe_image(vms_logo_bytes, max_w=4.8 * cm, max_h=1.4 * cm)
    client_logo_bytes = data.logos.get("client") if data.logos else None
    client_logo_img = _safe_image(client_logo_bytes, max_w=4.0 * cm, max_h=1.3 * cm) if client_logo_bytes else None

    company_info = [
        Paragraph("<b>PT VISIONTECH INDOGRAHA</b>", styles["title_left"]),
        Paragraph("Telecommunication & Security Solutions | Dokumen Hasil Survei Teknis", styles["subtitle_left"]),
    ]

    if client_logo_img:
        header_data = [[logo_img or "", company_info, client_logo_img]]
        header_table = Table(header_data, colWidths=[4.8 * cm, 9.2 * cm, 4.0 * cm])
        header_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (0, 0), "LEFT"),
            ("ALIGN", (1, 0), (1, 0), "LEFT"),
            ("ALIGN", (2, 0), (2, 0), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
        ]))
    else:
        header_data = [[logo_img or "", company_info]]
        header_table = Table(header_data, colWidths=[4.8 * cm, 13.2 * cm])
        header_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (0, 0), "LEFT"),
            ("ALIGN", (1, 0), (1, 0), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
        ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=NAVY, spaceAfter=8, spaceBefore=4))

    # 2. JUDUL SURVEI
    story.append(Paragraph(f"<b>LAPORAN HASIL SURVEI TEKNIS {data.format.upper()}</b>", styles["title"]))
    story.append(Paragraph(f"Klien: <b>{data.client}</b> | Tanggal: <b>{data.date_text}</b>", styles["subtitle"]))
    story.append(Spacer(1, 8))

    # 3. RINGKASAN SURVEI
    summary_data = [
        [
            Paragraph("<b>Lokasi / Site:</b>", styles["cell_bold"]),
            Paragraph(data.location, styles["cell"]),
            Paragraph("<b>Tim Survei:</b>", styles["cell_bold"]),
            Paragraph(data.team_name or "Tim Lapangan", styles["cell"]),
        ],
        [
            Paragraph("<b>Tujuan Survei:</b>", styles["cell_bold"]),
            Paragraph(data.purpose or "Penentuan titik & kebutuhan instalasi", styles["cell"]),
            Paragraph("<b>Total Titik:</b>", styles["cell_bold"]),
            Paragraph(f"<b>{len(data.points)} Titik Disurvei</b>", styles["cell"]),
        ],
    ]
    summary_table = Table(summary_data, colWidths=[3.5 * cm, 6.0 * cm, 3.5 * cm, 5.0 * cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
        ("BOX", (0, 0), (-1, -1), 0.5, SLATE_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, SLATE_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 10))

    # 4. RINCIAN TITIK SURVEI & FOTO SOP
    story.append(Paragraph("<b>1. Rincian Titik & Kebutuhan Lapangan</b>", styles["h2"]))
    for idx, p in enumerate(data.points, start=1):
        point_elements: list[Any] = []
        point_elements.append(Paragraph(f"<b>Titik #{idx}: {p.name}</b> (Status: {p.status})", styles["body_bold"]))
        if p.remarks:
            point_elements.append(Paragraph("Catatan: " + "; ".join(p.remarks), styles["body"]))
        if p.needs:
            point_elements.append(Paragraph("Kebutuhan: " + ", ".join(p.needs), styles["body"]))

        # Foto per titik
        if p.photos:
            p_photos_row: list[Any] = []
            for sphoto in p.photos[:4]:
                simg = _safe_image(sphoto.image, max_w=4.2 * cm, max_h=3.0 * cm)
                if simg:
                    p_photos_row.append([simg, Paragraph(sphoto.slot or "Foto", styles["caption"])])
            if p_photos_row:
                p_table = Table([p_photos_row], colWidths=[4.5 * cm] * len(p_photos_row))
                p_table.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
                point_elements.append(p_table)

        point_elements.append(Spacer(1, 6))
        story.append(KeepTogether(point_elements))

    # 5. REKAPITULASI BOM HASIL SURVEI
    bom_list = getattr(data, "bom", None) or getattr(data, "general_bom", None) or []
    if bom_list:
        story.append(Paragraph("<b>2. Rekapitulasi Kebutuhan Material (BoM Hasil Survei)</b>", styles["h2"]))
        bom_rows = [
            [
                Paragraph("No", styles["cell_header"]),
                Paragraph("Nama Material / Perangkat", styles["cell_header"]),
                Paragraph("Jumlah", styles["cell_header"]),
                Paragraph("Satuan", styles["cell_header"]),
            ]
        ]
        for bidx, bitem in enumerate(bom_list, start=1):
            m_name = bitem[0] if len(bitem) > 0 else "-"
            m_qty = bitem[1] if len(bitem) > 1 else 0
            m_unit = bitem[2] if len(bitem) > 2 else "-"
            bom_rows.append([
                Paragraph(str(bidx), styles["cell"]),
                Paragraph(str(m_name), styles["cell"]),
                Paragraph(_qty(m_qty), styles["cell"]),
                Paragraph(str(m_unit), styles["cell"]),
            ])
        bom_tbl = Table(bom_rows, colWidths=[1.5 * cm, 10.5 * cm, 3.0 * cm, 3.0 * cm])
        bom_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("BOX", (0, 0), (-1, -1), 0.5, SLATE_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, SLATE_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ]))
        story.append(bom_tbl)
        story.append(Spacer(1, 10))

    # 6. SIGN-OFF
    sig_data = [
        [
            Paragraph("Dibuat Oleh,<br/><b>Ketua Tim Survei</b>", styles["cell_bold"]),
            Paragraph("Diperiksa & Disetujui,<br/><b>Project Manager</b>", styles["cell_bold"]),
        ],
        [Spacer(1, 2.0 * cm), Spacer(1, 2.0 * cm)],
        [
            Paragraph(f"({data.team_name or 'Ketua Tim'})", styles["cell"]),
            Paragraph("(Project Manager)", styles["cell"]),
        ],
    ]
    sig_table = Table(sig_data, colWidths=[9.0 * cm, 9.0 * cm])
    sig_table.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    story.append(KeepTogether(sig_table))

    doc.build(story, canvasmaker=NumberedCanvas)
    return buf.getvalue()
