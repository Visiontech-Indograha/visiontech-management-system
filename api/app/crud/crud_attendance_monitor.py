"""
app/crud/crud_attendance_monitor.py
Kueri agregat untuk pemantauan absensi (dok 17 §5.3). Selalu per organisasi, hanya angka.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from uuid import UUID

from .base import CRUDBase


class CRUDAttendanceMonitor(CRUDBase):
    """
    Kelas operasi CRUD untuk pemantauan absensi (dashboard/agregat data).
    """

    async def active_employee_count(self, org_id: UUID | str) -> int:
        """
        Menghitung jumlah total karyawan aktif dalam sebuah organisasi.
        
        Args:
            org_id (UUID | str): ID organisasi.
            
        Returns:
            int: Jumlah karyawan aktif.
        """
        # Menghitung baris karyawan yang status is_active-nya true dan belum dihapus
        return int(await self.scalar(
            """
            SELECT count(*) FROM vms.employee
            WHERE organization_id = :org AND is_active AND deleted_at IS NULL
            """,
            {"org": org_id},
        ) or 0)

    async def check_in_count(self, org_id: UUID | str, work_date: date) -> int:
        """
        Menghitung jumlah absensi (check-in) pada suatu tanggal kerja untuk sebuah organisasi.
        
        Args:
            org_id (UUID | str): ID organisasi.
            work_date (date): Tanggal kerja.
            
        Returns:
            int: Jumlah absen masuk.
        """
        # Menghitung total absensi berdasarkan tanggal kerja (work_date)
        return int(await self.scalar(
            "SELECT count(*) FROM vms.attendance WHERE organization_id = :org AND work_date = :d",
            {"org": org_id, "d": work_date},
        ) or 0)

    async def last_check_in_at(self, org_id: UUID | str) -> datetime | None:
        """
        Mendapatkan waktu check-in terakhir (paling baru) di seluruh organisasi.
        
        Args:
            org_id (UUID | str): ID organisasi.
            
        Returns:
            datetime | None: Waktu check-in terakhir, atau None jika belum ada absensi.
        """
        # Mengambil nilai maksimum dari kolom check_in_at
        value: datetime | None = await self.scalar(
            "SELECT max(check_in_at) FROM vms.attendance WHERE organization_id = :org",
            {"org": org_id},
        )
        return value

    async def needs_review_count(self, org_id: UUID | str, work_date: date) -> int:
        """
        Menghitung jumlah absensi yang berstatus 'NEEDS_REVIEW' (perlu ditinjau) 
        pada tanggal tertentu.
        
        Args:
            org_id (UUID | str): ID organisasi.
            work_date (date): Tanggal kerja.
            
        Returns:
            int: Jumlah absensi yang perlu ditinjau.
        """
        # Menghitung absensi dengan status spesifik 'NEEDS_REVIEW'
        return int(await self.scalar(
            """
            SELECT count(*) FROM vms.attendance
            WHERE organization_id = :org AND work_date = :d AND status = 'NEEDS_REVIEW'
            """,
            {"org": org_id, "d": work_date},
        ) or 0)

    async def needs_review_daily_average(self, org_id: UUID | str, before: date, days: int) -> float:
        """
        Menghitung rata-rata harian absensi berstatus 'NEEDS_REVIEW' selama periode hari tertentu
        sebelum tanggal yang ditentukan (hari tanpa data dianggap 0).
        
        Args:
            org_id (UUID | str): ID organisasi.
            before (date): Batas tanggal akhir (eksklusif).
            days (int): Jumlah hari ke belakang.
            
        Returns:
            float: Rata-rata harian.
        """
        start, end = before - timedelta(days=days), before - timedelta(days=1)
        # Menggunakan generate_series untuk memastikan setiap hari dalam rentang waktu terhitung
        # meskipun tidak ada data absensi pada hari tersebut (LEFT JOIN), sehingga rata-ratanya akurat.
        return float(await self.scalar(
            """
            SELECT COALESCE(avg(COALESCE(c.n, 0)), 0)
            FROM generate_series(CAST(:start AS date), CAST(:end AS date), interval '1 day') AS d(day)
            LEFT JOIN (
                SELECT work_date, count(*) AS n FROM vms.attendance
                WHERE organization_id = :org AND status = 'NEEDS_REVIEW'
                  AND work_date BETWEEN :start AND :end
                GROUP BY work_date
            ) c ON c.work_date = d.day::date
            """,
            {"org": org_id, "start": start, "end": end},
        ) or 0)
