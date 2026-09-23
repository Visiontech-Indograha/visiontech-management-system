"""
app/repositories/attendance_monitor_repo.py
Kueri agregat untuk pemantauan absensi (dok 17 §5.3). Selalu per organisasi, hanya angka.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from uuid import UUID

from .base_repo import BaseRepo


class AttendanceMonitorRepo(BaseRepo):

    async def active_employee_count(self, org_id: UUID | str) -> int:
        return int(await self.scalar(
            """
            SELECT count(*) FROM vms.employee
            WHERE organization_id = :org AND is_active AND deleted_at IS NULL
            """,
            {"org": org_id},
        ) or 0)

    async def check_in_count(self, org_id: UUID | str, work_date: date) -> int:
        return int(await self.scalar(
            "SELECT count(*) FROM vms.attendance WHERE organization_id = :org AND work_date = :d",
            {"org": org_id, "d": work_date},
        ) or 0)

    async def last_check_in_at(self, org_id: UUID | str) -> datetime | None:
        value: datetime | None = await self.scalar(
            "SELECT max(check_in_at) FROM vms.attendance WHERE organization_id = :org",
            {"org": org_id},
        )
        return value

    async def needs_review_count(self, org_id: UUID | str, work_date: date) -> int:
        return int(await self.scalar(
            """
            SELECT count(*) FROM vms.attendance
            WHERE organization_id = :org AND work_date = :d AND status = 'NEEDS_REVIEW'
            """,
            {"org": org_id, "d": work_date},
        ) or 0)

    async def needs_review_daily_average(self, org_id: UUID | str, before: date, days: int) -> float:
        """Rata-rata NEEDS_REVIEW per hari selama `days` hari sebelum `before` (hari tanpa data = 0)."""
        start, end = before - timedelta(days=days), before - timedelta(days=1)
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
