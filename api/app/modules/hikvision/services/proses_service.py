"""Pembentuk absen dari event Hikvision (hikvision_event -> attendance).

Aturan (keputusan pemilik): absen mesin sah dan boleh CAMPUR dengan HP/web; satu sesi per karyawan per hari
(tanggal WIB) lintas sumber. Tap pertama = masuk; tap berikutnya yang berjarak >= `jarak_min` dari masuk = pulang.
Sisi yang sudah diisi HP/web tidak ditimpa. Tap lewat batas jam tanpa sesi = kandidat lembur (TIDAK membuat absen,
tidak disetujui otomatis; event mentah tetap tersimpan untuk perhitungan lembur). Pulang dari mesin boleh diperbarui
tap yang lebih akhir (terakhir menang) hanya bila sesinya dibuat mesin. Perangkat SHADOW tidak membuat absen.
Foto perangkat tidak disimpan. Aturan terlambat/lembur/uang makan dihitung dari data absen seperti biasa."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, time, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import WIB, utcnow
from app.modules.hikvision.repositories.hikvision_proses_repository import HikvisionProsesRepository
from app.modules.hikvision.services import konstanta as hk

JARAK_MIN_BAWAAN = timedelta(minutes=30)
BATAS_JAM_BAWAAN = time(19, 0)
UKURAN_BATCH = 500
_VALID = ("AUTO_VALID", "APPROVED_BY_OM")

MASUK = "MASUK"
PULANG = "PULANG"
PULANG_DIPERBARUI = "PULANG_DIPERBARUI"
DUPLIKAT = "DUPLIKAT"
DIABAIKAN = "DIABAIKAN"
LEMBUR_KANDIDAT = "LEMBUR_KANDIDAT"
PERLU_TINJAU = "PERLU_TINJAU"


@dataclass
class RingkasProses:
    event_dibaca: int = 0
    dipetakan_ulang: int = 0
    disaring: int = 0
    masuk_dibuat: int = 0
    pulang_diisi: int = 0
    pulang_diperbarui: int = 0
    duplikat: int = 0
    diabaikan: int = 0
    lembur_kandidat: int = 0
    perlu_tinjau: int = 0
    tak_terpetakan: int = 0
    bayangan_tertunda: int = 0

    @property
    def absen_dihasilkan(self) -> int:
        return self.masuk_dibuat

    def as_dict(self) -> dict[str, int]:
        d = asdict(self)
        d["absen_dihasilkan"] = self.absen_dihasilkan
        return d


def putuskan(absen: Any, waktu: datetime, jarak_min: timedelta, batas_jam: time) -> str:
    """Keputusan murni dari keadaan sesi hari itu. `absen` = baris absen_hari (atau None)."""
    if absen is None:
        return LEMBUR_KANDIDAT if waktu.astimezone(WIB).time() >= batas_jam else MASUK
    if absen.clock_out_at is None:
        if absen.om_approval_status not in _VALID:
            return PERLU_TINJAU
        return PULANG if waktu - absen.clock_in_at >= jarak_min else DUPLIKAT
    if absen.source == "HIKVISION" and waktu > absen.clock_out_at and waktu - absen.clock_in_at >= jarak_min:
        return PULANG_DIPERBARUI
    return DIABAIKAN


async def proses_event(
    db: AsyncSession, *, dry_run: bool = False, sertakan_bayangan: bool = False,
    jarak_min: timedelta = JARAK_MIN_BAWAAN, batas_jam: time = BATAS_JAM_BAWAAN, ukuran_batch: int = UKURAN_BATCH,
    perangkat: list[str] | None = None,
) -> RingkasProses:
    """Proses semua event terpetakan yang belum diproses. Idempoten (diproses_at). CLI = batas transaksi:
    satu kelompok = satu commit; `dry_run` mengerjakan semuanya lalu membatalkan (rollback).
    `perangkat` (id) membatasi ke perangkat tertentu (None = semua)."""
    repo = HikvisionProsesRepository(db)
    r = RingkasProses()
    r.dipetakan_ulang = await repo.petakan_ulang(sertakan_bayangan, perangkat)
    while True:
        batch = await repo.event_tertunda(sertakan_bayangan, ukuran_batch, perangkat)
        if not batch:
            break
        for ev in batch:
            r.event_dibaca += 1
            if ev.major_event_type != hk.MAJOR_AKSES or ev.minor_event_type not in hk.MINOR_VERIFIKASI_LOLOS:
                r.disaring += 1
                continue
            waktu = ev.event_time
            tanggal = waktu.astimezone(WIB).date()
            await repo.lock_employee(ev.employee_id)
            absen = await repo.absen_hari(ev.employee_id, tanggal)
            aksi = putuskan(absen, waktu, jarak_min, batas_jam)
            if aksi == MASUK:
                if await repo.masuk_dari_mesin(ev.employee_id, ev.office_id, tanggal, waktu, ev.event_id):
                    r.masuk_dibuat += 1
                else:
                    r.diabaikan += 1  # kantor perangkat tidak ditemukan
            elif aksi in (PULANG, PULANG_DIPERBARUI):
                await repo.pulang_dari_mesin(absen.attendance_id, waktu, ev.event_id)
                if aksi == PULANG:
                    r.pulang_diisi += 1
                else:
                    r.pulang_diperbarui += 1
            elif aksi == DUPLIKAT:
                r.duplikat += 1
            elif aksi == LEMBUR_KANDIDAT:
                r.lembur_kandidat += 1
            elif aksi == PERLU_TINJAU:
                r.perlu_tinjau += 1
            else:
                r.diabaikan += 1
        await repo.tandai_diproses([e.event_id for e in batch], utcnow())
        if not dry_run:
            await db.commit()
    r.tak_terpetakan = await repo.hitung_tak_terpetakan(sertakan_bayangan, perangkat)
    r.bayangan_tertunda = 0 if sertakan_bayangan else await repo.hitung_bayangan_tertunda(perangkat)
    if dry_run:
        await db.rollback()
    else:
        await db.commit()
    return r
