"""
app/crud/crud_attendance_monitor.py
Kueri agregat untuk pemantauan absensi Master Schema V2.
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
        """Menghitung jumlah total karyawan aktif."""
        return int(
            await self.scalar(
                """
                SELECT count(*) FROM employee
                WHERE delete_at IS NULL AND offboarding_status = 'active'
                """
            )
            or 0
        )

    async def check_in_count(self, org_id: UUID | str, work_date: date) -> int:
        """Menghitung jumlah absensi (check-in) pada suatu tanggal kerja."""
        return int(
            await self.scalar(
                "SELECT count(*) FROM attendance WHERE attendance_date = :d AND delete_at IS NULL",
                {"d": work_date},
            )
            or 0
        )

    async def last_check_in_at(self, org_id: UUID | str) -> datetime | None:
        """Mendapatkan waktu check-in terakhir (paling baru)."""
        value: datetime | None = await self.scalar("SELECT max(clock_in_at) FROM attendance WHERE delete_at IS NULL")
        return value

    async def needs_review_count(self, org_id: UUID | str, work_date: date) -> int:
        """Menghitung jumlah absensi yang berstatus 'PENDING_OM' (perlu ditinjau)."""
        return int(
            await self.scalar(
                """
                SELECT count(*) FROM attendance
                WHERE attendance_date = :d AND om_approval_status = 'PENDING_OM' AND delete_at IS NULL
                """,
                {"d": work_date},
            )
            or 0
        )

    async def needs_review_daily_average(self, org_id: UUID | str, before: date, days: int) -> float:
        """Menghitung rata-rata harian absensi berstatus 'PENDING_OM' selama periode hari tertentu."""
        start, end = before - timedelta(days=days), before - timedelta(days=1)
        return float(
            await self.scalar(
                """
                SELECT COALESCE(avg(COALESCE(c.n, 0)), 0)
                FROM generate_series(CAST(:start AS date), CAST(:end AS date), interval '1 day') AS d(day)
                LEFT JOIN (
                    SELECT attendance_date AS work_date, count(*) AS n FROM attendance
                    WHERE om_approval_status = 'PENDING_OM' AND delete_at IS NULL
                      AND attendance_date BETWEEN :start AND :end
                    GROUP BY attendance_date
                ) c ON c.work_date = d.day::date
                """,
                {"start": start, "end": end},
            )
            or 0
        )
