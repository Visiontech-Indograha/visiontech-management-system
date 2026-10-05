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
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
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
                            allowed_modules=["detection", "recognition"], providers=["CPUExecutionProvider"])
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
