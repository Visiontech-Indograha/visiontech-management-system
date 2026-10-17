"""
app/crud/crud_plan_day.py
Baca hari kerja rencana mingguan beserta item tugas dan laporannya Master Schema V2.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDPlanDay(CRUDBase):
    """
    Kelas CRUD untuk pengambilan data terkait hari kerja SK beserta laporannya (Master Schema V2).
    """

    async def days_with_tasks_and_reports(self, plan_id: UUID | str) -> list[Any]:
        """Mendapatkan data hari kerja Work Plan mingguan beserta item tugas dan statusnya."""
        return list(
            await self.fetchall(
                """
            SELECT d.daily_plan_id AS id,
                   d.work_date,
                   'Rencana Hari ' || to_char(d.work_date, 'DD/MM/YYYY') AS title,
                   1 AS sort_order,
                   COALESCE((
                       SELECT jsonb_agg(jsonb_build_object(
                                  'id', wi.item_id,
                                  'title', wi.title,
                                  'sort_order', 1,
                                  'is_done', (wi.status = 'COMPLETED'),
                                  'done_at', wi.update_at,
                                  'work_type_name', wt.name)
                              ORDER BY wi.create_at)
                       FROM work_plan_item wi
                       LEFT JOIN work_type wt ON wt.work_type_id = wi.work_type_id
                       WHERE wi.daily_plan_id = d.daily_plan_id AND wi.delete_at IS NULL
                   ), '[]'::jsonb) AS tasks,
                   jsonb_build_object(
                       'status', d.status,
                       'body', COALESCE(wc.summary_notes, ''),
                       'obstacle', wc.obstacles,
                       'review_note', NULL,
                       'submitted_at', wc.leader_signed_at,
                       'reviewed_at', wc.pm_signed_at,
                       'resubmitted', FALSE,
                       'evidence_file_ids', COALESCE(wc.realization_photos_json, '[]'::jsonb),
                       'evidence', '[]'::jsonb
                   ) AS report,
                   0 AS member_reports_sent,
                   d.site_name,
                   (
                       SELECT wt.name FROM work_plan_item wi
                       JOIN work_type wt ON wt.work_type_id = wi.work_type_id
                       WHERE wi.daily_plan_id = d.daily_plan_id AND wi.delete_at IS NULL
                       LIMIT 1
                   ) AS work_type_name,
                   (
                       SELECT array_agg(m.employee_id)
                       FROM member m
                       WHERE m.team_id = wp.team_id AND m.is_active = TRUE AND m.delete_at IS NULL
                   ) AS member_employee_ids
            FROM work_plan_daily d
            JOIN work_plan_weekly wp ON wp.weekly_plan_id = d.weekly_plan_id
            LEFT JOIN work_completion wc ON wc.daily_plan_id = d.daily_plan_id AND wc.delete_at IS NULL
            WHERE d.weekly_plan_id = CAST(:plan AS uuid) AND d.delete_at IS NULL
            ORDER BY d.work_date
            """,
                {"plan": str(plan_id)},
            )
        )
