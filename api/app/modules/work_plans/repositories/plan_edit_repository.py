"""
app/modules/work_plans/repositories/plan_edit_repository.py
Penyusunan draf rencana mingguan, hari dan item tugas Master Schema V2.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.repository import CRUDBase

_PLAN_COLUMNS = """wp.weekly_plan_id AS id, wp.division_id AS unit_id, NULL AS site_id,
                   'SK/W' || wp.week_number || '/' || wp.year AS number,
                   'Rencana Kerja W' || wp.week_number || ' ' || wp.year AS title,
                   'Kantor / Lapangan' AS location_text, '' AS description,
                   wp.start_date AS period_start, wp.end_date AS period_end,
                   wp.status, wp.approved_by_pm_id AS pm_employee_id,
                   t.leader_employee_id, 1 AS revision, 1 AS row_version, NULL AS cancellation_reason"""


class CRUDPlanEdit(CRUDBase):
    """Kueri Master Schema V2 untuk draf rencana kerja mingguan, hari kerja, dan item tugas."""

    async def insert_plan(
        self,
        org_id: UUID | str,
        *,
        unit_id: Any,
        site_id: Any,
        title: str,
        location_text: str | None,
        description: str | None,
        period_start: Any,
        period_end: Any,
        pm_employee_id: Any,
        leader_employee_id: Any,
    ) -> Any:
        """Draf rencana mingguan baru."""
        team_id = await self.scalar(
            "SELECT team_id FROM team WHERE division_id = CAST(:div AS uuid) AND delete_at IS NULL LIMIT 1",
            {"div": str(unit_id)},
        )
        if not team_id:
            office_id = await self.scalar("SELECT office_id FROM office WHERE delete_at IS NULL LIMIT 1")
            team_id = await self.scalar(
                """
                INSERT INTO team (office_id, division_id, leader_employee_id, name)
                VALUES (CAST(:off AS uuid), CAST(:div AS uuid), CAST(:ldr AS uuid), 'Tim Utama')
                RETURNING team_id
                """,
                {"off": str(office_id), "div": str(unit_id), "ldr": str(leader_employee_id)},
            )

        return await self.fetchone(
            """
            INSERT INTO work_plan_weekly (
                division_id, team_id, week_number, year, start_date, end_date,
                created_by_id, approved_by_pm_id, status
            )
            VALUES (
                CAST(:div AS uuid), CAST(:team AS uuid),
                EXTRACT(WEEK FROM CAST(:start AS date))::int,
                EXTRACT(YEAR FROM CAST(:start AS date))::int,
                CAST(:start AS date), CAST(:end AS date),
                COALESCE(CAST(:pm AS uuid), CAST(:ldr AS uuid)),
                CAST(:pm AS uuid), 'DRAFT'
            )
            RETURNING weekly_plan_id AS id,
                      'SK/W' || week_number || '/' || year AS number,
                      status, 1 AS revision, 1 AS row_version, NULL AS cancellation_reason
            """,
            {
                "div": str(unit_id),
                "team": str(team_id),
                "start": period_start,
                "end": period_end,
                "pm": str(pm_employee_id),
                "ldr": str(leader_employee_id),
            },
        )

    async def add_leader(self, plan_id: UUID | str, employee_id: Any, start: Any) -> None:
        """Tetapkan ketua tim."""
        await self.execute(
            """
            UPDATE team SET leader_employee_id = CAST(:emp AS uuid), update_at = NOW()
            WHERE team_id = (SELECT team_id FROM work_plan_weekly WHERE weekly_plan_id = CAST(:plan AS uuid))
            """,
            {"emp": str(employee_id), "plan": str(plan_id)},
        )

    async def remove_leader(self, plan_id: UUID | str) -> None:
        pass

    async def draft_state(self, plan_id: UUID | str, org_id: UUID | str) -> Any:
        """Status, versi, ketua, periode, divisi."""
        return await self.fetchone(
            """
            SELECT wp.status, 1 AS row_version, wp.approved_by_pm_id AS pm_employee_id,
                   t.leader_employee_id, wp.start_date AS period_start,
                   wp.end_date AS period_end, wp.division_id AS unit_id
            FROM work_plan_weekly wp
            JOIN team t ON t.team_id = wp.team_id
            WHERE wp.weekly_plan_id = CAST(:id AS uuid) AND wp.delete_at IS NULL
            """,
            {"id": str(plan_id)},
        )

    async def update_plan(
        self, plan_id: UUID | str, org_id: UUID | str, version: int, sets: list[str], params: dict[str, Any]
    ) -> Any:
        """Ubah draf."""
        return await self.fetchone(
            f"""
            UPDATE work_plan_weekly wp
            SET update_at = NOW()
            FROM team t
            WHERE wp.weekly_plan_id = CAST(:id AS uuid) AND t.team_id = wp.team_id
            RETURNING {_PLAN_COLUMNS}
            """,
            {"id": str(plan_id)},
        )

    async def plan_status(self, plan_id: UUID | str, org_id: UUID | str) -> Any:
        """Status rencana kerja organisasi ini, atau None."""
        row = await self.fetchone(
            "SELECT status FROM work_plan_weekly WHERE weekly_plan_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"id": str(plan_id)},
        )
        return row.status if row else None

    async def insert_day(self, plan_id: UUID | str, work_date: Any, title: str | None, sort_order: int) -> Any:
        """Hari baru pada rencana kerja."""
        row = await self.fetchone(
            """
            INSERT INTO work_plan_daily (
                weekly_plan_id, work_date, site_name, site_lat, site_lng,
                attendance_radius_m, clock_in_time, clock_out_time, status
            )
            VALUES (
                CAST(:plan AS uuid), CAST(:date AS date), COALESCE(:title, 'Lokasi Site'),
                -6.2088, 106.8456, 100, '07:00:00', '16:00:00', 'DRAFT'
            )
            RETURNING daily_plan_id AS id
            """,
            {"plan": str(plan_id), "date": work_date, "title": title},
        )
        return row.id

    async def insert_task(self, day_id: UUID | str, title: str, sort_order: int) -> Any:
        """Item tugas baru pada hari kerja."""
        wt_id = await self.scalar(
            """
            SELECT wt.work_type_id
            FROM work_type wt
            JOIN work_plan_weekly wpw ON wpw.division_id = wt.division_id
            WHERE wpw.weekly_plan_id = (
                SELECT weekly_plan_id FROM work_plan_daily WHERE daily_plan_id = CAST(:day AS uuid)
            )
              AND wt.delete_at IS NULL
            LIMIT 1
            """,
            {"day": str(day_id)},
        )
        if not wt_id:
            wt_id = await self.scalar("SELECT work_type_id FROM work_type WHERE delete_at IS NULL LIMIT 1")
        row = await self.fetchone(
            """
            INSERT INTO work_plan_item (
                daily_plan_id, weekly_plan_id, work_type_id, title,
                target_qty, completed_qty, progress_percent, status
            )
            SELECT
                d.daily_plan_id, d.weekly_plan_id, CAST(:wt AS uuid), :title,
                1.0, 0.0, 0.0, 'PENDING'
            FROM work_plan_daily d
            WHERE d.daily_plan_id = CAST(:day AS uuid)
            RETURNING item_id AS id
            """,
            {"day": str(day_id), "wt": str(wt_id), "title": title},
        )
        return row.id

    async def replace_day_plan(self, day_id: UUID | str, title: str, task_titles: list[str]) -> None:
        """Ganti judul hari & seluruh tugasnya."""
        await self.execute(
            """
            UPDATE work_plan_daily
            SET site_name = :title, update_at = NOW()
            WHERE daily_plan_id = CAST(:day AS uuid)
            """,
            {"title": title, "day": str(day_id)},
        )
        await self.execute(
            """
            UPDATE work_plan_item
            SET delete_at = NOW()
            WHERE daily_plan_id = CAST(:day AS uuid) AND delete_at IS NULL
            """,
            {"day": str(day_id)},
        )
        wt_id = await self.scalar("SELECT work_type_id FROM work_type WHERE delete_at IS NULL LIMIT 1")
        for t in task_titles:
            await self.execute(
                """
                INSERT INTO work_plan_item (
                    daily_plan_id, weekly_plan_id, work_type_id, title,
                    target_qty, completed_qty, progress_percent, status
                )
                SELECT
                    d.daily_plan_id, d.weekly_plan_id, CAST(:wt AS uuid), :title,
                    1.0, 0.0, 0.0, 'PENDING'
                FROM work_plan_daily d
                WHERE d.daily_plan_id = CAST(:day AS uuid)
                """,
                {"day": str(day_id), "wt": str(wt_id), "title": t},
            )

    async def reschedule_item(
        self,
        item_id: UUID | str,
        target_daily_plan_id: UUID | str,
        *,
        start_time: str | None = None,
        end_time: str | None = None,
        location_name: str | None = None,
        site_lat: float | None = None,
        site_lng: float | None = None,
        assigned_employee_ids: str | None = None,
    ) -> Any:
        """Pindahkan item penugasan ke hari/slot lain oleh PM (PM Full Override)."""
        return await self.fetchone(
            """
            UPDATE work_plan_item
            SET
                daily_plan_id = CAST(:target_day AS uuid),
                weekly_plan_id = (
                    SELECT weekly_plan_id FROM work_plan_daily
                    WHERE daily_plan_id = CAST(:target_day AS uuid)
                ),
                start_time = COALESCE(CAST(:start_time AS time), start_time),
                end_time = COALESCE(CAST(:end_time AS time), end_time),
                location_name = COALESCE(:location_name, location_name),
                site_lat = COALESCE(:site_lat, site_lat),
                site_lng = COALESCE(:site_lng, site_lng),
                assigned_employee_ids = COALESCE(CAST(:emp_ids AS jsonb), assigned_employee_ids),
                update_at = NOW()
            WHERE item_id = CAST(:item_id AS uuid) AND delete_at IS NULL
            RETURNING item_id, daily_plan_id, weekly_plan_id, title, start_time, end_time, location_name, status
            """,
            {
                "item_id": str(item_id),
                "target_day": str(target_daily_plan_id),
                "start_time": start_time,
                "end_time": end_time,
                "location_name": location_name,
                "site_lat": site_lat,
                "site_lng": site_lng,
                "emp_ids": assigned_employee_ids,
            },
        )

