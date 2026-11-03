"""Tema slide laporan Visiontech (16:9): sampul navy + aksen emas, kepala slide berpita, kartu angka, tabel bergaris,
slide pekerjaan dengan badge berwarna & bingkai foto, dan penutup. Semua laporan .pptx memakai helper ini.

Palet mengikuti brand (docs/18): navy #232C6F, emas #F0C000; status: selesai hijau, berjalan biru,
sebagian/pindah hari kuning, terlambat merah, belum abu.
"""
from __future__ import annotations

import io
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.presentation import Presentation as PptxPresentation
from pptx.util import Cm, Emu, Pt

from app.shared.documents.branding import COMPANY_BOX_PX, KopLogos, fit_contain_png
from app.shared.documents.docx_kit import LOGO

LOGO_WHITE = Path(LOGO).with_name("logo-visiontech-white.png")
# Logo tim disimpan di objek Presentation (atribut ini) agar tak perlu diteruskan ke setiap slide.
TEAM_LOGO_ATTR = "team_logo_png"
FONT = "Segoe UI"

NAVY = "232C6F"
NAVY_DARK = "141A43"
NAVY_SOFT = "EEF0FA"
GOLD = "F0C000"
INK = "161A24"
MUTED = "5E6573"
LINE = "E2E5EC"
PAPER = "F7F8FB"
WHITE = "FFFFFF"

# Status & jenis pekerjaan → (isi, teks)
STATUS_COLOR = {
    "DONE": ("1E6B43", WHITE), "IN_PROGRESS": ("3569A0", WHITE), "TODO": ("8A91A0", WHITE),
    "PENDING_ROLLOVER": ("C7892A", WHITE), "SHIFTED_DAY": ("C7892A", WHITE), "LATE": ("B42318", WHITE),
    "CANCELLED": ("B42318", WHITE), "CANCELED": ("B42318", WHITE),
}
PHASE_COLOR = {
    "SURVEY": ("3569A0", WHITE), "PREPARATION": ("5E6573", WHITE), "INSTALLATION": ("1E6B43", WHITE),
    "REPLACEMENT": ("C7892A", WHITE), "MAINTENANCE": (NAVY, WHITE),
}

W, H = Cm(33.867), Cm(19.05)


def rgb(hex_: str) -> RGBColor:
    return RGBColor.from_string(hex_)  # type: ignore[no-untyped-call,no-any-return]


def deck(logos: KopLogos | None = None) -> PptxPresentation:
    """Presentasi kosong. Logo Visiontech selalu tampil; logo tim (`logos[1]`, bila ada) di sampingnya."""
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H
    team_logo = logos[1] if logos else None
    setattr(prs, TEAM_LOGO_ATTR, fit_contain_png(team_logo, COMPANY_BOX_PX) if team_logo else None)
    return prs


def _logo_width_cm(path: Path, height_cm: float) -> float:
    """Lebar logo (cm) pada tinggi `height_cm`, mengikuti rasio berkas asli."""
    with Image.open(path) as img:
        return height_cm * img.width / img.height


def _team_logo(prs: PptxPresentation) -> bytes | None:
    logo: bytes | None = getattr(prs, TEAM_LOGO_ATTR, None)
    return logo


def save(prs: PptxPresentation) -> bytes:
    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


# ── Elemen dasar ─────────────────────────────────────────────────────────────
def box(slide: Any, x: float, y: float, w: float, h: float, fill: str, *, shape: Any = MSO_SHAPE.RECTANGLE,
        line: str | None = None) -> Any:
    s = slide.shapes.add_shape(shape, Cm(x), Cm(y), Cm(w), Cm(h))
    s.fill.solid()
    s.fill.fore_color.rgb = rgb(fill)
    if line:
        s.line.color.rgb = rgb(line)
        s.line.width = Pt(0.75)
    else:
        s.line.fill.background()
    s.shadow.inherit = False
    return s


def text(slide: Any, x: float, y: float, w: float, h: float, value: str, *, size: float = 14, color: str = INK,
         bold: bool = False, align: Any = PP_ALIGN.LEFT, anchor: Any = MSO_ANCHOR.TOP, wrap: bool = True) -> Any:
    tb = slide.shapes.add_textbox(Cm(x), Cm(y), Cm(w), Cm(h))
    tf = tb.text_frame
    tf.word_wrap = wrap
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Cm(0.1)
    for i, line in enumerate(str(value).split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        run = p.add_run()
        run.text = line
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.name = FONT
        run.font.color.rgb = rgb(color)
    return tb


def pill(slide: Any, x: float, y: float, label: str, colors: tuple[str, str], *, w: float | None = None,
         h: float = 0.95, size: float = 11) -> float:
    """Badge membulat; mengembalikan lebar (cm) agar badge berikutnya bisa disusun berurutan."""
    width = w or max(2.6, 0.24 * len(label) + 1.2)
    s = box(slide, x, y, width, h, colors[0], shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    s.adjustments[0] = 0.5
    tf = s.text_frame
    tf.margin_left = tf.margin_right = Cm(0.2)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = label
    run.font.size, run.font.bold, run.font.name = Pt(size), True, FONT
    run.font.color.rgb = rgb(colors[1])
    return width


def blank(prs: PptxPresentation) -> Any:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = rgb(WHITE)
    return slide


# ── Slide ────────────────────────────────────────────────────────────────────
def cover(prs: PptxPresentation, title: str, subtitle: str, tagline: str, badge: str | None = None,
          emblem: str | None = None) -> None:
    """Sampul: latar navy, lingkaran dekoratif, garis emas, logo putih, judul besar."""
    slide = blank(prs)
    slide.background.fill.fore_color.rgb = rgb(NAVY)
    big = box(slide, 22.5, -6.0, 18.0, 18.0, NAVY_DARK, shape=MSO_SHAPE.OVAL)
    big.fill.fore_color.brightness = 0
    ring = box(slide, 25.0, 9.5, 14.0, 14.0, NAVY, shape=MSO_SHAPE.OVAL, line=GOLD)
    ring.line.width = Pt(6)
    box(slide, 0, 0, 0.5, 19.05, GOLD)
    team_logo = _team_logo(prs)
    slide.shapes.add_picture(str(LOGO_WHITE), Cm(2.2), Cm(1.8), height=Cm(1.9))  # logo Visiontech selalu tampil
    if team_logo:  # logo tim di kartu putih (logo tim bisa berwarna gelap; kartu menjaga keterbacaannya)
        box(slide, 24.4, 2.6, 8.6, 4.0, WHITE, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
        slide.shapes.add_picture(io.BytesIO(team_logo), Cm(24.9), Cm(3.5), width=Cm(7.6))
    if badge:
        pill(slide, 2.2, 6.1, badge.upper(), (GOLD, NAVY_DARK), size=12)
    text(slide, 2.2, 7.4, 22, 4.2, title, size=40, color=WHITE, bold=True)
    box(slide, 2.2, 12.0, 4.0, 0.18, GOLD)
    text(slide, 2.2, 12.5, 22, 1.4, subtitle, size=18, color="DDE1F3")
    text(slide, 2.2, 16.6, 22, 1.0, tagline, size=11, color="BCC3E6")
    if team_logo and emblem:
        text(slide, 23.8, 7.0, 10.0, 1.0, emblem, size=14, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    elif emblem:  # lambang tim (inisial) — tim belum punya logo sendiri
        words = emblem.replace("Tim ", "").split() or ["T"]
        initials = (words[0] if len(words) == 1 or len(words[0]) <= 4 else "".join(w[0] for w in words[:2]))[:4].upper()
        disc = box(slide, 26.2, 3.2, 5.2, 5.2, GOLD, shape=MSO_SHAPE.OVAL)
        tf = disc.text_frame
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        para = tf.paragraphs[0]
        para.alignment = PP_ALIGN.CENTER
        run = para.add_run()
        run.text = initials
        run.font.size, run.font.bold, run.font.name = Pt(44 if len(initials) <= 2 else 30), True, FONT
        run.font.color.rgb = rgb(NAVY_DARK)
        text(slide, 23.8, 8.7, 10.0, 1.0, emblem, size=14, color=WHITE, bold=True, align=PP_ALIGN.CENTER)


def page(prs: PptxPresentation, title: str, kicker: str = "", *, footer: str = "") -> Any:
    """Slide isi: pita kiri emas, judul navy, logo kecil kanan atas, kaki halaman bernomor."""
    slide = blank(prs)
    box(slide, 0, 0, 33.867, 19.05, PAPER)
    box(slide, 0, 0, 33.867, 3.2, WHITE)
    box(slide, 0, 0, 0.5, 3.2, GOLD)
    if kicker:
        text(slide, 1.3, 0.55, 24, 0.8, kicker.upper(), size=10, color=MUTED, bold=True)
    text(slide, 1.3, 1.15, 26, 1.6, title, size=24, color=NAVY, bold=True, wrap=False)
    team_logo = _team_logo(prs)
    vms_x = 32.6 - _logo_width_cm(LOGO, 1.3)  # logo Visiontech kanan atas, selalu tampil (tinggi 1,3 cm)
    slide.shapes.add_picture(str(LOGO), Cm(vms_x), Cm(0.9), height=Cm(1.3))
    if team_logo:  # logo tim di kirinya, proporsional (lebar mengikuti rasio kotak logo)
        width = 1.3 * COMPANY_BOX_PX[0] / COMPANY_BOX_PX[1]
        slide.shapes.add_picture(io.BytesIO(team_logo), Cm(vms_x - 0.6 - width), Cm(0.9), height=Cm(1.3))
    box(slide, 0, 3.2, 33.867, 0.06, LINE)
    number = len(prs.slides)
    text(slide, 1.3, 18.1, 26, 0.7, footer or "PT Visiontech Indograha", size=9, color=MUTED)
    text(slide, 30.0, 18.1, 2.6, 0.7, str(number), size=9, color=MUTED, align=PP_ALIGN.RIGHT)
    return slide


def kpis(slide: Any, cards: Sequence[tuple[str, str, str]], *, y: float = 4.2) -> None:
    """Kartu angka besar: (angka, keterangan, warna aksen)."""
    n = max(1, len(cards))
    gap, width = 0.6, (31.3 - 0.6 * (n - 1)) / n
    for i, (value, label, accent) in enumerate(cards):
        x = 1.3 + i * (width + gap)
        card = box(slide, x, y, width, 3.6, WHITE, shape=MSO_SHAPE.ROUNDED_RECTANGLE, line=LINE)
        card.adjustments[0] = 0.08
        box(slide, x, y + 0.5, 0.18, 2.6, accent)
        text(slide, x + 0.6, y + 0.35, width - 0.9, 1.8, value, size=30, color=accent, bold=True)
        text(slide, x + 0.6, y + 2.25, width - 0.9, 1.0, label, size=11, color=MUTED)


def bars(slide: Any, rows: Sequence[tuple[str, int, str]], *, x: float, y: float, w: float) -> None:
    """Batang horizontal sederhana: (label, jumlah, warna)."""
    top = max([v for _, v, _ in rows] or [1]) or 1
    for i, (label, value, color) in enumerate(rows):
        yy = y + i * 1.15
        text(slide, x, yy, 5.0, 0.9, label, size=12, color=INK, anchor=MSO_ANCHOR.MIDDLE)
        box(slide, x + 5.2, yy + 0.2, w - 7.0, 0.55, LINE, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
        box(slide, x + 5.2, yy + 0.2, max(0.4, (w - 7.0) * value / top), 0.55, color, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
        text(slide, x + w - 1.6, yy, 1.6, 0.9, str(value), size=12, color=INK, bold=True, align=PP_ALIGN.RIGHT,
             anchor=MSO_ANCHOR.MIDDLE)


def table(slide: Any, headers: Sequence[str], rows: Sequence[Sequence[Any]], widths: Sequence[float], *,
          y: float = 4.0, status_col: int | None = None, statuses: Sequence[str] = ()) -> None:
    """Tabel: kepala navy, baris belang, kolom status berwarna."""
    shape = slide.shapes.add_table(len(rows) + 1, len(headers), Cm(1.3), Cm(y), Cm(sum(widths)),
                                   Cm(0.95 * (len(rows) + 1)))
    tbl = shape.table
    for c, wdt in enumerate(widths):
        tbl.columns[c].width = Cm(wdt)
    for r_i in range(len(rows) + 1):
        tbl.rows[r_i].height = Cm(0.95)
    for c, h in enumerate(headers):
        _cell(tbl.cell(0, c), h, fill=NAVY, color=WHITE, bold=True)
    for r_i, row in enumerate(rows, start=1):
        fill = WHITE if r_i % 2 else NAVY_SOFT
        for c, v in enumerate(row):
            value = "-" if v in (None, "") else str(v)
            if status_col is not None and c == status_col and r_i - 1 < len(statuses):
                col = STATUS_COLOR.get(statuses[r_i - 1], (MUTED, WHITE))[0]
                _cell(tbl.cell(r_i, c), value, fill=fill, color=col, bold=True)
            else:
                _cell(tbl.cell(r_i, c), value, fill=fill, color=INK)


def _cell(cell: Any, value: str, *, fill: str, color: str, bold: bool = False) -> None:
    cell.fill.solid()
    cell.fill.fore_color.rgb = rgb(fill)
    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    cell.margin_left = cell.margin_right = Cm(0.2)
    tf = cell.text_frame
    tf.text = value
    for p in tf.paragraphs:
        for run in p.runs:
            run.font.size, run.font.bold, run.font.name = Pt(10.5), bold, FONT
            run.font.color.rgb = rgb(color)


def work_slide(prs: PptxPresentation, *, kicker: str, title: str, phase: str, phase_label: str, status: str,
               status_label: str, note: str, progress: str, photos: Sequence[tuple[str, bytes]],
               footer: str = "") -> None:
    """Satu pekerjaan: badge jenis & status, kartu keterangan, foto berbingkai dengan label."""
    slide = page(prs, title, kicker, footer=footer)
    x = 1.3
    x += pill(slide, x, 3.8, phase_label, PHASE_COLOR.get(phase, (NAVY, WHITE))) + 0.3
    x += pill(slide, x, 3.8, status_label, STATUS_COLOR.get(status, (MUTED, WHITE))) + 0.3
    pill(slide, x, 3.8, progress, (NAVY_SOFT, NAVY))
    card = box(slide, 1.3, 5.15, 31.3, 1.5, WHITE, shape=MSO_SHAPE.ROUNDED_RECTANGLE, line=LINE)
    card.adjustments[0] = 0.15
    text(slide, 1.8, 5.3, 30.3, 1.2, f"Keterangan: {note or '-'}", size=12, color=INK, anchor=MSO_ANCHOR.MIDDLE)
    shown = list(photos)[:3]
    if not shown:
        empty = box(slide, 1.3, 7.2, 31.3, 9.8, WHITE, shape=MSO_SHAPE.ROUNDED_RECTANGLE, line=LINE)
        empty.adjustments[0] = 0.04
        text(slide, 1.3, 11.5, 31.3, 1.0, "Belum ada foto untuk pekerjaan ini", size=13, color=MUTED,
             align=PP_ALIGN.CENTER)
        return
    gap = 0.6
    width = (31.3 - gap * (len(shown) - 1)) / len(shown)
    max_h = 8.6
    for i, (label, image) in enumerate(shown):
        left = 1.3 + i * (width + gap)
        frame = box(slide, left, 7.2, width, 1.0, WHITE, shape=MSO_SHAPE.ROUNDED_RECTANGLE, line=LINE)
        frame.adjustments[0] = 0.04
        pic = slide.shapes.add_picture(io.BytesIO(image), Cm(left + 0.3), Cm(7.5), width=Cm(width - 0.6))
        if pic.height > Cm(max_h):  # foto tegak → batasi tinggi, tengahkan
            ratio = Cm(max_h) / pic.height
            pic.height = Cm(max_h)
            pic.width = Emu(int(pic.width * ratio))
            pic.left = Emu(int(Cm(left) + (Cm(width) - pic.width) / 2))
        caption_y = (pic.top + pic.height) / 360000 + 0.2  # EMU → cm
        frame.height = Emu(int(pic.top + pic.height - Cm(7.2) + Cm(1.4)))  # bingkai mengikuti tinggi foto
        text(slide, left + 0.3, caption_y, width - 0.6, 0.9, label, size=11, color=NAVY, bold=True)


def closing(prs: PptxPresentation, line: str) -> None:
    slide = blank(prs)
    slide.background.fill.fore_color.rgb = rgb(NAVY)
    box(slide, 0, 0, 0.5, 19.05, GOLD)
    ring = box(slide, -5.0, 9.0, 14.0, 14.0, NAVY, shape=MSO_SHAPE.OVAL, line=GOLD)
    ring.line.width = Pt(6)
    team_logo = _team_logo(prs)
    if team_logo:  # logo Visiontech di kiri, logo tim di kartu putih di kanan (sama seperti sampul)
        slide.shapes.add_picture(str(LOGO_WHITE), Cm(5.0), Cm(5.2), height=Cm(2.6))
        box(slide, 19.9, 4.5, 10.0, 4.0, WHITE, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
        slide.shapes.add_picture(io.BytesIO(team_logo), Cm(20.43), Cm(5.2), width=Cm(9.0))
    else:
        slide.shapes.add_picture(str(LOGO_WHITE), Cm(12.4), Cm(5.2), height=Cm(2.6))
    text(slide, 2, 8.8, 29.9, 1.8, "Terima kasih", size=36, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    text(slide, 2, 10.8, 29.9, 1.0, line, size=14, color="BCC3E6", align=PP_ALIGN.CENTER)
