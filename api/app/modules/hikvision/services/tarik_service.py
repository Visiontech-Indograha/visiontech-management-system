"""Tarik riwayat event dari perangkat ke `hikvision_event` (dipakai CLI `hikvision-tarik`).

Berkelompok (satu INSERT per kelompok, bukan per baris), idempoten (kunci unik perangkat+nomor event), memori
terbatas (event dialirkan), dan dapat dilanjutkan. Kredensial perangkat hanya dari lingkungan, tidak pernah dicetak."""
from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.modules.hikvision.repositories.hikvision_repository import HikvisionRepository
from app.modules.hikvision.schemas.tarik import PullCursor

from .isapi_client import PullClient
from .penyimpanan import baris_event

UKURAN_KELOMPOK = 1000
HARI_JENDELA = 7


class TarikError(Exception):
    """Galat yang aman ditampilkan ke operator."""


@dataclass
class RingkasanTarik:
    perangkat: str
    dry_run: bool
    total_event: int = 0          # dry-run: total di perangkat; tarik: event diproses
    event_tertua: str | None = None
    jendela: int = 0
    permintaan: int = 0
    baru: int = 0
    duplikat: int = 0
    dilewati: int = 0
    dilanjutkan_dari: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def nama_variabel(serial: str, akhiran: str) -> str:
    return f"HIKVISION_{re.sub(r'[^A-Za-z0-9]', '_', serial).upper()}_{akhiran}"


def kredensial(serial: str, env: dict[str, str] | None = None) -> tuple[str, str]:
    sumber = os.environ if env is None else env
    user, pw = sumber.get(nama_variabel(serial, "USER")), sumber.get(nama_variabel(serial, "PASS"))
    if not user or not pw:
        raise TarikError(
            f"Kredensial perangkat belum diatur. Isi variabel lingkungan {nama_variabel(serial, 'USER')} "
            f"dan {nama_variabel(serial, 'PASS')}."
        )
    return user, pw


def _awal_jendela(mulai: datetime, titik: datetime) -> datetime:
    n = int((titik - mulai) / timedelta(days=HARI_JENDELA))
    return mulai + timedelta(days=HARI_JENDELA * n)


async def tarik_riwayat(
    engine: AsyncEngine, *, serial: str, mulai: datetime, akhir: datetime, dry_run: bool, jeda: float,
    lanjutkan: bool, env: dict[str, str] | None = None, transport: httpx.AsyncBaseTransport | None = None,
    base_url: str | None = None, sleep: Any = None,
) -> RingkasanTarik:
    async with AsyncSession(engine) as db:
        repo = HikvisionRepository(db)
        device = await repo.device_by_serial(serial)
        if device is None:
            raise TarikError("Perangkat dengan nomor seri itu tidak terdaftar.")
        kursor: PullCursor | None = None
        ringkas = RingkasanTarik(perangkat=serial, dry_run=dry_run)
        if lanjutkan and not dry_run:
            terakhir = await repo.latest_pull_time(device.device_id, mulai, akhir)
            if terakhir is not None:
                kursor = PullCursor(_awal_jendela(mulai, terakhir), 0)
                ringkas.dilanjutkan_dari = kursor.window_start.isoformat()
        user, pw = kredensial(serial, env)
        opsi: dict[str, Any] = {"device_serial": serial, "transport": transport, "delay_s": jeda,
                                "window_days": HARI_JENDELA}
        if sleep is not None:
            opsi["sleep"] = sleep
        klien = PullClient(base_url or f"http://{device.ip_address}:{device.http_port}", user, pw, **opsi)

        if dry_run:
            hasil = await klien.dry_run(mulai, akhir)
            ringkas.total_event = hasil.total_event
            ringkas.event_tertua = hasil.event_tertua.isoformat() if hasil.event_tertua else None
            ringkas.jendela, ringkas.permintaan = hasil.jendela_diperiksa, hasil.jumlah_permintaan
            return ringkas

        buf: list[dict[str, Any]] = []

        async def simpan() -> None:
            if not buf:
                return
            baru = await repo.insert_events(device.device_id, "PULL", buf)
            await db.commit()  # CLI = batas transaksi: satu kelompok = satu transaksi
            ringkas.baru += baru
            ringkas.duplikat += len(buf) - baru
            buf.clear()

        async for e in klien.tarik(mulai, akhir, lanjut=kursor):
            ringkas.total_event += 1
            buf.append(baris_event(e))
            if len(buf) >= UKURAN_KELOMPOK:
                await simpan()
        await simpan()
        ringkas.permintaan = klien.jumlah_permintaan
        ringkas.dilewati = sum(klien.dilewati.values())
        return ringkas
