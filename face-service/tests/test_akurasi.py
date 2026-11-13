"""Harness FAR/FRR dan normalisasi pencahayaan: murni Python, tanpa model, tanpa wajah asli."""
from __future__ import annotations

import akurasi
import lighting


def test_far_frr_dasar():
    gen, imp = [0.9, 0.8, 0.5], [0.1, 0.6, 0.85]
    assert akurasi.far_frr(gen, imp, 0.8) == (1 / 3, 1 / 3)
    assert akurasi.far_frr(gen, imp, 0.0) == (1.0, 0.0)
    assert akurasi.far_frr([], [], 0.5) == (0.0, 0.0)


def test_kurva_monoton_dan_eer():
    pts = akurasi.sweep([0.9, 0.7, 0.6], [0.2, 0.3, 0.65])
    fars = [p.far for p in pts]
    frrs = [p.frr for p in pts]
    assert fars == sorted(fars, reverse=True) and frrs == sorted(frrs)
    e = akurasi.eer(pts)
    assert abs(e.far - e.frr) <= 1 / 3


def test_ambang_untuk_far_target():
    pts = akurasi.sweep([0.9, 0.8, 0.7], [0.2, 0.3, 0.75])
    t = akurasi.threshold_for_far(pts, 0.0)
    assert t is not None and t.far == 0.0 and t.threshold > 0.75
    assert akurasi.threshold_for_far(pts, -1.0) is None


def test_sintetis_deterministik_dan_derau_menurunkan_genuine():
    a, b = akurasi.synthetic_scores(seed=3), akurasi.synthetic_scores(seed=3)
    assert a == b
    mean = {c: sum(s["genuine"]) / len(s["genuine"]) for c, s in a.items()}
    assert mean["frontal"] > mean["miring"] > 0 and mean["frontal"] > mean["redup"]
    impostor_mean = sum(a["frontal"]["impostor"]) / len(a["frontal"]["impostor"])
    assert impostor_mean < mean["frontal"] - 0.2


def test_laporan_memuat_semua_kondisi():
    out = akurasi.report(akurasi.synthetic_scores(identities=10), 0.8)
    for cond in ("frontal", "miring", "redup"):
        assert f"| {cond} |" in out


def _gelap():
    return [20 + (i % 40) for i in range(4000)]      # rata-rata ~40, rentang sempit


def test_normalisasi_mencerahkan_foto_redup():
    gelap = _gelap()
    rep = lighting.lighting_report(lighting.histogram(gelap))
    assert rep["dark"] and rep["low_contrast"]
    out = lighting.normalize_luma(gelap)
    assert sum(out) / len(out) > sum(gelap) / len(gelap) + 40
    rep2 = lighting.lighting_report(lighting.histogram(out))
    assert rep2["span"] > rep["span"]


def test_lut_monoton_dan_batas():
    lut = lighting.build_lut(lighting.histogram(_gelap()))
    assert len(lut) == 256 and lut == sorted(lut) and lut[0] >= 0 and lut[-1] <= 255


def test_foto_terang_tidak_digelapkan_dan_rata_tak_berubah():
    terang = [150 + (i % 100) for i in range(4000)]
    out = lighting.normalize_luma(terang)
    assert sum(out) / len(out) == sum(terang) / len(terang)
    assert lighting.normalize_luma([100] * 50) == [100] * 50
    assert lighting.normalize_luma([]) == []
