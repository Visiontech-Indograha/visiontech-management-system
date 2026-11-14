"""Impor ekspor iVMS-4200 ke `hikvision_event` (dipakai CLI `hikvision-impor-ekspor`).

Idempoten (kunci cadangan event_key = hash(perangkat, ID orang, waktu)), berkelompok 1000, memori terbatas.
`dry_run` mengerjakan semuanya dalam satu transaksi lalu membatalkannya (hitungan sama persis dengan impor nyata).
Foto tidak disimpan; isi baris tidak pernah dicetak."""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.time import WIB
from app.modules.hikvision.repositories.hikvision_repository import HikvisionRepository

from . import konstanta as hk
from .impor_ekspor import SUMBER_IMPOR, EventImpor, ImporError, baca_ekspor, kunci_impor

UKURAN_KELOMPOK = 1000
_UUID = re.compile(r"^[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$")


@dataclass
class RingkasanImpor:
    perangkat: str
    dry_run: bool
    baris_dibaca: int = 0         # baris data yang dikenali sebagai absen (valid, di dalam rentang)
    baris_tidak_valid: int = 0    # judul ulang, ringkasan, atau isi tak terbaca
    di_luar_rentang: int = 0
    event_baru: int = 0
    duplikat: int = 0
    event_tak_terpetakan: int = 0
    id_tak_terpetakan: int = 0
    tanggal_tertua: str | None = None
    tanggal_terbaru: str | None = None
    per_bulan: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def tanggal_cli(teks: str | None, nama: str) -> date | None:
    if not teks:
        return None
    try:
        return date.fromisoformat(teks)
    except ValueError:
        raise ImporError(f"Tanggal {nama} {teks!r} tidak valid; pakai format 2026-10-31.") from None


def _baris(device_id: Any, e: EventImpor) -> dict[str, Any]:
    w = e.waktu.isoformat()
    return {
        "serial_no_event": None,
        "event_key": kunci_impor(device_id, e.employee_no, e.waktu),
        "major": hk.MAJOR_AKSES,
        "minor": hk.MINOR_WAJAH,
        "event_time": w,
        "employee_no_string": e.employee_no,
        "card_no": e.card_no,
        "verify_mode": "impor",
        "payload": {"impor": SUMBER_IMPOR, "major": hk.MAJOR_AKSES, "minor": hk.MINOR_WAJAH, "event_time": w,
                    "employee_no_string": e.employee_no, "card_no": e.card_no, "status": e.status,
                    "ada_gambar": False},
    }


async def jalankan_impor(
    engine: AsyncEngine, *, berkas: Path, perangkat: str, dry_run: bool, dari: date | None = None,
    sampai: date | None = None,
) -> RingkasanImpor:
    if dari and sampai and dari > sampai:
        raise ImporError("Tanggal --dari harus sama atau sebelum --sampai.")
    async with AsyncSession(engine) as db:
        repo = HikvisionRepository(db)
        device = await (repo.device_by_id(perangkat) if _UUID.match(perangkat) else repo.device_by_serial(perangkat))
        if device is None:
            raise ImporError("Perangkat tidak terdaftar. Beri ID atau nomor seri perangkat yang sudah terdaftar.")
        ringkas = RingkasanImpor(perangkat=perangkat, dry_run=dry_run)
        bulan: Counter[str] = Counter()
        tak_terpetakan: set[str] = set()
        buf: list[dict[str, Any]] = []

        async def simpan() -> None:
            if not buf:
                return
            nomor = list({str(r["employee_no_string"]) for r in buf})
            terpetakan = await repo.employee_no_terpetakan(device.device_id, nomor)
            ringkas.event_tak_terpetakan += sum(1 for r in buf if r["employee_no_string"] not in terpetakan)
            tak_terpetakan.update(n for n in nomor if n not in terpetakan)
            baru = await repo.insert_events(device.device_id, "PULL", buf)
            if not dry_run:
                await db.commit()  # CLI = batas transaksi: satu kelompok = satu transaksi
            ringkas.event_baru += baru
            ringkas.duplikat += len(buf) - baru
            buf.clear()

        try:
            for e in baca_ekspor(berkas):
                if e is None:
                    ringkas.baris_tidak_valid += 1
                    continue
                hari = e.waktu.astimezone(WIB).date()
                if (dari and hari < dari) or (sampai and hari > sampai):
                    ringkas.di_luar_rentang += 1
                    continue
                ringkas.baris_dibaca += 1
                bulan[f"{hari:%Y-%m}"] += 1
                if ringkas.tanggal_tertua is None or hari.isoformat() < ringkas.tanggal_tertua:
                    ringkas.tanggal_tertua = hari.isoformat()
                if ringkas.tanggal_terbaru is None or hari.isoformat() > ringkas.tanggal_terbaru:
                    ringkas.tanggal_terbaru = hari.isoformat()
                buf.append(_baris(device.device_id, e))
                if len(buf) >= UKURAN_KELOMPOK:
                    await simpan()
            await simpan()
        except BaseException:
            await db.rollback()
            raise
        if dry_run:
            await db.rollback()
        ringkas.id_tak_terpetakan = len(tak_terpetakan)
        ringkas.per_bulan = dict(sorted(bulan.items()))
        return ringkas
