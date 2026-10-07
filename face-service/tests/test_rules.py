"""Aturan tantangan liveness face-service (rules.py) — tanpa model, hanya angka pose/landmark tiruan."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

import rules


def lmks(mouth_open: float = 0.0, width: float = 100.0) -> list[list[float]]:
    """106 titik; hanya indeks yang dipakai `metrics`: mulut (52, 61 lebar; 60, 62 tinggi)."""
    pts = [[0.0, 0.0] for _ in range(106)]
    pts[52] = [0.0, 0.0]
    pts[61] = [width, 0.0]
    pts[60] = [0.0, 0.0]
    pts[62] = [0.0, mouth_open * width]
    return pts


def face(pitch=0.0, yaw=0.0, mouth_open=0.0, bbox=(100, 100, 300, 300), with_pose=True, with_lmk=True):
    return SimpleNamespace(
        bbox=bbox,
        pose=[pitch, yaw, 0.0] if with_pose else None,
        landmark_2d_106=lmks(mouth_open) if with_lmk else None,
    )


def m(**kw):
    return rules.metrics(face(**kw), (400, 400))


# ── metrics ───────────────────────────────────────────────────────────────────
def test_metrics_reports_size_position_pose_and_mouth():
    got = rules.metrics(face(pitch=3.14, yaw=-7.77, mouth_open=0.5, bbox=(100, 100, 300, 300)), (400, 400))
    assert got["face_w"] == 0.5 and got["off_x"] == 0.0 and got["off_y"] == 0.0
    assert got["pitch"] == 3.1 and got["yaw"] == -7.8
    assert got["mouth_ratio"] == 0.5


def test_metrics_off_center_signs():
    right_low = rules.metrics(face(bbox=(220, 220, 380, 380)), (400, 400))
    assert right_low["off_x"] > 0 and right_low["off_y"] > 0          # kanan dan bawah bingkai


def test_metrics_missing_pose_or_landmarks_are_omitted():
    got = rules.metrics(face(with_pose=False, with_lmk=False), (400, 400))
    assert "yaw" not in got and "mouth_ratio" not in got and "face_w" in got


# ── arah kiri/kanan/atas/bawah (sudut pandang pengguna) ────────────────────────
@pytest.mark.parametrize("challenge, passing, failing", [
    ("kiri", dict(yaw=20), dict(yaw=5)),
    ("kanan", dict(yaw=-20), dict(yaw=-5)),
    ("atas", dict(pitch=15), dict(pitch=2)),
    ("bawah", dict(pitch=-15), dict(pitch=-2)),
    ("buka_mulut", dict(mouth_open=0.6), dict(mouth_open=0.1)),
])
def test_each_challenge_passes_and_fails(challenge, passing, failing):
    rules.evaluate(m(**passing), challenge)                              # tidak melempar
    with pytest.raises(ValueError):
        rules.evaluate(m(**failing), challenge)


@pytest.mark.parametrize("challenge, wrong_way, text", [
    ("kiri", dict(yaw=-20), "Salah arah. Tengok ke KIRI"),
    ("kanan", dict(yaw=20), "Salah arah. Tengok ke KANAN"),
    ("atas", dict(pitch=-20), "Salah arah. Dongakkan"),
    ("bawah", dict(pitch=20), "Salah arah. Tundukkan"),
])
def test_wrong_direction_gets_a_distinct_message(challenge, wrong_way, text):
    with pytest.raises(ValueError, match=text):
        rules.evaluate(m(**wrong_way), challenge)


@pytest.mark.parametrize("challenge, nearly, text", [
    ("kiri", dict(yaw=6), "Tengok lagi ke KIRI sedikit"),
    ("kanan", dict(yaw=-6), "Tengok lagi ke KANAN sedikit"),
    ("atas", dict(pitch=2), "Dongakkan lagi"),
    ("bawah", dict(pitch=-2), "Tundukkan lagi"),
])
def test_right_direction_but_not_enough_asks_for_more(challenge, nearly, text):
    with pytest.raises(ValueError, match=text):
        rules.evaluate(m(**nearly), challenge)


# ── langkah meluruskan wajah (depan) ──────────────────────────────────────────
def test_depan_accepts_straight_face():
    rules.evaluate(m(yaw=3, pitch=-4), "depan")


@pytest.mark.parametrize("pose, text", [
    (dict(yaw=25), "terlalu menoleh ke kiri. Putar sedikit ke KANAN"),
    (dict(yaw=-25), "terlalu menoleh ke kanan. Putar sedikit ke KIRI"),
    (dict(pitch=25), "terlalu menengadah"),
    (dict(pitch=-25), "terlalu menunduk"),
])
def test_depan_tells_which_way_to_straighten(pose, text):
    with pytest.raises(ValueError, match=text):
        rules.evaluate(m(**pose), "depan")


# ── data tidak lengkap dan tantangan tak dikenal ──────────────────────────────
def test_missing_data_and_unknown_challenge():
    with pytest.raises(ValueError, match="pose"):
        rules.evaluate(rules.metrics(face(with_pose=False), (400, 400)), "kiri")
    with pytest.raises(ValueError, match="landmark"):
        rules.evaluate(rules.metrics(face(with_lmk=False), (400, 400)), "buka_mulut")
    with pytest.raises(ValueError, match="tidak dikenal"):
        rules.evaluate(m(), "terbang")
    rules.evaluate(m(), "")                                              # tantangan kosong = tidak ada syarat


def test_kedip_was_removed():
    with pytest.raises(ValueError, match="tidak dikenal"):
        rules.evaluate(m(), "kedip")


# ── judge: jarak dan posisi ───────────────────────────────────────────────────
def test_judge_distance_comes_first():
    far = rules.metrics(face(yaw=25, bbox=(150, 150, 200, 200)), (400, 400))        # lebar 0,125
    near = rules.metrics(face(yaw=25, bbox=(0, 0, 395, 395)), (400, 400))           # lebar ~0,99
    assert rules.judge(far, "kiri") == {"status": "menunggu", "detail": "Wajah terlalu jauh. Dekatkan HP ke wajah."}
    assert rules.judge(near, "kiri")["detail"].startswith("Wajah terlalu dekat")


def test_judge_success_and_off_center_hint():
    ok = rules.judge(m(yaw=25), "kiri")
    assert ok == {"status": "sukses", "detail": "Tantangan berhasil!"}
    off = rules.metrics(face(yaw=2, bbox=(230, 100, 390, 300)), (400, 400))         # wajah terlalu ke kanan
    wait = rules.judge(off, "kiri")
    assert wait["status"] == "menunggu" and wait["detail"].endswith("Posisikan wajah di tengah oval.")
