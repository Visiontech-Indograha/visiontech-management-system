"""Layanan inferensi wajah VMS (docs/06 P8-1): gambar -> embedding 512-d.

Hanya inferensi: tanpa basis data, tanpa penyimpanan gambar, tanpa CORS web. Yang memutuskan cocok atau
tidak adalah API VMS (`verify_face_for_attendance` di PostgreSQL). Dipanggil API lewat jaringan internal
dengan header `X-Face-Token`; port tidak dipublikasikan.
"""
from __future__ import annotations

import asyncio
import hmac
import os
from contextlib import asynccontextmanager
from typing import Any

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from insightface.app import FaceAnalysis
from pydantic import BaseModel

MODEL_PACK = os.getenv("FACE_MODEL_PACK", "buffalo_s")   # paket InsightFace: detektor det_500m + pengenal w600k_mbf
MODEL_NAME = "w600k_mbf"                                 # model pengenal 512-d; HP memakai model yang SAMA
MAX_BYTES = 5 * 1024 * 1024
TOKEN = os.getenv("FACE_SERVICE_TOKEN", "")
_state: dict[str, Any] = {}
_gate = asyncio.Semaphore(int(os.getenv("FACE_MAX_CONCURRENCY", "2")))   # membatasi memori pada server kecil


@asynccontextmanager
async def lifespan(_: FastAPI):
    if not TOKEN:
        raise RuntimeError("FACE_SERVICE_TOKEN wajib diisi (rahasia bersama dengan API VMS).")
    analyzer = FaceAnalysis(name=MODEL_PACK, root=os.getenv("INSIGHTFACE_ROOT", "~/.insightface"),
                            allowed_modules=["detection", "recognition", "landmark_2d_106", "landmark_3d_68"], providers=["CPUExecutionProvider"])
    analyzer.prepare(ctx_id=-1, det_size=(640, 640))
    _state["analyzer"] = analyzer
    yield
    _state.clear()


app = FastAPI(title="VMS Face Service", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


class EmbedResponse(BaseModel):
    faces: int                          # jumlah wajah terdeteksi; embedding hanya ada bila tepat 1
    embedding: list[float] | None = None
    quality: float | None = None        # 0..1 = skor deteksi x ukuran wajah x ketajaman
    detection_score: float | None = None
    model_name: str = MODEL_NAME
    model_version: str = MODEL_PACK


def _check_token(supplied: str | None) -> None:
    if not supplied or not hmac.compare_digest(supplied.encode(), TOKEN.encode()):
        raise HTTPException(status_code=401, detail="Token layanan wajah tidak valid.")


def _quality(img: np.ndarray, face: Any) -> float:
    x1, y1, x2, y2 = (int(v) for v in face.bbox)
    side = max(0, min(x2 - x1, y2 - y1))
    size_q = min(1.0, side / 160)       # >= 160 px dianggap baik
    crop = img[max(0, y1):max(0, y2), max(0, x1):max(0, x2)]
    if crop.size == 0:
        return 0.0
    blur = float(cv2.Laplacian(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var())
    blur_q = min(1.0, blur / 80)        # varians Laplacian >= 80 dianggap tajam
    return round(min(float(face.det_score), 1.0) * size_q * blur_q, 3)


def _embed(data: bytes) -> EmbedResponse:
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Format gambar tidak valid.")
    faces = _state["analyzer"].get(img)
    if len(faces) != 1:
        return EmbedResponse(faces=len(faces))
    face = faces[0]
    return EmbedResponse(faces=1, embedding=[round(float(v), 6) for v in face.normed_embedding],
                         quality=_quality(img, face), detection_score=round(float(face.det_score), 3))


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok" if "analyzer" in _state else "loading", "model": MODEL_NAME, "pack": MODEL_PACK}


@app.post("/embed", response_model=EmbedResponse)
async def embed(file: UploadFile = File(...), x_face_token: str | None = Header(default=None)) -> EmbedResponse:
    _check_token(x_face_token)
    data = await file.read(MAX_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="Gambar kosong.")
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="Gambar melebihi 5 MB.")
    async with _gate:
        return await run_in_threadpool(_embed, data)


def _evaluate_challenge(face: Any, challenge: str) -> None:
    if not challenge:
        return
    lmks = getattr(face, "landmark_2d_106", None)
    pose = getattr(face, "pose", None)

    if challenge == "depan":
        if pose is None:
            raise ValueError("Gagal mendeteksi pose wajah.")
        pitch, yaw, _ = pose[0], pose[1], pose[2]
        if abs(yaw) > 15 or abs(pitch) > 15:
            raise ValueError("Tantangan Gagal: Harap menghadap lurus ke depan!")
    elif challenge == "buka_mulut":
        if lmks is None:
            raise ValueError("Gagal mendeteksi titik wajah (landmark).")
        inner_h = abs(lmks[60][1] - lmks[62][1])
        width = abs(lmks[52][0] - lmks[61][0])
        mouth_ratio = inner_h / width if width > 0 else 0
        if mouth_ratio < 0.35:
            raise ValueError("Tantangan Gagal: Mulut kurang terbuka!")
    elif challenge == "kedip":
        if lmks is None:
            raise ValueError("Gagal mendeteksi titik wajah (landmark).")
        ear_left = (abs(lmks[37][1] - lmks[41][1]) + abs(lmks[38][1] - lmks[40][1])) / (
            2 * abs(lmks[35][0] - lmks[39][0]) + 1e-6
        )
        ear_right = (abs(lmks[87][1] - lmks[95][1]) + abs(lmks[88][1] - lmks[94][1])) / (
            2 * abs(lmks[89][0] - lmks[93][0]) + 1e-6
        )
        if ear_left > 0.25 or ear_right > 0.25:
            raise ValueError("Tantangan Gagal: Mata belum berkedip / tertutup!")
    elif challenge == "kanan":
        if pose is None:
            raise ValueError("Gagal mendeteksi pose wajah.")
        yaw = pose[1]
        if yaw < 15:
            raise ValueError("Tantangan Gagal: Kurang menghadap ke kanan!")
    elif challenge == "kiri":
        if pose is None:
            raise ValueError("Gagal mendeteksi pose wajah.")
        yaw = pose[1]
        if yaw > -15:
            raise ValueError("Tantangan Gagal: Kurang menghadap ke kiri!")
    elif challenge == "atas":
        if pose is None:
            raise ValueError("Gagal mendeteksi pose wajah.")
        pitch = pose[0]
        if pitch > -10:
            raise ValueError("Tantangan Gagal: Kurang menghadap ke atas / menengadah!")
    else:
        raise ValueError(f"Tantangan '{challenge}' tidak dikenal.")


def _check_challenge(data: bytes, challenge: str) -> dict[str, Any]:
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Format gambar tidak valid.")
    faces = _state["analyzer"].get(img)
    if len(faces) == 0:
        return {"status": "menunggu", "detail": "Tidak ada wajah terdeteksi di kamera."}
    if len(faces) > 1:
        return {"status": "menunggu", "detail": "Terdeteksi lebih dari satu wajah! Pastikan hanya Anda di kamera."}

    face = faces[0]
    try:
        _evaluate_challenge(face, challenge)
        return {"status": "sukses", "detail": "Tantangan berhasil!", "quality": _quality(img, face)}
    except ValueError as ve:
        return {"status": "menunggu", "detail": str(ve)}


@app.post("/challenge-check")
async def challenge_check(
    file: UploadFile = File(...),
    challenge: str = Form(...),
    x_face_token: str | None = Header(default=None),
) -> dict[str, Any]:
    _check_token(x_face_token)
    data = await file.read(MAX_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="Gambar kosong.")
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="Gambar melebihi 5 MB.")
    async with _gate:
        return await run_in_threadpool(_check_challenge, data, challenge)
