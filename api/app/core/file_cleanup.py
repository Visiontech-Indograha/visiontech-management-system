"""
app/core/file_cleanup.py
Pembersihan berkas MinIO yang tak lagi dipakai (UU PDP: berkas pribadi harus ikut terhapus).

Aturan:
- Satu unggahan gambar = kunci asli `{org}/{id}.{ext}` + varian `{org}/{id}_{full|view|thumb}.webp`.
  Semua varian ikut dihapus, bukan hanya kunci yang tercatat di DB.
- Urutan aman: DB commit dulu, baru objek dihapus (`queue_after_commit`). Gagal hapus objek hanya dicatat
  (tanpa nilai sensitif) dan tidak membatalkan DB; hapus objek idempoten sehingga aman diulang
  (sisa yang tertinggal dibersihkan skrip operator `scripts/bersihkan_berkas_yatim.py`).
- Berkas yang masih dirujuk data lain (kolom kunci, FK ke `file_object`) tidak dihapus.
"""
from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.core.events import queue_after_commit

logger = logging.getLogger(__name__)

VARIANTS = ("full", "view", "thumb")
VARIANT_RE = re.compile(r"_(?:full|view|thumb)$")

# Kolom penyimpan kunci objek (= file_object.storage_key): tabel, kolom, syarat baris yang masih dianggap memakai.
KEY_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("employee", "photo_path", "TRUE"),
    ("employee", "profile_photo_path", "TRUE"),
    ("employee_file", "path_file", "delete_at IS NULL"),
    ("tool", "photo_path", "TRUE"),
    ("vehicle", "photo_path", "TRUE"),
    ("vehicle_file", "path_file", "TRUE"),
    ("vehicle_inspection", "path_file", "TRUE"),
    ("asset_assignment", "handover_photo_path", "TRUE"),
    ("asset_assignment", "return_photo_path", "TRUE"),
    ("offboarding_clearance_item", "handover_photo_path", "TRUE"),
    ("attendance", "face_photo_path", "TRUE"),
    ("attendance", "out_of_radius_photo_path", "TRUE"),
    ("attendance_site_visit", "photo_path", "TRUE"),
    ("work_completion", "leader_signature_path", "TRUE"),
    ("work_completion", "pm_signature_path", "TRUE"),
    ("hse_campaigns", "media_path", "TRUE"),
)


def object_variants(key: str) -> list[str]:
    """Kunci asli + semua varian WebP-nya (`_full`, `_view`, `_thumb`)."""
    tail = key.rsplit("/", 1)[-1]
    base = key.rsplit(".", 1)[0] if "." in tail else key
    base = VARIANT_RE.sub("", base)
    return list(dict.fromkeys([key, *(f"{base}_{v}.webp" for v in VARIANTS)]))


def purge_keys(keys: Iterable[str]) -> tuple[int, int]:
    """Hapus semua varian tiap kunci. Mengembalikan (berhasil, gagal). Idempoten; tidak melempar galat."""
    done = failed = 0
    for key in dict.fromkeys(k for k in keys if k):
        for name in object_variants(key):
            if storage.delete_object(name):
                done += 1
            else:
                failed += 1
    if failed:
        logger.warning("Pembersihan berkas: %d objek gagal dihapus (ulangi lewat skrip operator)", failed)
    return done, failed


PURGE_CONCURRENCY = 4
_tasks: set[asyncio.Task[tuple[int, int]]] = set()  # rujukan kuat agar task tidak dibuang GC sebelum selesai


async def purge_keys_async(keys: list[str]) -> tuple[int, int]:
    """Hapus di luar event loop (thread), maksimal PURGE_CONCURRENCY panggilan MinIO sekaligus."""
    sem = asyncio.Semaphore(PURGE_CONCURRENCY)

    async def one(key: str) -> tuple[int, int]:
        async with sem:
            return await asyncio.to_thread(purge_keys, [key])

    results = await asyncio.gather(*(one(k) for k in dict.fromkeys(keys)))
    return sum(r[0] for r in results), sum(r[1] for r in results)


def _purge_later(keys: list[str]) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:  # konteks sinkron (skrip): tidak ada event loop untuk diblokir
        purge_keys(keys)
        return
    task = loop.create_task(purge_keys_async(keys))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


def queue_purge(db: AsyncSession, keys: Iterable[str]) -> None:
    """Hapus objek HANYA setelah transaksi commit."""
    unique = list(dict.fromkeys(k for k in keys if k))
    if unique:
        queue_after_commit(db, lambda: _purge_later(unique))


async def is_referenced(db: AsyncSession, key: str) -> bool:
    for table, col, cond in KEY_COLUMNS:
        hit = await db.execute(
            text(f"SELECT 1 FROM {table} WHERE {col} = :k AND {cond} LIMIT 1"), {"k": key}
        )
        if hit.first() is not None:
            return True
    return False


async def employee_keys(db: AsyncSession, employee_id: UUID | str) -> list[str]:
    """SEMUA kunci objek milik karyawan: foto, dokumen (KTP/SIM/...), swafoto/foto absensi, unggahan akunnya."""
    p = {"id": str(employee_id)}
    queries = (
        "SELECT photo_path FROM employee WHERE employee_id = CAST(:id AS uuid)",
        "SELECT profile_photo_path FROM employee WHERE employee_id = CAST(:id AS uuid)",
        "SELECT path_file FROM employee_file WHERE employee_id = CAST(:id AS uuid)",
        "SELECT face_photo_path FROM attendance WHERE employee_id = CAST(:id AS uuid)",
        "SELECT out_of_radius_photo_path FROM attendance WHERE employee_id = CAST(:id AS uuid)",
        "SELECT v.photo_path FROM attendance_site_visit v JOIN attendance a ON a.attendance_id = v.attendance_id "
        "WHERE a.employee_id = CAST(:id AS uuid)",
        "SELECT f.storage_key FROM file_object f JOIN users u ON u.user_id = f.uploaded_by "
        "WHERE u.employee_id = CAST(:id AS uuid)",
    )
    keys: list[str] = []
    for sql in queries:
        keys.extend(str(r[0]) for r in (await db.execute(text(sql), p)).all() if r[0])
    return list(dict.fromkeys(keys))


async def release_keys(db: AsyncSession, keys: Iterable[str]) -> int:
    """Lepas berkas yang tak dirujuk data mana pun: hapus baris `file_object` (dalam transaksi), lalu jadwalkan
    penghapusan objek + varian setelah commit. Mengembalikan jumlah kunci yang dilepas."""
    released: list[str] = []
    for key in dict.fromkeys(k for k in keys if k):
        if await is_referenced(db, key):
            continue
        try:
            async with db.begin_nested():
                await db.execute(text("DELETE FROM file_object WHERE storage_key = :k"), {"k": key})
        except IntegrityError:  # masih dipakai tabel lain lewat FK
            continue
        released.append(key)
    queue_purge(db, released)
    return len(released)
