"""
app/shared/documents/docx_kit.py
Perangkat kecil python-docx untuk dokumen resmi Visiontech: kop berlogo, tabel bergaris, gambar, blok tanda tangan.
"""
from __future__ import annotations

import io
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from docx import Document
from docx.document import Document as DocxDocument
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

LOGO = Path(__file__).resolve().parent / "templates" / "assets" / "logo-visiontech.png"
INK = RGBColor(30, 41, 59)
MUTED = RGBColor(100, 116, 139)
HEADER_FILL = "E2E8F0"


def new_document(margin_cm: float = 2.0) -> DocxDocument:
    doc = Document()
    for section in doc.sections:
        section.top_margin = section.bottom_margin = Cm(margin_cm)
        section.left_margin = section.right_margin = Cm(margin_cm)
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10.5)
    return doc


def letterhead(doc: DocxDocument, company: str, title: str, subtitle: str | None = None,
               client: str | None = None) -> None:
    """Kop: logo + nama perusahaan (kiri), klien (kanan), lalu judul dokumen di tengah."""
    table = doc.add_table(rows=1, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    left, right = table.rows[0].cells
    p = left.paragraphs[0]
    if LOGO.exists():
        p.add_run().add_picture(str(LOGO), height=Cm(1.4))
    run = left.add_paragraph().add_run(company)
    run.bold, run.font.size, run.font.color.rgb = True, Pt(12), INK
    if client:
        rp = right.paragraphs[0]
        rp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r = rp.add_run("Klien\n")
        r.font.size, r.font.color.rgb = Pt(8), MUTED
        r = rp.add_run(client)
        r.bold, r.font.size = True, Pt(12)
    _rule(doc)
    head = doc.add_paragraph()
    head.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = head.add_run(title.upper())
    r.bold, r.font.size, r.font.color.rgb = True, Pt(14), INK
    if subtitle:
        sub = doc.add_paragraph()
        sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = sub.add_run(subtitle)
        r.font.size, r.font.color.rgb = Pt(9.5), MUTED


def heading(doc: DocxDocument, text: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    r = p.add_run(text)
    r.bold, r.font.size, r.font.color.rgb = True, Pt(11.5), INK


def para(doc: DocxDocument, text: str, *, italic: bool = False, size: float | None = None) -> None:
    r = doc.add_paragraph().add_run(text)
    r.italic = italic
    if size:
        r.font.size = Pt(size)


def info_table(doc: DocxDocument, rows: Sequence[tuple[str, Any]]) -> None:
    table = doc.add_table(rows=0, cols=2)
    table.style = "Table Grid"
    for label, value in rows:
        cells = table.add_row().cells
        cells[0].width, cells[1].width = Cm(5), Cm(12)
        _shade(cells[0])
        cells[0].paragraphs[0].add_run(label).bold = True
        cells[1].text = "-" if value in (None, "") else str(value)


def grid(doc: DocxDocument, headers: Sequence[str], rows: Sequence[Sequence[Any]],
         widths_cm: Sequence[float] | None = None) -> None:
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        _shade(cell)
        cell.paragraphs[0].add_run(h).bold = True
    for row in rows:
        cells = table.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = "-" if v in (None, "") else str(v)
    if widths_cm:
        for row in table.rows:
            for i, w in enumerate(widths_cm):
                row.cells[i].width = Cm(w)


def picture_pair(doc: DocxDocument, photos: Sequence[tuple[str, bytes]], width_cm: float = 8.0) -> None:
    """Foto dua kolom dengan keterangan di bawahnya."""
    for start in range(0, len(photos), 2):
        pair = photos[start:start + 2]
        table = doc.add_table(rows=2, cols=2)
        for i, (label, image) in enumerate(pair):
            table.rows[0].cells[i].paragraphs[0].add_run().add_picture(io.BytesIO(image), width=Cm(width_cm))
            cap = table.rows[1].cells[i].paragraphs[0]
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = cap.add_run(label)
            r.italic, r.font.size = True, Pt(8.5)


def signatures(doc: DocxDocument, blocks: Sequence[tuple[str, str, str, bytes | None]]) -> None:
    """[(peran, nama, tanggal, png)] berdampingan."""
    table = doc.add_table(rows=1, cols=len(blocks))
    for i, (role, name, when, png) in enumerate(blocks):
        cell = table.rows[0].cells[i]
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run(role).bold = True
        img = cell.add_paragraph()
        img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if png:
            img.add_run().add_picture(io.BytesIO(png), height=Cm(1.8))
        else:
            img.add_run("\n\n\n")
        n = cell.add_paragraph()
        n.alignment = WD_ALIGN_PARAGRAPH.CENTER
        n.add_run(name).bold = True
        d = cell.add_paragraph()
        d.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = d.add_run(when)
        r.font.size, r.font.color.rgb = Pt(8.5), MUTED


def to_bytes(doc: DocxDocument) -> bytes:
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _shade(cell: Any) -> None:
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), HEADER_FILL)
    cell._tc.get_or_add_tcPr().append(shd)


def _rule(doc: DocxDocument) -> None:
    p = doc.add_paragraph()
    border = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    for k, v in (("w:val", "single"), ("w:sz", "12"), ("w:space", "1"), ("w:color", "1E293B")):
        bottom.set(qn(k), v)
    border.append(bottom)
    p._p.get_or_add_pPr().append(border)
