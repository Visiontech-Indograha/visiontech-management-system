"""
app/services/face_embed_client.py

Klien HTTP ke face-service (inferensi saja, jaringan internal). Tidak pernah mencatat embedding atau gambar.
Layanan mati/lambat → `FaceServiceUnavailable`; pemanggil memutuskan (absen tetap berjalan, hasil SKIPPED).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class FaceServiceUnavailable(Exception):
    """face-service tidak terjangkau, menolak token, atau gagal memproses."""


@dataclass(frozen=True)
class EmbedResult:
    faces: int                              # jumlah wajah terdeteksi; embedding hanya ada bila tepat 1
    embedding: list[float] | None
    quality: float | None
    detection_score: float | None
    model_name: str
    model_version: str


class FaceEmbedClient:
    """Memanggil `POST /embed` face-service."""

    def __init__(self, base_url: str | None = None, token: str | None = None, timeout_s: float | None = None) -> None:
        self.base_url = (base_url if base_url is not None else settings.FACE_SERVICE_URL).rstrip("/")
        self.token = token if token is not None else settings.FACE_SERVICE_TOKEN
        self.timeout_s = timeout_s if timeout_s is not None else settings.FACE_SERVICE_TIMEOUT_S

    async def embed(self, image: bytes, filename: str = "probe.jpg") -> EmbedResult:
        if not self.base_url or not self.token:
            raise FaceServiceUnavailable("face-service belum dikonfigurasi")
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                response = await client.post(f"{self.base_url}/embed", files={"file": (filename, image)},
                                             headers={"X-Face-Token": self.token})
        except httpx.HTTPError as exc:
            logger.warning("face-service tidak terjangkau: %s", type(exc).__name__)
            raise FaceServiceUnavailable(type(exc).__name__) from None
        if response.status_code in (401, 403, 502, 503, 504) or response.status_code >= 500:
            logger.warning("face-service menjawab %s", response.status_code)
            raise FaceServiceUnavailable(f"HTTP {response.status_code}")
        if response.status_code != 200:
            # 400/413: gambar tidak valid — kesalahan pemanggil, bukan layanan mati.
            raise ValueError(f"face-service menolak gambar (HTTP {response.status_code})")
        body = response.json()
        return EmbedResult(faces=int(body["faces"]), embedding=body.get("embedding"), quality=body.get("quality"),
                           detection_score=body.get("detection_score"), model_name=body["model_name"],
                           model_version=body["model_version"])
