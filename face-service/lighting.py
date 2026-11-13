"""Normalisasi pencahayaan untuk swafoto redup/kontras rendah (rencana: docs/rencana/akurasi-wajah.md).

Murni Python (tanpa numpy/OpenCV) agar bisa diuji di CI. Layanan memakainya lewat tabel LUT 256 entri:
`lut = build_lut(histogram)` lalu `cv2.LUT(gambar, lut)` pada kanal luma. Belum dipasang di `/embed`:
dipasang hanya setelah harness (`akurasi.py`) membuktikan FAR/FRR tidak memburuk pada data nyata.
"""
from __future__ import annotations

import math
from collections.abc import Sequence

TARGET_MEAN = 118.0      # kecerahan rata-rata sasaran (0..255)
CLIP_PCT = 0.01          # buang 1% piksel terang/gelap ekstrem saat meregang kontras
GAMMA_MIN, GAMMA_MAX = 0.45, 1.0   # hanya mencerahkan; foto terang tidak digelapkan
DARK_MEAN = 70.0         # di bawah ini = "kurang terang"
LOW_CONTRAST_SPAN = 90   # rentang persentil 1..99 di bawah ini = kontras rendah


def histogram(pixels: Sequence[int]) -> list[int]:
    hist = [0] * 256
    for p in pixels:
        hist[min(255, max(0, int(p)))] += 1
    return hist


def mean_of(hist: Sequence[int]) -> float:
    total = sum(hist)
    return sum(i * c for i, c in enumerate(hist)) / total if total else 0.0


def percentile(hist: Sequence[int], pct: float) -> int:
    """Nilai piksel terkecil sehingga >= pct (0..1) piksel berada di bawah atau sama dengannya."""
    total = sum(hist)
    if total == 0:
        return 0
    goal, acc = pct * total, 0
    for i, c in enumerate(hist):
        acc += c
        if acc >= goal:
            return i
    return 255


def lighting_report(hist: Sequence[int]) -> dict[str, float | bool]:
    lo, hi = percentile(hist, 0.01), percentile(hist, 0.99)
    mean = mean_of(hist)
    return {"mean": round(mean, 1), "span": float(hi - lo), "dark": mean < DARK_MEAN,
            "low_contrast": (hi - lo) < LOW_CONTRAST_SPAN}


def _gamma_for(mean01: float, target01: float) -> float:
    return math.log(target01) / math.log(mean01) if 0 < mean01 < 1 else 1.0


def build_lut(hist: Sequence[int]) -> list[int]:
    """Peta 256 -> 256: regang kontras (persentil terpotong) lalu gamma ke kecerahan sasaran. Monoton naik."""
    lo, hi = percentile(hist, CLIP_PCT), percentile(hist, 1 - CLIP_PCT)
    if hi - lo < 8:                      # gambar nyaris rata: tidak ada yang bisa diregangkan
        return list(range(256))
    rep = lighting_report(hist)
    if not (rep["dark"] or rep["low_contrast"]):   # pencahayaan sudah cukup: jangan diubah
        return list(range(256))
    stretched = [min(1.0, max(0.0, (i - lo) / (hi - lo))) for i in range(256)]
    total = sum(hist)
    mean = sum(stretched[i] * c for i, c in enumerate(hist)) / total * 255 if total else TARGET_MEAN
    gamma = 1.0
    if 1 <= mean < TARGET_MEAN:          # gamma < 1 mencerahkan; dibatasi agar derau tidak meledak
        gamma = min(GAMMA_MAX, max(GAMMA_MIN, _gamma_for(mean / 255, TARGET_MEAN / 255)))
    return [round(255 * (v ** gamma)) for v in stretched]


def normalize_luma(pixels: Sequence[int]) -> list[int]:
    lut = build_lut(histogram(pixels))
    return [lut[min(255, max(0, int(p)))] for p in pixels]
