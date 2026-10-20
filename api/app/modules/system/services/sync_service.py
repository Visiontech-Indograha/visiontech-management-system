"""
app/modules/system/services/sync_service.py
Sinkronisasi luring (M12; dok 02 A-08, dok 04 §7). Tiap operasi dijalankan dalam SAVEPOINT memakai
logika yang sama dengan jalur daring, lalu ditandai APPLIED / REJECTED (alasan disimpan, tidak dibuang).
Hanya aksi lapangan yang boleh luring; absensi, penerbitan & persetujuan wajib daring (waktu & geofence server).
Daily-first (Milestone 5): laporan harian & insiden SK V1 dipensiunkan — yang tersisa lembur per jadwal harian.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import CurrentUser
from app.modules.overtime.services.overtime_service import OvertimeService
from app.modules.system.repositories.sync_repository import CRUDSync

OFFLINE_ALLOWED = ("OVERTIME_REPORT",)
NOT_OFFLINE = "Aksi ini tidak dapat dikirim saat luring."
INVALID = "Data operasi tidak valid."


def _message(exc: Exception) -> str:
    if isinstance(exc, AppError):
        return exc.message
    if isinstance(exc, HTTPException):
        detail = exc.detail
        return str(detail.get("message") if isinstance(detail, dict) else detail)
    return INVALID


class SyncService:
    """
    Layanan sinkronisasi untuk memproses antrean operasi yang dikirim oleh klien secara luring (offline).
    Menjamin operasi divalidasi dengan aturan yang sama seperti saat online dan hasil sinkronisasi dicatat.
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        Inisialisasi SyncService.

        Args:
            db (AsyncSession): Sesi database asinkron.
        """
        self.db = db
        self.repo = CRUDSync(db)

    async def _apply(self, user: CurrentUser, op_type: str, p: dict[str, Any]) -> None:
        """
        Menerapkan satu buah operasi (payload) ke dalam sistem dengan menggunakan fungsi yang sama
        seperti endpoint online.

        Args:
            user (CurrentUser): Pengguna yang mengirimkan operasi.
            op_type (str): Tipe operasi (mis. DAILY_REPORT_SAVE).
            p (dict[str, Any]): Payload / data dari operasi.
        """
        if op_type == "OVERTIME_REPORT":
            daily_plan_id = UUID(str(p["daily_plan_id"]))
            await OvertimeService(self.db).report(user, daily_plan_id, float(p["hours"]), str(p["reason"]))

    async def apply_operations(self, user: CurrentUser, device_id: str, operations: list[Any]) -> list[dict[str, Any]]:
        """
        Memproses sekumpulan operasi dari antrean sinkronisasi luring yang dikirim klien.

        Args:
            user (CurrentUser): Pengguna pengirim.
            device_id (str): ID perangkat yang digunakan klien.
            operations (list[Any]): Daftar operasi yang akan disinkronisasi.

        Returns:
            list[dict[str, Any]]: Hasil proses tiap operasi (client_op_id, status, dan pesan galat jika ada).
        """
        results = []
        for op in operations:
            # Mendaftarkan operasi ke tabel sinkronisasi agar tidak terjadi double-processing
            row = await self.repo.enqueue(
                user.organization_id,
                user.user_id,
                device_id,
                op.client_op_id,
                op.op_type,
                op.payload,
                op.client_created_at,
            )
            status, error = row.status, row.error_message
            # Jika operasi belum pernah diproses (PENDING), maka eksekusi sekarang
            if status == "PENDING":
                if op.op_type not in OFFLINE_ALLOWED:
                    status, error = "REJECTED", NOT_OFFLINE
                else:
                    try:
                        # Jalankan aplikasi operasi di dalam nested transaction (SAVEPOINT)
                        # agar jika satu operasi gagal, operasi lainnya tetap bisa dilanjutkan.
                        async with self.db.begin_nested():
                            await self._apply(user, op.op_type, op.payload)
                        status, error = "APPLIED", None
                    except (AppError, HTTPException, PydanticValidationError, KeyError, ValueError, TypeError) as exc:
                        # Menangkap segala error validasi atau logika bisnis untuk ditandai sebagai ditolak
                        status, error = "REJECTED", _message(exc)
                # Menandai hasil akhir pemrosesan operasi di database
                await self.repo.mark(row.id, status, error)
            results.append({"client_op_id": str(op.client_op_id), "status": status, "error_message": error})
        return results

    async def status(self, user: CurrentUser, since: datetime | None) -> list[Any]:
        """
        Mengambil status operasi-operasi sinkronisasi yang pernah dikirimkan oleh pengguna.

        Args:
            user (CurrentUser): Pengguna.
            since (datetime | None): Filter waktu (mengembalikan operasi sejak waktu ini).

        Returns:
            list[Any]: Daftar status operasi.
        """
        return await self.repo.status_since(user.user_id, since)
