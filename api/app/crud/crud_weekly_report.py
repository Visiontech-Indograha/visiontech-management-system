"""
app/crud/crud_weekly_report.py
Laporan mingguan SK (V-25). Minggu dihitung dari hari kerja SK: potongan 7 hari urut tanggal,
hanya bila SK lebih dari 7 hari (alur SK v2: "lebih dari 1 minggu"). Baris `weekly_report` dibuat saat pertama disimpan.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base import CRUDBase

_WEEKS = """
    WITH d AS (
        SELECT wpd.work_date, dr.status AS report_status,
               (row_number() OVER (ORDER BY wpd.work_date) - 1) / 7 + 1 AS week,
               count(*) OVER () AS total
        FROM vms.work_plan_day wpd
        LEFT JOIN vms.daily_report dr ON dr.work_plan_day_id = wpd.id
        WHERE wpd.work_plan_id = :plan
    ), w AS (
        SELECT week, min(work_date) AS starts_on, max(work_date) AS ends_on,
               bool_and(report_status IS NOT DISTINCT FROM 'APPROVED') AS days_approved
        FROM d WHERE total > 7 GROUP BY week
    )
    SELECT w.week, 'Laporan Mingguan ' || w.week AS name, w.starts_on, w.ends_on, w.days_approved,
           COALESCE(CAST(wr.status AS text), 'DRAFT') AS status,
           COALESCE(wr.body, '') AS body, COALESCE(wr.obstacle, '') AS obstacle, wr.review_note,
           COALESCE(wr.resubmitted, false) AS resubmitted
    FROM w
    LEFT JOIN vms.weekly_report wr ON wr.work_plan_id = :plan AND wr.name = 'Laporan Mingguan ' || w.week
    WHERE CAST(:week AS integer) IS NULL OR w.week = CAST(:week AS integer)
    ORDER BY w.week
"""


class CRUDWeeklyReport(CRUDBase):

    async def list_weeks(self, plan_id: UUID | str) -> list[Any]:
        return list(await self.fetchall(_WEEKS, {"plan": plan_id, "week": None}))

    async def get_week(self, plan_id: UUID | str, week: int) -> Any:
        return await self.fetchone(_WEEKS, {"plan": plan_id, "week": week})

    async def save(self, plan_id: UUID | str, week: Any, body: str, obstacle: str) -> Any:
        """Simpan draft; baris yang sudah diserahkan tidak tersentuh (→ None)."""
        return await self.fetchone(
            """
            INSERT INTO vms.weekly_report (work_plan_id, name, covered_period, body, obstacle)
            VALUES (:plan, :name, daterange(CAST(:starts AS date), CAST(:ends AS date), '[]'), :body, :obstacle)
            ON CONFLICT (work_plan_id, name) DO UPDATE
               SET body = EXCLUDED.body, obstacle = EXCLUDED.obstacle, covered_period = EXCLUDED.covered_period
             WHERE vms.weekly_report.status IN ('DRAFT', 'CHANGES_REQUESTED')
            RETURNING id
            """,
            {"plan": plan_id, "name": week.name, "starts": week.starts_on, "ends": week.ends_on,
             "body": body, "obstacle": obstacle},
        )

    async def submit(self, plan_id: UUID | str, name: str, user_id: UUID | str) -> Any:
        return await self.fetchone(
            """
            UPDATE vms.weekly_report
               SET status = 'SUBMITTED', resubmitted = resubmitted OR status = 'CHANGES_REQUESTED',
                   submitted_by = (SELECT employee_id FROM vms.app_user WHERE id = :uid)
             WHERE work_plan_id = :plan AND name = :name AND status IN ('DRAFT', 'CHANGES_REQUESTED')
            RETURNING id
            """,
            {"plan": plan_id, "name": name, "uid": user_id},
        )

    async def review(self, plan_id: UUID | str, name: str, status: str, note: str | None,
                     user_id: UUID | str) -> Any:
        return await self.fetchone(
            """
            UPDATE vms.weekly_report
               SET status = CAST(:status AS vms.report_status), review_note = :note,
                   reviewed_by = (SELECT employee_id FROM vms.app_user WHERE id = :uid)
             WHERE work_plan_id = :plan AND name = :name AND status = 'SUBMITTED'
            RETURNING id
            """,
            {"plan": plan_id, "name": name, "status": status, "note": note, "uid": user_id},
        )
