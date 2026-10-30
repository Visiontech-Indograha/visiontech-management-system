"""B21: peta BAST — penanda berdekatan tidak saling menutupi, label pendek tidak pindah baris,
kartu tanpa foto memakai latar netral dengan keterangan 'Belum ada foto' (bukan placeholder biru)."""
import io
import math
import os

from PIL import Image

from app.shared.documents import static_map as sm

MARKER_DIAMETER = 40  # diameter lingkaran penanda (px) pada SIZE 2000×1100


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def test_short_label_stays_on_one_line():
    """'2. UJI3 Titik CCTV B' dulu pindah ke baris kedua karena pembulatan lebar kotak."""
    _, _, lines = sm._card_layout(sm.MapPoint("UJI3 Titik CCTV B", -0.42, 101.38, None, "PROPOSED"), 2)
    assert lines == ["2. UJI3 Titik CCTV B"]


def test_coincident_points_get_separate_markers():
    """Tiga titik di koordinat yang sama dulu menumpuk: hanya penanda terakhir yang terlihat."""
    anchors = [(1000.0, 550.0)] * 3
    spread = sm._spread_markers(anchors)
    assert len(spread) == 3
    for i in range(3):
        for j in range(i + 1, 3):
            assert _dist(spread[i], spread[j]) >= MARKER_DIAMETER + 4
    assert all(_dist(s, anchors[0]) < 120 for s in spread)  # tetap berdekatan dengan lokasi asli


def test_isolated_points_keep_their_position():
    anchors = [(300.0, 300.0), (1500.0, 800.0)]
    assert sm._spread_markers(anchors) == anchors


def test_card_without_photo_is_neutral_with_caption():
    p = sm.MapPoint("Titik tanpa foto", -6.2, 106.8, None, "PROPOSED")
    assert sm._card_fill(p) == sm.CARD_FILL_NO_PHOTO
    assert sm._card_fill(p) != "#A5DDF7"  # bukan biru placeholder
    _, h, lines = sm._card_layout(p, 1)
    assert sm.NO_PHOTO_CAPTION == "Belum ada foto"
    assert h >= sm.CARD_PAD + len(lines) * sm.TITLE_LINE + sm.CAPTION_GAP + sm.CAPTION_LINE + sm.CARD_PAD


def test_card_with_photo_keeps_photo_fill():
    p = sm.MapPoint("Titik berfoto", -6.2, 106.8, b"x", "EXISTING")
    assert sm._card_fill(p) == sm.CARD_FILL_PHOTO


def test_map_with_coincident_points_renders_and_saves_sample(monkeypatch):
    solid = Image.new("RGB", (256, 256), (90, 120, 90))
    monkeypatch.setattr(sm, "_tile", lambda z, x, y, client: solid)
    points = [
        sm.MapPoint("UJI3 Titik CCTV A", 0.4212983, 101.3806115, None, "EXISTING"),
        sm.MapPoint("UJI3 Titik CCTV B", 0.4212983, 101.3806115, None, "PROPOSED"),
        sm.MapPoint("UJI3 Titik CCTV B", 0.4212983, 101.3806115, b"x", "EXISTING"),
        sm.MapPoint("Lokasi order", -7.0, 110.4, None, "PROPOSED"),
    ]
    png = sm.render_point_map(points)
    assert png is not None
    assert Image.open(io.BytesIO(png)).size == sm.SIZE
    out_dir = os.environ.get("PETA_SAMPEL_DIR")
    if out_dir:  # render sampel untuk ditinjau manual
        with open(os.path.join(out_dir, "peta-bast-b21.png"), "wb") as fh:
            fh.write(png)
