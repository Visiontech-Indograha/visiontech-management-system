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


def _card_size(p: MapPoint) -> tuple[int, int]:
    text = min(640, 60 + int(_font(30).getlength(p.label)))
    return (max(380, text), 60 + 285) if p.photo else (max(240, text), 70)


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

    pts = [(x - ox, y - oy) for x, y in world]
    sizes = [_card_size(p) for p in points]
    cards = _place_cards(pts, sizes, SIZE)
    draw = ImageDraw.Draw(canvas)
    title_font, num_font, small = _font(30), _font(24), _font(20)

    for i, (p, (mx, my), box) in enumerate(zip(points, pts, cards, strict=True)):
        fill = "#FFFDF2" if p.photo else "#A5DDF7"
        bx = (box[0] + box[2]) / 2
        by = (box[1] + box[3]) / 2
        ang = math.atan2(my - by, mx - bx)
        nx, ny = -math.sin(ang) * 26, math.cos(ang) * 26
        draw.polygon([(mx, my), (bx + nx, by + ny), (bx - nx, by - ny)], fill=fill, outline="#374151")
        draw.rounded_rectangle(box, radius=10, fill=fill, outline="#374151", width=2)
        draw.text((box[0] + 16, box[1] + 14), _fit(draw, f"{i + 1}. {p.label}", title_font, box[2] - box[0] - 32),
                  font=title_font, fill="#111827")
        if p.photo:
            try:
                ph = ImageOps.fit(Image.open(io.BytesIO(p.photo)).convert("RGB"), (int(box[2] - box[0] - 32), 261))
                canvas.paste(ph, (int(box[0] + 16), int(box[1] + 64)))
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


def _fit(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, width: float) -> str:
    if draw.textlength(text, font=font) <= width:
        return text
    while text and draw.textlength(text + "…", font=font) > width:
        text = text[:-1]
    return text + "…"
