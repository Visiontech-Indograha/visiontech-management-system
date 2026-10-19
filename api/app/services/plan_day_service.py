"""
app/services/plan_day_service.py
Baca hari kerja SK beserta tugas & laporan harian. Kewenangan (melihat SK) dijaga penjaga V-07 di router.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.crud.crud_plan_day import CRUDPlanDay
from app.services.access_service import PlanAccess


class PlanDayService:
    """
    Layanan untuk mengelola hari kerja (plan day) dalam sebuah SK (Surat Keputusan).
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        Inisialisasi PlanDayService.

        Args:
            db (AsyncSession): Sesi database asinkron.
        """
        self.repo = CRUDPlanDay(db)

    async def list_days(self, access: PlanAccess) -> list[Any]:
        """
        Mengambil daftar hari kerja beserta tugas dan laporan harian untuk SK tertentu.

        Args:
            access (PlanAccess): Objek akses yang berisi informasi SK yang diizinkan untuk diakses pengguna.

        Returns:
            list[Any]: Daftar hari kerja beserta detail tugas dan laporannya.
        """
        # Mengambil data hari kerja dari layer CRUD berdasarkan ID SK yang ada pada objek akses.
        # Hak akses (Kewenangan melihat SK) sudah dijaga di level router.
        rows = await self.repo.days_with_tasks_and_reports(access.plan.id)
        if access.is_leader:
            return list(rows)
        # Laporan harian berstatus Draf hanya milik ketua: PM/anggota baru melihatnya setelah dikirim.
        days: list[Any] = []
        for row in rows:
            day = dict(row._mapping)
            report = day.get("report")
            if isinstance(report, str):
                report = json.loads(report)
            if isinstance(report, dict) and report.get("status") == "DRAFT":
                day["report"] = None
            days.append(day)
        return days

    async def get_daily_schedule_detail(self, daily_plan_id: UUID | str) -> dict[str, Any]:
        """
        Mengambil detail jadwal harian multi-slot lengkap beserta SOP dan order klien.

        Args:
            daily_plan_id (UUID | str): ID unik jadwal harian (work_plan_daily).

        Returns:
            dict[str, Any]: Payload terstruktur rencana kerja harian.
        """
        data = await self.repo.get_daily_schedule_detail(daily_plan_id)
        if not data:
            raise AppError("NOT_FOUND", "Data rencana kerja harian tidak ditemukan.", status=404)
        return data
