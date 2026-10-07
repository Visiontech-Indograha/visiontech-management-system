"""Aturan tantangan liveness face-service (murni, tanpa model/OpenCV) agar bisa diuji tanpa memuat InsightFace.

Arah memakai sudut pandang PENGGUNA (kiri = sisi kiri tubuhnya). Bingkai kamera depan dikirim TIDAK dicerminkan, sehingga
menoleh ke kiri = yaw positif dan menengadah = pitch positif pada keluaran InsightFace (hasil uji Realme 2026-10-06).
"""
from __future__ import annotations

import os
from typing import Any

# Ambang tantangan (dapat dikalibrasi per perangkat tanpa ubah kode).
# Tanda yaw/pitch disesuaikan dengan hasil uji nyata di Realme (2026-10-06): bingkai kamera depan TIDAK dicerminkan,
# sehingga menoleh ke kiri pengguna = yaw positif dan menengadah = pitch positif pada keluaran InsightFace.
YAW_MIN = float(os.getenv("FACE_YAW_MIN", "12"))          # derajat menoleh kiri/kanan
PITCH_UP = float(os.getenv("FACE_PITCH_UP", "8"))         # pitch >= nilai ini = menengadah; pitch <= -nilai = menunduk
FRONT_MAX = float(os.getenv("FACE_FRONT_MAX", "12"))      # |yaw| dan |pitch| maksimum agar dianggap menghadap lurus
WRONG_WAY = 5.0                                           # sudah menoleh sejauh ini ke arah SALAH -> beri tahu salah arah
FACE_MIN_W = float(os.getenv("FACE_MIN_WIDTH", "0.25"))   # lebar wajah / lebar bingkai; di bawahnya = terlalu jauh
FACE_MAX_W = float(os.getenv("FACE_MAX_WIDTH", "0.80"))   # di atasnya = terlalu dekat
MOUTH_MIN = float(os.getenv("FACE_MOUTH_MIN", "0.35"))    # tinggi bukaan mulut / lebar mulut


def metrics(face: Any, shape: tuple[int, ...] | None = None) -> dict[str, float]:
    """Ukuran mentah yang dipakai tantangan; juga dikirim ke HP pada mode pengembangan untuk kalibrasi."""
    m: dict[str, float] = {}
    if shape is not None:
        h, w = shape[0], shape[1]
        x1, y1, x2, y2 = (float(v) for v in face.bbox)
        m["face_w"] = round((x2 - x1) / w, 2)
        m["off_x"] = round(((x1 + x2) / 2 - w / 2) / w, 2)    # >0 = wajah di kanan bingkai
        m["off_y"] = round(((y1 + y2) / 2 - h / 2) / h, 2)    # >0 = wajah di bawah bingkai
    pose = getattr(face, "pose", None)
    if pose is not None:
        m["pitch"], m["yaw"] = round(float(pose[0]), 1), round(float(pose[1]), 1)
    lmks = getattr(face, "landmark_2d_106", None)
    if lmks is not None:
        width = abs(lmks[52][0] - lmks[61][0])
        m["mouth_ratio"] = round(float(abs(lmks[60][1] - lmks[62][1]) / width) if width > 0 else 0.0, 3)
    return m


def evaluate(m: dict[str, float], challenge: str) -> None:
    """Melempar ValueError berisi petunjuk untuk pengguna bila gerakan belum terpenuhi. Arah memakai sudut pandang
    PENGGUNA (kiri = sisi kiri tubuhnya). yaw > 0 = menoleh ke kiri; pitch > 0 = menengadah."""
    if not challenge:
        return
    if challenge in {"depan", "kanan", "kiri", "atas", "bawah"} and "yaw" not in m:
        raise ValueError("Gagal mendeteksi pose wajah.")
    if challenge == "buka_mulut" and "mouth_ratio" not in m:
        raise ValueError("Gagal mendeteksi titik wajah (landmark).")

    if challenge == "depan":
        yaw, pitch = m["yaw"], m["pitch"]
        if yaw > FRONT_MAX:
            raise ValueError("Kepala terlalu menoleh ke kiri. Putar sedikit ke KANAN untuk meluruskan.")
        if yaw < -FRONT_MAX:
            raise ValueError("Kepala terlalu menoleh ke kanan. Putar sedikit ke KIRI untuk meluruskan.")
        if pitch > FRONT_MAX:
            raise ValueError("Kepala terlalu menengadah. Turunkan sedikit untuk meluruskan.")
        if pitch < -FRONT_MAX:
            raise ValueError("Kepala terlalu menunduk. Angkat sedikit untuk meluruskan.")
    elif challenge == "buka_mulut":
        if m["mouth_ratio"] < MOUTH_MIN:
            raise ValueError("Buka mulut lebih lebar.")
    elif challenge == "kiri":
        if m["yaw"] < YAW_MIN:
            raise ValueError("Salah arah. Tengok ke KIRI Anda, bukan kanan." if m["yaw"] <= -WRONG_WAY
                             else "Tengok lagi ke KIRI sedikit.")
    elif challenge == "kanan":
        if m["yaw"] > -YAW_MIN:
            raise ValueError("Salah arah. Tengok ke KANAN Anda, bukan kiri." if m["yaw"] >= WRONG_WAY
                             else "Tengok lagi ke KANAN sedikit.")
    elif challenge == "atas":
        if m["pitch"] < PITCH_UP:
            raise ValueError("Salah arah. Dongakkan kepala ke ATAS, bukan menunduk." if m["pitch"] <= -WRONG_WAY
                             else "Dongakkan lagi kepala ke ATAS sedikit.")
    elif challenge == "bawah":
        if m["pitch"] > -PITCH_UP:
            raise ValueError("Salah arah. Tundukkan kepala ke BAWAH, bukan menengadah." if m["pitch"] >= WRONG_WAY
                             else "Tundukkan lagi kepala ke BAWAH sedikit.")
    else:
        raise ValueError(f"Tantangan '{challenge}' tidak dikenal.")


def judge(m: dict[str, float], challenge: str) -> dict[str, Any]:
    """Keputusan satu bingkai: jarak dulu (terlalu jauh/dekat), lalu gerakan. `status` sukses/menunggu + `detail`."""
    if m.get("face_w", FACE_MIN_W) < FACE_MIN_W:
        return {"status": "menunggu", "detail": "Wajah terlalu jauh. Dekatkan HP ke wajah."}
    if m.get("face_w", FACE_MIN_W) > FACE_MAX_W:
        return {"status": "menunggu", "detail": "Wajah terlalu dekat. Jauhkan HP sedikit."}
    try:
        evaluate(m, challenge)
    except ValueError as ve:
        detail = str(ve)
        if abs(m.get("off_x", 0.0)) > 0.2 or abs(m.get("off_y", 0.0)) > 0.25:
            detail += " Posisikan wajah di tengah oval."
        return {"status": "menunggu", "detail": detail}
    return {"status": "sukses", "detail": "Tantangan berhasil!"}

