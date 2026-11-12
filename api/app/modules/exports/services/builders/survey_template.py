"""
app/modules/exports/services/builders/survey_template.py
Laporan survei ACS / CCTV yang SAMA dengan dokumen contoh pemilik (docs/37): berkas contoh dipakai sebagai master
template — kop, footer, gaya, ukuran kertas & margin, sampul, serta elemen prototipe (judul titik, tabel foto,
remark, material, tabel FO, BoM, penutup) DIKLON lalu diisi data survei. Tidak ada tata letak yang digambar ulang.

Peta prototipe = indeks elemen body pada master (lihat SPECS); bila master diganti, indeks ikut disesuaikan.
"""
from __future__ import annotations

import copy
import io
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

from docx import Document
from docx.document import Document as DocumentObject
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm
from docx.text.paragraph import Paragraph
from PIL import Image

from app.modules.exports.services.builders.model import omitted_note
from app.shared.documents.branding import apply_logos

TEMPLATES = Path(__file__).resolve().parents[4] / "shared" / "documents" / "templates"
SAMPLE_CLIENT = "PERTAMINA HULU ROKAN"
# Teks proyek bawaan master (kop, footer, sampul). Diganti judul pekerjaan & klien nyata; tidak boleh tersisa.
MASTER_TITLES = (
    ("NEW CCTV INSTALLATION AT PHR ZONA ROKAN", "{title}"),
    ("INSTALLASI BARU CCTV- ACS AREA ZONA ROKAN", "{title}"),
    ("NEW ACS AND CCTV INSTALLATION AT SMO SOUTH AREA", "{title}"),
    ("SURVEY REPORT NEW CCTV INSTALATION", "LAPORAN SURVEI {title}"),
    ("INSTALLASI ACS", "{title}"),
    ("Proposal for New CCTV and ACS Installation", "Proposal: {title}"),
    ("Proposal for New CCTV Installation", "Proposal: {title}"),
)

# Kolom tabel "Hitungan installasi Fiber Optic (FO) CCTV" (urutan = kolom master, mulai kolom ke-3).
FO_NUMERIC = ["Galian/Tarikan", "Indoor Cable", "Spare cable", "Kabel FO", "Kabel Power", "Cable Subduct", "Pipe 2\"",
              "Patch Cord SC-SC", "Pigtail SC", "FDU", "Concrete Cable Cover", "Concrete Marker Block (Straight)",
              "Concrete Marker Block (Bend)", "Plastic Marker Tape"]
FO_TEXT = ["Uplink Switch", "Remark"]
FO_COLUMNS = FO_NUMERIC + FO_TEXT

SPECS: dict[str, dict[str, Any]] = {
    "ACS": {
        "file": "survey_acs.docx",
        "cover_end": 20,  # paragraf penutup sampul (berisi section break)
        "client": 6, "date": 16, "location": 17, "purpose": 18,
        "activity_heading": 21, "activity_table": 23, "narrative": [25], "narrative_indent": "          ",
        "layout_heading": 26, "layout_image": 27, "layout_legend": [28, 29, 30],
        "fo_heading": None, "fo_table": None,
        "docs_heading": 32, "point_heading": 34, "photo_table": 35, "photo_table_single": 90,
        "remark_label": 36, "remark_item": 37, "material_label": 56, "material_item": 57,
        "bom_heading": 173, "bom_table": 174,
        "closing": [178, 179, 180, 182, 183, 184], "signature": 184, "team_line": None, "names_line": None,
    },
    "CCTV": {
        "file": "survey_cctv.docx",
        "cover_end": 30,
        "client": 6, "date": 14, "location": 16, "purpose": 18,
        "activity_heading": 31, "activity_table": 33, "narrative": [34, 35], "narrative_indent": "",
        "layout_heading": 36, "layout_image": 37, "layout_legend": [],
        "fo_heading": 56, "fo_table": 57,
        "docs_heading": 59, "point_heading": 60, "photo_table": 62, "photo_table_single": None,
        "remark_label": 63, "remark_item": 64, "material_label": None, "material_item": None,
        "bom_heading": 129, "bom_table": 131,
        "closing": [134, 135, 136, 137, 138, 139], "signature": None, "team_line": 138, "names_line": 139,
    },
}


@dataclass
class SurveyPhoto:
    slot: str
    image: bytes


@dataclass
class SurveyPointDoc:
    name: str
    remarks: list[str]
    photos: list[SurveyPhoto]
    materials: list[tuple[str, Decimal, str]] = field(default_factory=list)  # (nama, qty, satuan)
    needs: list[str] = field(default_factory=list)
    cable: dict[str, str] = field(default_factory=dict)  # kolom FO → nilai
    slots: list[str] = field(default_factory=list)  # slot foto jenis titiknya (urut template)
    status: str = "PROPOSED"  # EXISTING (sudah terpasang) / PROPOSED (usulan baru) → warna penanda layout


@dataclass
class SurveyDoc:
    format: str  # ACS | CCTV
    client: str
    date_text: str  # "21 September 2026"
    activity_date_text: str  # ACS "21-September-2026", CCTV "17 September 2026"
    location: str
    purpose: str
    activities: list[str]
    narrative: list[str]
    points: list[SurveyPointDoc]
    bom: list[tuple[str, Decimal, str, str]]  # (nama, qty, satuan, kelompok: jenis titik / "Umum")
    team_name: str
    leader_name: str
    member_names: list[str]
    logos: dict[str, bytes] = field(default_factory=dict)
    auto_layout: bytes | None = None  # peta satelit + penanda titik (static_map)  # logo kop pengganti (company/client)
    project_title: str = ""  # judul pekerjaan (order) → kop, footer, sampul
    omitted_photos: int = 0  # foto yang terpotong batas jumlah (dicatat di dokumen)


# ── Helper teks: isi run tanpa merusak format ─────────────────────────────────
def _texts(el: Any) -> list[Any]:
    return list(el.iter(qn("w:t")))


def set_text(el: Any, value: str) -> None:
    """Seluruh teks paragraf = value (format run pertama dipakai); tab dibuang."""
    ts = _texts(el)
    for tab in list(el.iter(qn("w:tab"))):
        if tab.getparent() is not None and tab.getparent().tag == qn("w:r"):
            tab.getparent().remove(tab)
    if not ts:
        run = OxmlElement("w:r")
        t = OxmlElement("w:t")
        run.append(t)
        el.append(run)
        ts = [t]
    ts[0].text = value
    ts[0].set(qn("xml:space"), "preserve")
    for t in ts[1:]:
        t.text = ""


def set_after(el: Any, marker: str, value: str) -> None:
    """Pertahankan teks sampai run yang memuat `marker` (dan spasi/tab sesudahnya), ganti sisanya dengan value."""
    ts = _texts(el)
    idx = next((i for i, t in enumerate(ts) if marker in (t.text or "")), None)
    if idx is None:
        set_text(el, value)
        return
    rest = list(ts[idx + 1:])
    while rest and not (rest[0].text or "").strip():
        rest = rest[1:]
    if not rest:
        ts[idx].text = (ts[idx].text or "") + value
        return
    rest[0].text = value
    rest[0].set(qn("xml:space"), "preserve")
    for t in rest[1:]:
        t.text = ""


def replace_in(el: Any, old: str, new: str) -> None:
    """Ganti `old` → `new` walau terpecah di beberapa run (dipakai untuk nama klien di kop/footer)."""
    ts = _texts(el)
    full = "".join(t.text or "" for t in ts)
    start = full.upper().find(old.upper())
    if start < 0:
        return
    end, pos, placed = start + len(old), 0, False
    for t in ts:
        text = t.text or ""
        a, b = pos, pos + len(text)
        pos = b
        if b <= start or a >= end:
            continue
        keep_left = text[: max(0, start - a)]
        keep_right = text[max(0, end - a):] if b > end else ""
        t.text = keep_left + (new if not placed else "") + keep_right
        t.set(qn("xml:space"), "preserve")
        placed = True


def _keep_with_next(p: Any) -> None:
    ppr = p.find(qn("w:pPr"))
    if ppr is None:
        ppr = OxmlElement("w:pPr")
        p.insert(0, ppr)
    if ppr.find(qn("w:keepNext")) is None:  # urutan skema: pStyle lalu keepNext
        style = ppr.find(qn("w:pStyle"))
        ppr.insert(list(ppr).index(style) + 1 if style is not None else 0, OxmlElement("w:keepNext"))


def _cell_photo_spacing(p: Any) -> None:
    """Ruang 6 pt di atas & bawah foto agar gambar tidak menempel/menutupi garis tabel."""
    ppr = p.find(qn("w:pPr"))
    if ppr is None:
        ppr = OxmlElement("w:pPr")
        p.insert(0, ppr)
    spacing = ppr.find(qn("w:spacing"))
    if spacing is None:
        spacing = OxmlElement("w:spacing")
        jc = ppr.find(qn("w:jc"))
        if jc is not None:
            jc.addprevious(spacing)
        else:
            ppr.append(spacing)
    spacing.set(qn("w:before"), "120")
    spacing.set(qn("w:after"), "120")
    spacing.set(qn("w:line"), "240")
    spacing.set(qn("w:lineRule"), "auto")


def _clear_runs(p: Any) -> None:
    for child in list(p):
        if child.tag != qn("w:pPr"):
            p.remove(child)


def _note_paragraph(text: str) -> Any:
    """Paragraf catatan polos (miring) untuk keterangan dokumen."""
    p = OxmlElement("w:p")
    run = OxmlElement("w:r")
    props = OxmlElement("w:rPr")
    props.append(OxmlElement("w:i"))
    run.append(props)
    t = OxmlElement("w:t")
    t.text = text
    t.set(qn("xml:space"), "preserve")
    run.append(t)
    p.append(run)
    return p


def _page_break() -> Any:
    p = OxmlElement("w:p")
    r = OxmlElement("w:r")
    br = OxmlElement("w:br")
    br.set(qn("w:type"), "page")
    r.append(br)
    p.append(r)
    return p


def _picture_dims(image: bytes, max_w_cm: float, max_h_cm: float) -> tuple[Cm, Cm]:
    with Image.open(io.BytesIO(image)) as img:
        w, h = img.size
    ratio = min(max_w_cm / w, max_h_cm / h)
    return Cm(w * ratio), Cm(h * ratio)


def _add_picture(doc: DocumentObject, p_el: Any, image: bytes, max_w_cm: float, max_h_cm: float) -> None:
    width, height = _picture_dims(image, max_w_cm, max_h_cm)
    Paragraph(p_el, doc._body).add_run().add_picture(io.BytesIO(image), width=width, height=height)


def _extents_cm(el: Any) -> list[tuple[float, float]]:
    """Ukuran gambar contoh di prototipe (wp:extent, EMU → cm): kotak maksimum gambar pengganti."""
    out = []
    for ext in el.iter(qn("wp:extent")):
        out.append((int(ext.get("cx")) / 360000, int(ext.get("cy")) / 360000))
    return out


def _cell_width_cm(tc: Any) -> float | None:
    """Lebar sel dari tcW (dxa = 1/20 pt) → cm."""
    w = tc.find(qn("w:tcPr") + "/" + qn("w:tcW"))
    if w is None or w.get(qn("w:type")) not in (None, "dxa"):
        return None
    return int(w.get(qn("w:w"))) / 567


def _usable_width_cm(doc: DocumentObject) -> float:
    s = doc.sections[-1]
    return float(((s.page_width or 0) - (s.left_margin or 0) - (s.right_margin or 0)) / 360000)


def _qty(value: Decimal | float | int) -> str:
    number = Decimal(str(value))
    return f"{number:f}".rstrip("0").rstrip(".") if "." in f"{number:f}" else f"{number:f}"


# ── Tabel ─────────────────────────────────────────────────────────────────────
def _rows(tbl: Any) -> list[Any]:
    return list(tbl.findall(qn("w:tr")))


def _cells(tr: Any) -> list[Any]:
    return list(tr.findall(qn("w:tc")))


def _cell_set(tc: Any, value: str, marker: str | None = None) -> None:
    ps = tc.findall(qn("w:p"))
    for extra in ps[1:]:
        tc.remove(extra)
    if marker:
        set_after(ps[0], marker, value)
    else:
        set_text(ps[0], value)


def _fill_rows(tbl: Any, proto_index: int, keep_tail: int, rows: list[list[str]]) -> None:
    """Baris data = klon baris prototipe; baris lain di antara header dan `keep_tail` (mis. Total) dibuang."""
    all_rows = _rows(tbl)
    proto = all_rows[proto_index]
    tail = all_rows[len(all_rows) - keep_tail:] if keep_tail else []
    for tr in all_rows[proto_index:len(all_rows) - keep_tail if keep_tail else None]:
        tbl.remove(tr)
    anchor = tail[0] if tail else None
    for values in rows:
        tr = copy.deepcopy(proto)
        for tc, value in zip(_cells(tr), values, strict=False):
            _cell_set(tc, value)
        if anchor is not None:
            anchor.addprevious(tr)
        else:
            tbl.append(tr)


# ── Builder ───────────────────────────────────────────────────────────────────
def build_survey_docx(data: SurveyDoc) -> bytes:
    spec = SPECS[data.format]
    doc = Document(str(TEMPLATES / spec["file"]))
    body = doc.element.body
    elements = list(body.iterchildren())
    proto = {i: copy.deepcopy(el) for i, el in enumerate(elements)}
    final_sect = elements[-1]
    width = _usable_width_cm(doc)
    apply_logos(doc, data.format, data.logos)
    # Word: jangan kompres gambar otomatis saat disimpan/diekspor (foto & peta tetap tajam).
    settings = doc.settings.element
    if settings.find(qn("w:doNotAutoCompressPictures")) is None:
        settings.insert(0, OxmlElement("w:doNotAutoCompressPictures"))

    def clone(i: int) -> Any:
        return copy.deepcopy(proto[i])

    # Sampul tetap; isi klien, tanggal, lokasi, tujuan.
    client = data.client.upper()
    title = data.project_title.strip() or client
    set_text(elements[spec["client"]], client)
    set_after(elements[spec["date"]], ":", data.date_text)
    set_after(elements[spec["location"]], ":", data.location)
    set_after(elements[spec["purpose"]], ":", data.purpose)
    titles = [(old, new.format(title=title)) for old, new in MASTER_TITLES]
    for section in doc.sections:
        for part in (section.header, section.footer, section.first_page_header, section.first_page_footer):
            for p in part._element.iter(qn("w:p")):
                replace_in(p, SAMPLE_CLIENT, client.removeprefix("PT. ").removeprefix("PT "))
                for old, new in titles:
                    replace_in(p, old, new)
    for el in elements[: spec["cover_end"] + 1]:
        if el.tag == qn("w:p"):
            for old, new in titles:
                replace_in(el, old, new)
    for el in elements[spec["cover_end"] + 1:-1]:
        body.remove(el)

    out: list[Any] = []

    # Aktivitas
    out.append(clone(spec["activity_heading"]))
    table = clone(spec["activity_table"])
    if data.format == "CCTV":
        rows = _rows(table)
        first, cont = rows[1], rows[2]
        for tr in rows[1:]:
            table.remove(tr)
        for n, line in enumerate(data.activities or ["Survei Lokasi"]):
            tr = copy.deepcopy(first if n == 0 else cont)
            cells = _cells(tr)
            if n == 0:
                _cell_set(cells[0], data.activity_date_text)
            _cell_set(cells[1], line, marker="-")
            table.append(tr)
    else:
        _fill_rows(table, 1, 0, [[data.activity_date_text, line] for line in (data.activities or ["Survei"])])
    out.append(table)
    out.append(OxmlElement("w:p"))
    narr_proto = spec["narrative"][-1]
    for text in data.narrative:
        p = clone(narr_proto)
        set_text(p, spec["narrative_indent"] + text)
        out.append(p)

    # Layout
    out.append(clone(spec["layout_heading"]))
    layout_box = max(_extents_cm(proto[spec["layout_image"]]) or [(width, 16)], key=lambda e: e[0] * e[1])
    # Layout otomatis (peta satelit + penanda titik) menggantikan foto layout & "Keterangan Warna" template.
    for image in [data.auto_layout] if data.auto_layout else []:
        p = clone(spec["layout_image"])
        _clear_runs(p)
        _add_picture(doc, p, image, min(layout_box[0], width), max(layout_box[1], 8))
        out.append(p)
    if data.points:
        head = clone(spec["layout_legend"][0] if spec["layout_legend"] else narr_proto)
        _clear_runs(head)  # buang kotak warna legenda lama yang menempel di paragraf ini
        set_text(head, "Keterangan:")
        rpr = OxmlElement("w:rPr")
        rpr.append(OxmlElement("w:b"))
        head.find(qn("w:r")).insert(0, rpr)
        out.append(head)
        for n, point in enumerate(data.points, 1):
            p = clone(narr_proto)
            note = (" — Existing" if point.status == "EXISTING" else " — Usulan baru") + (
                f"; {point.remarks[0]}" if point.remarks else "")
            set_text(p, f"{spec['narrative_indent']}{n}. {point.name}{note}")
            out.append(p)

    # Tabel hitungan FO (CCTV)
    if spec["fo_table"] is not None:
        out.append(clone(spec["fo_heading"]))
        fo = clone(spec["fo_table"])
        rows_out, totals = [], [Decimal(0)] * len(FO_NUMERIC)
        for n, point in enumerate(data.points, start=1):
            vals = []
            for k, col in enumerate(FO_NUMERIC):
                raw = point.cable.get(col)
                try:
                    num = Decimal(str(raw)) if raw not in (None, "") else Decimal(0)
                except ArithmeticError:
                    num = Decimal(0)
                totals[k] += num
                vals.append(_qty(num) if num else "-")
            rows_out.append([str(n), f"Cam{n}", *vals, point.cable.get("Uplink Switch", ""),
                             point.cable.get("Remark", "")])
        _fill_rows(fo, 1, 1, rows_out)
        total_cells = _cells(_rows(fo)[-1])
        for k, tot in enumerate(totals, start=1):
            if k < len(total_cells):
                _cell_set(total_cells[k], _qty(tot) if tot else "")
        out.append(fo)
        out.append(OxmlElement("w:p"))

    # Dokumentasi per titik (halaman baru; judul titik menempel ke tabel fotonya)
    out.append(_page_break())
    docs_heading = clone(spec["docs_heading"])
    replace_in(docs_heading, "Assessment", "Penilaian")
    out.append(docs_heading)
    photo_note = omitted_note(data.omitted_photos)
    if photo_note:
        out.append(_note_paragraph(photo_note))
    half = (width - 0.6) / 2
    for n, point in enumerate(data.points):
        if n:
            out.append(_page_break())
        heading = clone(spec["point_heading"])
        set_text(heading, point.name)
        _keep_with_next(heading)
        out.append(heading)
        photos = point.photos or []
        slots = [s for s in point.slots if any(ph.slot == s for ph in photos)] or [ph.slot for ph in photos[:1]]
        single = len(slots) == 1 and spec["photo_table_single"] is not None
        tbl = clone(spec["photo_table_single"] if single else spec["photo_table"])
        head, pics = _rows(tbl)[0], _rows(tbl)[1]
        columns = slots[:1] if single else (point.slots or slots)[:2]
        for tc, slot in zip(_cells(head), columns, strict=False):
            _cell_set(tc, slot)
        for tc, slot in zip(_cells(pics), columns, strict=False):
            box = (_cell_width_cm(tc) or (width - 0.6 if single else half)) - 0.7, 8.5
            ps = tc.findall(qn("w:p"))
            for extra in ps[1:]:
                tc.remove(extra)
            _clear_runs(ps[0])
            _cell_photo_spacing(ps[0])
            for ph in [ph for ph in photos if ph.slot == slot]:
                _add_picture(doc, ps[0], ph.image, box[0], box[1])
        out.append(tbl)
        remarks = point.remarks + [f"Kebutuhan: {need}" for need in point.needs]
        if remarks:
            out.append(clone(spec["remark_label"]))
            for text in remarks:
                p = clone(spec["remark_item"])
                set_text(p, text)
                out.append(p)
        if point.materials and spec["material_item"] is not None:
            out.append(clone(spec["material_label"]))
            for name, qty, unit in point.materials:
                p = clone(spec["material_item"])
                ts = _texts(p)
                ts[0].text = name
                set_after(p, "=", f"{_qty(qty)} {unit}")
                if len(name) >= 12:  # nama panjang melewati tab pertama → satu tab agar "=" tetap sejajar
                    tabs = [t for t in p.iter(qn("w:tab")) if t.getparent().tag == qn("w:r")]
                    if len(tabs) > 1:
                        tabs[-1].getparent().remove(tabs[-1])
                out.append(p)

    # Rincian volume dan biaya (estimasi)
    out.append(_page_break())
    bom_heading = clone(spec["bom_heading"])
    set_text(bom_heading, "Rincian Volume dan Biaya" + (" CCTV" if data.format == "CCTV" else ""))
    out.append(bom_heading)
    bom_tbl = clone(spec["bom_table"])
    # Lebih dari satu kelompok (jenis titik / Umum) → baris judul kelompok sebelum material-materialnya.
    grouped = len({g for *_x, g in data.bom}) > 1
    acs = data.format == "ACS"
    rows = []
    group = None
    for n, (name, qty, unit, g) in enumerate(data.bom, 1):
        if grouped and g != group:
            rows.append(["", g.upper(), "", "", ""] if acs else ["", g.upper(), ""])
            group = g
        rows.append([str(n), name, _qty(qty), unit, ""] if acs else [str(n), name, f"{_qty(qty)} {unit}"])
    _fill_rows(bom_tbl, 1, 0, rows)
    out.append(bom_tbl)
    out.append(OxmlElement("w:p"))

    # Penutup & tanda tangan
    for i in spec["closing"]:
        p = clone(i)
        replace_in(p, "report assessment", "laporan penilaian")
        replace_in(p, "report survey", "laporan survei")
        if i == spec["signature"]:
            set_after(p, "hormat", f", {data.leader_name}")
        elif i == spec["team_line"]:
            set_text(p, data.team_name)
        elif i == spec["names_line"]:
            set_text(p, " & ".join(data.member_names) or data.leader_name)
        out.append(p)

    for el in out:
        final_sect.addprevious(el)
    _prune_images(doc)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _prune_images(doc: DocumentObject) -> None:
    """Buang relasi gambar contoh yang tidak lagi dirujuk body (agar foto contoh tidak ikut terbawa)."""
    xml = doc.element.xml
    part = doc.part
    for rid, rel in list(part.rels.items()):
        if "image" in rel.reltype and f'"{rid}"' not in xml:
            del part.rels[rid]
