"""app/core/retention_job.py
Hapus terjadwal (UU PDP + retensi arsip). Dua tindakan terpisah:
  A. anonimisasi karyawan yang keluar > 30 hari (berkas pribadi, embedding wajah, telepon, alamat; baris karyawan
     dan absensi tetap);
  B. hapus permanen arsip per jenis setelah batas retensi (purge_row + pembersihan berkas MinIO).
Aman: hanya jenis `is_active`; advisory lock; batch kecil FOR UPDATE SKIP LOCKED; batas waktu total; pemutus
ambang; baris yang masih dirujuk ditahan (job lanjut); objek MinIO dihapus di luar event loop setelah commit.
Waktu `now` selalu diinjeksi. Log/audit tanpa data sensitif."""
from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core import retention_repo as repo
from app.core.config import settings
from app.core.errors import AppError
from app.core.file_cleanup import employee_keys, purge_keys_async, release_keys_now
from app.core.hard_delete import purge_row
from app.core.retention import PERSONAL_DATA_DAYS

logger = logging.getLogger(__name__)

LOCK_NAME = "vms:retensi"


@dataclass
class TypeResult:
    kandidat: int = 0
    aktif: bool = False
    status: str = "ok"  # ok | nonaktif | diblokir | batas_waktu | tanpa_kebijakan
    diproses: int = 0
    ditahan: int = 0
    gagal: int = 0
    berkas_dihapus: int = 0
    berkas_gagal: int = 0


@dataclass
class Summary:
    mode: str
    status: str = "ok"  # ok | sedang_berjalan
    jenis: dict[str, TypeResult] = field(default_factory=dict)

    @property
    def bermasalah(self) -> bool:
        return any(r.gagal or r.berkas_gagal or r.status in ("diblokir", "batas_waktu") for r in self.jenis.values())

    def as_dict(self) -> dict[str, Any]:
        return {"mode": self.mode, "status": self.status, "jenis": {k: asdict(v) for k, v in self.jenis.items()}}


async def _hold_lock(engine: AsyncEngine, name: str) -> Any:
    conn = await engine.connect()
    got = (await conn.execute(text("SELECT pg_try_advisory_lock(hashtext(:n))"), {"n": name})).scalar_one()
    await conn.commit()
    if not got:
        await conn.close()
        return None
    return conn


async def _release_lock(conn: Any, name: str) -> None:
    try:
        await conn.execute(text("SELECT pg_advisory_unlock(hashtext(:n))"), {"n": name})
        await conn.commit()
    finally:
        await conn.close()


async def jalankan(
    engine: AsyncEngine,
    *,
    terapkan: bool,
    now: datetime,
    paksa: bool = False,
    batch_size: int | None = None,
    max_seconds: float | None = None,
    max_per_type: int | None = None,
    pause: float = 0.2,
    lock_name: str = LOCK_NAME,
    clock: Callable[[], float] = time.monotonic,
) -> Summary:
    """`--cek` (terapkan=False) tidak menulis apa pun. `now` timezone-aware (diinjeksi)."""
    batch = batch_size or settings.RETENTION_BATCH_SIZE
    limit = max_per_type if max_per_type is not None else settings.RETENTION_MAX_PER_TYPE
    deadline = clock() + (max_seconds if max_seconds is not None else settings.RETENTION_MAX_SECONDS)
    summary = Summary(mode="terapkan" if terapkan else "cek")

    lock_conn = None
    if terapkan:
        lock_conn = await _hold_lock(engine, lock_name)
        if lock_conn is None:
            summary.status = "sedang_berjalan"
            return summary
    try:
        async with AsyncSession(engine) as db:
            policies = await repo.load_policies(db)
            await db.rollback()
        plan: list[tuple[str, repo.ArchiveSpec | None, datetime]] = []
        days, _ = policies.get(repo.PERSONAL, (PERSONAL_DATA_DAYS, False))
        plan.append((repo.PERSONAL, None, now - timedelta(days=days)))
        for sp in repo.SPECS:
            if sp.data_type in policies:
                plan.append((sp.data_type, sp, now - timedelta(days=policies[sp.data_type][0])))
            else:
                summary.jenis[sp.data_type] = TypeResult(status="tanpa_kebijakan")
        for dtype, spec, cutoff in plan:
            aktif = policies.get(dtype, (0, False))[1]
            res = TypeResult(aktif=aktif)
            summary.jenis[dtype] = res
            async with AsyncSession(engine) as db:
                res.kandidat = (await repo.count_personal(db, cutoff) if spec is None
                                else await repo.count_archive(db, spec, cutoff))
                await db.rollback()
            if not terapkan:
                continue
            if not aktif:
                res.status = "nonaktif"
                continue
            if res.kandidat > limit and not paksa:
                res.status = "diblokir"
                logger.error("Hapus terjadwal: jenis %s melewati ambang (%d > %d), dihentikan", dtype,
                             res.kandidat, limit)
                continue
            await _proses_jenis(engine, dtype, spec, cutoff, res, batch, deadline, pause, clock)
        if terapkan:
            await _catat_run(engine, summary)
    finally:
        if lock_conn is not None:
            await _release_lock(lock_conn, lock_name)
    return summary


async def _proses_jenis(engine: AsyncEngine, dtype: str, spec: repo.ArchiveSpec | None, cutoff: datetime,
                        res: TypeResult, batch: int, deadline: float, pause: float,
                        clock: Callable[[], float]) -> None:
    seen: list[str] = []
    while True:
        if clock() >= deadline:
            res.status = "batas_waktu"
            return
        async with AsyncSession(engine) as db:
            ids = (await repo.next_personal_ids(db, cutoff, seen, batch) if spec is None
                   else await repo.next_archive_ids(db, spec, cutoff, seen, batch))
            await db.rollback()
        if not ids:
            return
        for row_id in ids:
            seen.append(row_id)
            if clock() >= deadline:
                res.status = "batas_waktu"
                return
            await _satu_baris(engine, dtype, spec, cutoff, row_id, res)
        if pause:
            await asyncio.sleep(pause)


async def _satu_baris(engine: AsyncEngine, dtype: str, spec: repo.ArchiveSpec | None, cutoff: datetime,
                      row_id: str, res: TypeResult) -> None:
    released: list[str] = []
    try:
        async with AsyncSession(engine) as db, db.begin():
            if spec is None:
                if not await repo.lock_personal(db, cutoff, row_id):
                    return
                keys = await employee_keys(db, row_id)
                async with db.begin_nested():
                    await repo.anonymize_employee(db, row_id)
                    released = await release_keys_now(db, keys)
                await repo.write_audit(db, "RETENTION_ANONYMIZE", "employee", row_id,
                                       {"jenis": dtype, "berkas": len(released)})
            else:
                if not await repo.lock_archive_row(db, spec, cutoff, row_id):
                    return
                keys = await repo.archive_keys(db, spec, row_id)
                async with db.begin_nested():
                    if spec.data_type == "employee_row":
                        await db.execute(text("UPDATE employee SET face_embedding = NULL "
                                              "WHERE employee_id = CAST(:id AS uuid)"), {"id": row_id})
                        for uid in await repo.user_ids_of(db, row_id):
                            await purge_row(db, "users", "user_id", uid)  # type: ignore[arg-type]
                    await purge_row(db, spec.table, spec.pk, row_id)  # type: ignore[arg-type]
                    released = await release_keys_now(db, keys)
                await repo.write_audit(db, "RETENTION_PURGE", spec.table, row_id,
                                       {"jenis": dtype, "berkas": len(released)})
    except AppError as exc:  # masih dirujuk data lain: ditahan, job lanjut
        res.ditahan += 1
        logger.warning("Hapus terjadwal: baris jenis %s ditahan (%s)", dtype, exc.code)
        return
    except Exception:
        res.gagal += 1
        logger.exception("Hapus terjadwal: baris jenis %s gagal diproses", dtype)
        return
    res.diproses += 1
    if released:
        done, failed = await purge_keys_async(released)  # di luar event loop, setelah commit, idempoten
        res.berkas_dihapus += done
        res.berkas_gagal += failed


async def _catat_run(engine: AsyncEngine, summary: Summary) -> None:
    status = "sebagian" if summary.bermasalah else "berhasil"
    counts = {k: {"kandidat": v.kandidat, "diproses": v.diproses, "ditahan": v.ditahan, "gagal": v.gagal,
                  "status": v.status} for k, v in summary.jenis.items()}
    async with AsyncSession(engine) as db, db.begin():
        await repo.write_run_log(db, counts, status, None)
