"""
app/modules/overtime/repositories/overtime_repository.py
Lembur Master Schema V2: overtime N─1 employee, N─1 work_plan_daily (daily-first), rekap bulanan per karyawan.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository

_COLUMNS = """
    o.overtime_id AS id, o.daily_plan_id, o.employee_id, e.full_name AS employee_name, o.work_date,
    o.hours::float AS hours, o.reason, o.status, o.reviewed_by_id AS reviewed_by, o.reviewed_at, o.review_note,
    o.create_at AS created_at
"""


class OvertimeRepository(BaseRepository):
    """Query pengajuan & rekap lembur."""

    async def duplicate(self, daily_plan_id: UUID | str, employee_id: str) -> bool:
        """Satu pengajuan yang belum ditolak per karyawan per jadwal."""
        return bool(await self.scalar(
            "SELECT EXISTS (SELECT 1 FROM overtime WHERE daily_plan_id = CAST(:p AS uuid) "
            "AND employee_id = CAST(:e AS uuid) AND status <> 'REJECTED' AND delete_at IS NULL)",
            {"p": str(daily_plan_id), "e": employee_id},
        ))

    async def insert(
        self, daily_plan_id: UUID | str, employee_id: str, work_date: date, hours: float, reason: str
    ) -> UUID:
        overtime_id: UUID = await self.scalar(
            """
            INSERT INTO overtime (daily_plan_id, employee_id, work_date, hours, reason, status)
            VALUES (CAST(:p AS uuid), CAST(:e AS uuid), :d, CAST(:h AS numeric), :r, 'PENDING_PM')
            RETURNING overtime_id
            """,
            {"p": str(daily_plan_id), "e": employee_id, "d": work_date, "h": hours, "r": reason},
        )
        return overtime_id

    async def get(self, overtime_id: UUID | str) -> Any:
        return await self.fetchone(
            f"SELECT {_COLUMNS} FROM overtime o JOIN employee e ON e.employee_id = o.employee_id "
            "WHERE o.overtime_id = CAST(:id AS uuid) AND o.delete_at IS NULL",
            {"id": str(overtime_id)},
        )

    async def review(self, overtime_id: UUID | str, reviewer: str, decision: str, note: str | None) -> bool:
        updated = await self.scalar(
            """
            UPDATE overtime SET status = :decision, reviewed_by_id = CAST(:emp AS uuid), reviewed_at = now(),
                                review_note = :note, update_at = now()
            WHERE overtime_id = CAST(:id AS uuid) AND status = 'PENDING_PM' AND delete_at IS NULL
            RETURNING overtime_id
            """,
            {"id": str(overtime_id), "decision": decision, "emp": reviewer, "note": note},
        )
        return updated is not None

    async def list_by_plan(self, daily_plan_id: UUID | str) -> Sequence[Any]:
        return await self.fetchall(
            f"SELECT {_COLUMNS} FROM overtime o JOIN employee e ON e.employee_id = o.employee_id "
            "WHERE o.daily_plan_id = CAST(:p AS uuid) AND o.delete_at IS NULL ORDER BY o.create_at DESC",
            {"p": str(daily_plan_id)},
        )

    async def list_by_employee(self, employee_id: UUID | str) -> Sequence[Any]:
        return await self.fetchall(
            f"SELECT {_COLUMNS} FROM overtime o JOIN employee e ON e.employee_id = o.employee_id "
            "WHERE o.employee_id = CAST(:emp AS uuid) AND o.delete_at IS NULL ORDER BY o.create_at DESC",
            {"emp": str(employee_id)},
        )

    async def list_all_active(self, managed_by: str | None = None) -> Sequence[Any]:
        sql = f"""
            SELECT {_COLUMNS} FROM overtime o
            JOIN employee e ON e.employee_id = o.employee_id
            LEFT JOIN work_plan_daily wpd ON wpd.daily_plan_id = o.daily_plan_id
            LEFT JOIN division d ON d.division_id = wpd.division_id
            WHERE o.delete_at IS NULL
              AND (CAST(:mgr AS uuid) IS NULL OR CAST(:mgr AS uuid) IN (d.pm_id, d.om_id))
            ORDER BY o.create_at DESC
        """
        return await self.fetchall(sql, {"mgr": managed_by})

    async def recap(self, month: date | None, managed_by: str | None) -> Sequence[Any]:
        """Rekap per karyawan per bulan; `managed_by` = hanya jadwal di divisi yang PM/OM-nya karyawan ini."""
        return await self.fetchall(
            """
            SELECT CAST(date_trunc('month', o.work_date) AS date) AS period_month, o.employee_id,
                   e.full_name AS employee_name,
                   count(*) FILTER (WHERE o.status = 'APPROVED') AS approved_entries,
                   count(*) FILTER (WHERE o.status = 'PENDING_PM') AS pending_entries,
                   COALESCE(sum(o.hours) FILTER (WHERE o.status = 'APPROVED'), 0)::float AS approved_hours
            FROM overtime o
            JOIN employee e ON e.employee_id = o.employee_id
            LEFT JOIN work_plan_daily wpd ON wpd.daily_plan_id = o.daily_plan_id
            LEFT JOIN division d ON d.division_id = wpd.division_id
            WHERE o.delete_at IS NULL
              AND (CAST(:month AS date) IS NULL
                   OR CAST(date_trunc('month', o.work_date) AS date) = CAST(:month AS date))
              AND (CAST(:mgr AS uuid) IS NULL OR CAST(:mgr AS uuid) IN (d.pm_id, d.om_id))
            GROUP BY period_month, o.employee_id, e.full_name
            ORDER BY period_month DESC, employee_name
            """,
            {"month": month, "mgr": managed_by},
        )
