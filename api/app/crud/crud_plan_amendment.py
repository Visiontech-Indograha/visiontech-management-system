"""
app/crud/crud_plan_amendment.py
Adendum saat SK Berjalan Master Schema V2 (tabel work_plan_weekly, work_plan_daily, work_plan_item, employee, app_activity_logs).
"""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from app.core.repository import CRUDBase


class CRUDPlanAmendment(CRUDBase):
    """
    Kelas CRUD untuk mengelola usulan adendum/perubahan rencana kerja mingguan (Master Schema V2).
    """

    async def list_changes(self, plan_id: UUID | str) -> list[Any]:
        """Mengambil daftar riwayat perubahan/adendum pada rencana kerja."""
        return list(
            await self.fetchall(
                """
            SELECT l.log_id AS id,
                   'EXTENSION' AS change_type,
                   wp.rollover_approval AS status,
                   COALESCE(l.details->>'reason', wp.notes, 'Perubahan rencana kerja') AS reason,
                   NULL AS decision_reason,
                   l.create_at AS created_at,
                   e.full_name AS requested_by_name,
                   pm.full_name AS decided_by_name,
                   NULL AS document_id
            FROM app_activity_logs l
            JOIN work_plan_weekly wp ON wp.weekly_plan_id = l.target_id
            LEFT JOIN users u ON u.user_id = l.user_id
            LEFT JOIN employee e ON e.employee_id = u.employee_id
            LEFT JOIN employee pm ON pm.employee_id = wp.approved_by_pm_id
            WHERE l.target_table = 'work_plan_weekly' AND l.target_id = CAST(:plan AS uuid)
            ORDER BY l.create_at DESC
            """,
                {"plan": str(plan_id)},
            )
        )

    async def update_header(
        self,
        plan_id: UUID | str,
        *,
        title: str,
        description: str,
        category: str,
        site_id: str,
        location_text: str,
        period_start: date,
        period_end: date,
        is_out_of_town: bool = False,
        work_type_id: UUID | str | None = None,
    ) -> None:
        """Memperbarui informasi header/dasar dari rencana kerja mingguan."""
        await self.execute(
            """
            UPDATE work_plan_weekly
               SET notes = :desc, start_date = :start, end_date = :end, update_at = NOW()
             WHERE weekly_plan_id = CAST(:plan AS uuid)
            """,
            {"plan": str(plan_id), "desc": description, "start": period_start, "end": period_end},
        )

    async def days_with_report_state(self, plan_id: UUID | str) -> list[Any]:
        """Hari rencana kerja beserta status pelaksanaannya."""
        return list(
            await self.fetchall(
                """
            SELECT d.daily_plan_id AS id, d.work_date, d.status AS report_status,
                   FALSE AS has_member_reports
            FROM work_plan_daily d
            WHERE d.weekly_plan_id = CAST(:plan AS uuid) AND d.delete_at IS NULL
            ORDER BY d.work_date
            """,
                {"plan": str(plan_id)},
            )
        )

    async def delete_day(self, day_id: UUID | str) -> None:
        """Hapus hari kerja yang belum ada laporannya."""
        await self.execute(
            "UPDATE work_plan_item SET delete_at = NOW() WHERE daily_plan_id = CAST(:day AS uuid)",
            {"day": str(day_id)},
        )
        await self.execute(
            "UPDATE work_plan_daily SET delete_at = NOW() WHERE daily_plan_id = CAST(:day AS uuid)",
            {"day": str(day_id)},
        )

    async def insert_day(self, plan_id: UUID | str, work_date: date, title: str, sort_order: int) -> str:
        """Tambah hari kerja baru ke rencana kerja."""
        row = await self.fetchone(
            """
            INSERT INTO work_plan_daily (weekly_plan_id, work_date, notes)
            VALUES (CAST(:plan AS uuid), :date, :title)
            RETURNING daily_plan_id AS id
            """,
            {"plan": str(plan_id), "date": work_date, "title": title},
        )
        return str(row.id)
