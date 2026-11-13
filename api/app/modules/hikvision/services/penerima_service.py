"""Penerima push perangkat Hikvision: token (hash, waktu-konstan), allowlist IP, simpan event idempoten.

Perangkat tak dikenal, token salah, atau IP tak diizinkan semuanya dijawab 404 yang sama (tanpa bocoran).
Mode SHADOW dan AKTIF sama-sama hanya menyimpan event mentah; absen resmi bukan tugas PR ini."""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import logging
import re

from app.core.errors import AppError
from app.modules.hikvision.repositories.hikvision_repository import HikvisionRepository
from app.modules.hikvision.schemas.event import ParseStatus
from app.modules.hikvision.schemas.penerima import PenerimaOut

from . import konstanta as k
from .event_parser import parse_push
from .penyimpanan import baris_event

log = logging.getLogger(__name__)
_TOKEN = re.compile(r"^[A-Za-z0-9_-]{16,128}$")


def _tak_dikenal() -> AppError:
    return AppError("NOT_FOUND", "Tidak ditemukan.", status=404)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _ip_sama(a: str, b: str) -> bool:
    try:
        return ipaddress.ip_address(a.strip()) == ipaddress.ip_address(b.strip())
    except ValueError:
        return False


class PenerimaService:
    def __init__(self, repo: HikvisionRepository) -> None:
        self.repo = repo

    async def terima(self, token: str, ip_klien: str, body: bytes, content_type: str | None) -> PenerimaOut:
        if len(body) > k.MAKS_BYTE_KIRIMAN:
            raise AppError("PAYLOAD_TOO_LARGE", "Kiriman terlalu besar (maksimum 2 MiB).", status=413)
        if not _TOKEN.match(token):
            raise _tak_dikenal()
        h = hash_token(token)
        device = await self.repo.device_by_token_hash(h)
        if device is None or not hmac.compare_digest(str(device.token_hash).strip(), h):
            raise _tak_dikenal()
        if not _ip_sama(ip_klien, str(device.ip_address)):
            log.warning("push hikvision dari IP tak diizinkan perangkat=%s", device.serial_no)
            raise _tak_dikenal()

        hasil = parse_push(body, content_type, device_serial=device.serial_no)
        if hasil.status is ParseStatus.DITOLAK:
            if hasil.kode == "TERLALU_BESAR":
                raise AppError("PAYLOAD_TOO_LARGE", hasil.pesan, status=413)
            raise AppError("INVALID_PAYLOAD", hasil.pesan, status=422)
        if hasil.status is ParseStatus.DIABAIKAN or hasil.event is None:
            return PenerimaOut(status="diabaikan", kode=hasil.kode)  # 200 cepat: perangkat tidak mengulang

        baru = await self.repo.insert_events(device.device_id, "PUSH", [baris_event(hasil.event)])
        return PenerimaOut(status="diterima" if baru else "duplikat", kode=hasil.kode)
