"""F18: label penanda peta BAST/work completion tidak boleh terpotong (dulu '1. Lokasi or…')."""
import io
import os

from PIL import Image, ImageDraw

from app.shared.documents import static_map as sm

LONG = "Lokasi Pemasangan CCTV Gerbang Utama Area Parkir Timur Gedung Operasional Blok B Lantai Dua"


def _text_width(text: str, font) -> float:
    return ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(text, font=font)


def test_long_label_wraps_without_truncation():
    p = sm.MapPoint(LONG, -6.2, 106.8, None, "PROPOSED")
    w, h, lines = sm._card_layout(p)
    font = sm._font(30)
    assert "…" not in "".join(lines)
    assert " ".join(lines) == f"1. {p.label}"  # seluruh nama tetap ada, tanpa dipotong
    assert all(_text_width(line, font) <= w - 32 for line in lines)  # setiap baris muat di dalam kotak
    assert h >= 14 + len(lines) * sm.TITLE_LINE + 14


def test_long_label_with_photo_keeps_full_text_and_photo_below():
    p = sm.MapPoint(("Lokasi " + "panjang sekali " * 8).strip(), -6.2, 106.8, b"x", "EXISTING")
    _, h, lines = sm._card_layout(p)
    assert " ".join(lines) == f"1. {p.label}"
    assert h >= 14 + len(lines) * sm.TITLE_LINE + 10 + 261


def test_single_word_wider_than_card_is_broken_not_cut():
    word = "X" * 120
    _, _, lines = sm._card_layout(sm.MapPoint(word, -6.2, 106.8))
    assert "".join(lines).replace(" ", "") == "1." + word  # dipecah per karakter, bukan dipotong
    assert "…" not in "".join(lines)


def test_map_with_long_labels_renders_and_saves_sample(monkeypatch, tmp_path):
    solid = Image.new("RGB", (256, 256), (90, 120, 90))
    monkeypatch.setattr(sm, "_tile", lambda z, x, y, client: solid)
    points = [
        sm.MapPoint(LONG, -6.2, 106.8, None, "EXISTING"),
        sm.MapPoint("Lokasi Pemasangan Access Control Pintu Samping Gudang Material Lantai Satu", -6.21, 106.82,
                    None, "PROPOSED"),
        sm.MapPoint("Titik kamera PTZ", -6.205, 106.81, None, "PROPOSED"),
    ]
    png = sm.render_point_map(points)
    assert png is not None
    assert all("…" not in line for i, p in enumerate(points) for line in sm._card_layout(p, i + 1)[2])
    assert Image.open(io.BytesIO(png)).size == sm.SIZE
    out_dir = os.environ.get("PETA_SAMPEL_DIR")
    if out_dir:  # render sampel untuk ditinjau manual (scratchpad)
        with open(os.path.join(out_dir, "peta-label-panjang.png"), "wb") as fh:
            fh.write(png)
