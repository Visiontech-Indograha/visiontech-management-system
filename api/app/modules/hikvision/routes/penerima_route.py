"""Penerima push perangkat absensi Hikvision (PUBLIK, tanpa login). Dijaga: token rahasia di path (disimpan hash),
IP harus sama dengan alamat perangkat di tabel, rate limit selalu aktif, badan maksimum 2 MiB, dan semua penolakan
identitas dijawab 404 yang sama."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.core.errors import AppError
from app.core.rate_limit import GROUP_HIKVISION, client_ip, rate_limit
from app.modules.hikvision.dependencies import get_penerima_service
from app.modules.hikvision.schemas.penerima import PenerimaOut
from app.modules.hikvision.services import konstanta as k
from app.modules.hikvision.services.penerima_service import PenerimaService

router = APIRouter(
    prefix="/hikvision", tags=["Hikvision"], dependencies=[Depends(rate_limit(GROUP_HIKVISION, always=True))]
)


def _terlalu_besar() -> AppError:
    return AppError("PAYLOAD_TOO_LARGE", "Kiriman terlalu besar (maksimum 2 MiB).", status=413)


async def _baca_badan(request: Request) -> bytes:
    """Baca badan dengan batas keras; berhenti begitu melewati batas (tanpa memuat seluruhnya)."""
    deklarasi = request.headers.get("content-length", "")
    if deklarasi.isdigit() and int(deklarasi) > k.MAKS_BYTE_KIRIMAN:
        raise _terlalu_besar()
    potongan = bytearray()
    async for bagian in request.stream():
        potongan += bagian
        if len(potongan) > k.MAKS_BYTE_KIRIMAN:
            raise _terlalu_besar()
    return bytes(potongan)


@router.post("/events/{token}", response_model=PenerimaOut)
async def terima_event(
    token: str, request: Request, service: PenerimaService = Depends(get_penerima_service)
) -> PenerimaOut:
    """Terima satu kiriman event dari perangkat. 404 bila token/perangkat/IP tidak dikenal, 413 bila terlalu besar,
    422 bila rusak. Event bukan verifikasi lolos (mis. sinyal hidup) dijawab 200 `diabaikan`."""
    body = await _baca_badan(request)
    return await service.terima(token, client_ip(request), body, request.headers.get("content-type"))
