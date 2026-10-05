"""
app/services/plan_day_service.py
Baca hari kerja SK beserta tugas & laporan harian. Kewenangan (melihat SK) dijaga penjaga V-07 di router.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

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
        return await self.repo.days_with_tasks_and_reports(access.plan.id)
