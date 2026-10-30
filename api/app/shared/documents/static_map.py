"""
app/shared/documents/static_map.py
Layout otomatis laporan survei: citra satelit (Esri World Imagery) dengan penanda bernomor per titik dan
kotak keterangan berbentuk balon (nama titik + satu foto), seperti layout manual di laporan ACS/CCTV.
Zoom dipilih setinggi mungkin (≤ MAX_ZOOM) yang masih memuat semua titik beserta keterangannya.
"""
from __future__ import annotations

import io
import logging
import math
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageStat

logger = logging.getLogger(__name__)

TILE_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
ATTRIBUTION = "Imagery © Esri, Maxar, Earthstar Geographics"
TILE = 256
MAX_ZOOM = 19
SIZE = (2000, 1100)  # px; ±16 × 8,8 cm pada 300 dpi — sama dengan kotak layout di template
_CACHE: OrderedDict[tuple[int, int, int], Image.Image] = OrderedDict()
_CACHE_MAX = 600

_FONTS = [
    "arialbd.ttf", "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


@dataclass
class MapPoint:
    label: str
    lat: float
    lng: float
    photo: bytes | None = None
    status: str = "PROPOSED"  # EXISTING / PROPOSED → warna penanda


# Warna sama dengan legenda template ACS: hijau = sudah terpasang, biru = usulan pemasangan baru.
STATUS_COLOR = {"EXISTING": "#16A34A", "PROPOSED": "#0284C7"}
STATUS_LABEL = {"EXISTING": "Existing (sudah terpasang)", "PROPOSED": "Usulan pemasangan baru"}


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for f in _FONTS:
        if f.endswith(".ttf") and ("/" not in f or Path(f).exists()):
            try:
                return ImageFont.truetype(f, size)
            except OSError:
                continue
    return ImageFont.load_default(size=size)


def _world(lat: float, lng: float, z: int) -> tuple[float, float]:
    n = TILE * 2 ** z
    s = math.sin(math.radians(max(min(lat, 85.0), -85.0)))
    return (lng + 180) / 360 * n, (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * n


def _tile(z: int, x: int, y: int, client: httpx.Client) -> Image.Image | None:
    key = (z, x, y)
    if key in _CACHE:
        _CACHE.move_to_end(key)
        return _CACHE[key]
    try:
        r = client.get(TILE_URL.format(z=z, x=x, y=y))
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content)).convert("RGB")
    except (httpx.HTTPError, OSError):
        return None
    _CACHE[key] = img
    if len(_CACHE) > _CACHE_MAX:
        _CACHE.popitem(last=False)
    return img


TITLE_LINE = 38   # tinggi satu baris judul (font 30 px)
CARD_PAD = 14
PHOTO_H = 261
CAPTION_GAP = 4
CAPTION_LINE = 28  # keterangan "Belum ada foto" (font 20 px)
NO_PHOTO_CAPTION = "Belum ada foto"
CARD_FILL_PHOTO = "#FFFDF2"
CARD_FILL_NO_PHOTO = "#F3F4F6"  # netral: bukan biru (biru = warna penanda usulan)
MARKER_RADIUS = 20
MARKER_GAP = 2 * MARKER_RADIUS + 4  # jarak minimum antarpusat penanda agar tidak saling menutupi
SPREAD_RADIUS = 46  # jari-jari sebaran penanda pada lokasi yang sama


def _wrap_label(text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, width: float) -> list[str]:
    """Pecah label per kata agar tiap baris muat di `width`. Kata tunggal yang lebih lebar dipecah per karakter.
    Tidak pernah memotong dengan "…": nama lengkap tetap terbaca (kotak tumbuh ke bawah bila perlu)."""
    lines: list[str] = []
    current = ""
    for word in text.split():
        pieces = [word] if font.getlength(word) <= width else _break_word(word, font, width)
        for piece in pieces:
            candidate = f"{current} {piece}".strip()
            if current and font.getlength(candidate) > width:
                lines.append(current)
                current = piece
            else:
                current = candidate
    if current:
        lines.append(current)
    return lines or [""]


def _break_word(word: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, width: float) -> list[str]:
    parts: list[str] = []
    chunk = ""
    for ch in word:
        if chunk and font.getlength(chunk + ch) > width:
            parts.append(chunk)
            chunk = ch
        else:
            chunk += ch
    if chunk:
        parts.append(chunk)
    return parts


def _card_layout(p: MapPoint, number: int = 1) -> tuple[int, int, list[str]]:
    """Ukuran kotak keterangan dan baris judulnya ("<nomor>. <nama>" dibungkus). Lebar mengikuti teks terpanjang
    (maks 640 px), tinggi mengikuti jumlah baris judul dan foto (bila ada)."""
    font = _font(30)
    title = f"{number}. {p.label}"
    natural = math.ceil(font.getlength(title)) + 36  # dibulatkan ke atas agar baris pendek tidak pindah baris
    width = max(380 if p.photo else 240, min(640, natural))
    lines = _wrap_label(title, font, width - 32)
    height = CARD_PAD + len(lines) * TITLE_LINE + CARD_PAD
    if p.photo:
        height += 10 + PHOTO_H + CARD_PAD
    else:
        height += CAPTION_GAP + CAPTION_LINE
    return width, height, lines


def _card_fill(p: MapPoint) -> str:
    return CARD_FILL_PHOTO if p.photo else CARD_FILL_NO_PHOTO


def _spread_markers(anchors: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Posisi penanda di layar. Titik yang koordinatnya berdekatan (mis. beberapa titik di satu lokasi) disebar
    melingkar di sekitar pusat kelompoknya agar semua nomor terlihat; titik tunggal tetap di tempatnya."""
    groups: list[list[int]] = []
    for i, (x, y) in enumerate(anchors):
        for g in groups:
            if any(math.hypot(x - anchors[j][0], y - anchors[j][1]) < MARKER_GAP for j in g):
                g.append(i)
                break
        else:
            groups.append([i])
    out = list(anchors)
    for g in groups:
        if len(g) == 1:
            continue
        cx = sum(anchors[j][0] for j in g) / len(g)
        cy = sum(anchors[j][1] for j in g) / len(g)
        for k, i in enumerate(g):
            ang = -math.pi / 2 + 2 * math.pi * k / len(g)
            out[i] = (cx + math.cos(ang) * SPREAD_RADIUS, cy + math.sin(ang) * SPREAD_RADIUS)
    return out


def _overlap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return max(w, 0) * max(h, 0)


def _place_cards(pts: list[tuple[float, float]], sizes: list[tuple[int, int]],
                 frame: tuple[int, int]) -> list[tuple[float, float, float, float]]:
    """Posisi kotak keterangan: kandidat di 8 arah sekitar penanda, dipilih yang tidak keluar bingkai dan
    paling sedikit menutupi kotak/penanda lain (rakus, urut titik)."""
    W, H = frame
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    placed: list[tuple[float, float, float, float]] = []
    for (x, y), (w, h) in zip(pts, sizes, strict=True):
        best, best_score = None, float("inf")
        away = math.atan2(y - cy, x - cx) if (x, y) != (cx, cy) else -math.pi / 2
        for j in (0, 1, -1, 2, -2, 3, -3, 4):
            ang = away + j * math.pi / 4
            for dist in (110, 170, 240):
                bx = x + math.cos(ang) * (dist + w / 2) - w / 2
                by = y + math.sin(ang) * (dist + h / 2) - h / 2
                box = (bx, by, bx + w, by + h)
                out = max(0, 12 - bx) + max(0, 12 - by) + max(0, box[2] - W + 12) + max(0, box[3] - H + 40)
                score = out * 1e4 + sum(_overlap(box, o) for o in placed) * 10 + dist
                score += sum(_overlap(box, (px - 22, py - 22, px + 22, py + 22)) * 50 for px, py in pts)
                if score < best_score:
                    best, best_score = box, score
        assert best is not None
        bx = min(max(best[0], 12), W - w - 12)
        by = min(max(best[1], 12), H - h - 40)
        placed.append((bx, by, bx + w, by + h))
    return placed


def _zoom_for(points: list[MapPoint]) -> int:
    W, H = SIZE
    for z in range(MAX_ZOOM, 2, -1):
        xs, ys = zip(*(_world(p.lat, p.lng, z) for p in points), strict=True)
        if max(xs) - min(xs) <= W - 2 * 430 and max(ys) - min(ys) <= H - 2 * 380:
            return z
    return 3


def render_point_map(points: list[MapPoint]) -> bytes | None:
    """PNG layout titik; None bila tidak ada titik berkoordinat atau citra tidak dapat diunduh sama sekali."""
    points = [p for p in points if p.lat is not None and p.lng is not None]
    if not points:
        return None
    W, H = SIZE
    z = _zoom_for(points)
    # Zoom tertinggi yang benar-benar punya citra (Esri mengirim ubin abu "Map data not yet available").
    with httpx.Client(timeout=8, headers={"User-Agent": "VisiontechVMS/1.0 survey-layout"}) as probe:
        for _ in range(4):
            px, py = _world(points[0].lat, points[0].lng, z)
            sample = _tile(z, int(px // TILE), int(py // TILE), probe)
            if sample is None or ImageStat.Stat(sample.convert("L")).stddev[0] > 12 or z <= 15:
                break
            z -= 1
    world = [_world(p.lat, p.lng, z) for p in points]
    cx = (min(x for x, _ in world) + max(x for x, _ in world)) / 2
    cy = (min(y for _, y in world) + max(y for _, y in world)) / 2
    ox, oy = cx - W / 2, cy - H / 2
    canvas = Image.new("RGB", SIZE, "#6b7280")
    tiles = [(tx, ty) for tx in range(int(ox // TILE), int((ox + W) // TILE) + 1)
             for ty in range(int(oy // TILE), int((oy + H) // TILE) + 1)]
    with httpx.Client(timeout=8, headers={"User-Agent": "VisiontechVMS/1.0 survey-layout"}) as client, \
            ThreadPoolExecutor(max_workers=8) as pool:
        got = list(pool.map(lambda t: _tile(z, t[0], t[1], client), tiles))
    if not any(got):
        logger.warning("Citra satelit tidak dapat diunduh untuk layout survei")
        return None
    for (tx, ty), img in zip(tiles, got, strict=True):
        if img is not None:
            canvas.paste(img, (int(tx * TILE - ox), int(ty * TILE - oy)))

    anchors = [(x - ox, y - oy) for x, y in world]
    pts = _spread_markers(anchors)
    layouts = [_card_layout(p, i + 1) for i, p in enumerate(points)]
    cards = _place_cards(pts, [(w, h) for w, h, _ in layouts], SIZE)
    draw = ImageDraw.Draw(canvas)
    title_font, num_font, small = _font(30), _font(24), _font(20)

    for (ax, ay), (mx, my) in zip(anchors, pts, strict=True):
        if (ax, ay) != (mx, my):  # koordinat asli titik yang penandanya digeser
            draw.ellipse((ax - 5, ay - 5, ax + 5, ay + 5), fill="#111827", outline="white", width=2)

    for p, (mx, my), box, (_, _, lines) in zip(points, pts, cards, layouts, strict=True):
        fill = _card_fill(p)
        bx = (box[0] + box[2]) / 2
        by = (box[1] + box[3]) / 2
        ang = math.atan2(my - by, mx - bx)
        nx, ny = -math.sin(ang) * 26, math.cos(ang) * 26
        draw.polygon([(mx, my), (bx + nx, by + ny), (bx - nx, by - ny)], fill=fill, outline="#374151")
        draw.rounded_rectangle(box, radius=10, fill=fill, outline="#374151", width=2)
        for k, line in enumerate(lines):
            draw.text((box[0] + 16, box[1] + CARD_PAD + k * TITLE_LINE), line, font=title_font, fill="#111827")
        if not p.photo:
            cap_y = box[1] + CARD_PAD + len(lines) * TITLE_LINE + CAPTION_GAP
            draw.text((box[0] + 16, cap_y), NO_PHOTO_CAPTION, font=small, fill="#4B5563")
        if p.photo:
            try:
                top = box[1] + CARD_PAD + len(lines) * TITLE_LINE + 10
                ph = ImageOps.fit(Image.open(io.BytesIO(p.photo)).convert("RGB"), (int(box[2] - box[0] - 32), PHOTO_H))
                canvas.paste(ph, (int(box[0] + 16), int(top)))
            except OSError:
                pass
    for i, (p, (mx, my)) in enumerate(zip(points, pts, strict=True)):
        color = STATUS_COLOR.get(p.status, STATUS_COLOR["PROPOSED"])
        draw.ellipse((mx - 20, my - 20, mx + 20, my + 20), fill=color, outline="white", width=4)
        draw.text((mx, my), str(i + 1), font=num_font, fill="white", anchor="mm")
    # Legenda warna (hanya status yang muncul di peta)
    used = [st for st in STATUS_COLOR if any(p.status == st for p in points)]
    lx, ly = 16, H - 16 - 40 * len(used)
    draw.rounded_rectangle((lx - 6, ly - 8, lx + 420, H - 10), radius=8, fill="#FFFFFFE6", outline="#374151")
    for k, st in enumerate(used):
        y = ly + k * 40
        draw.ellipse((lx + 4, y + 2, lx + 30, y + 28), fill=STATUS_COLOR[st], outline="white", width=3)
        draw.text((lx + 42, y + 3), STATUS_LABEL[st], font=small, fill="#111827")
    tw = draw.textlength(ATTRIBUTION, font=small)
    draw.rectangle((W - tw - 20, H - 32, W, H), fill="#00000099")
    draw.text((W - tw - 10, H - 28), ATTRIBUTION, font=small, fill="white")
    out = io.BytesIO()
    canvas.save(out, "PNG", optimize=True)
    return out.getvalue()

