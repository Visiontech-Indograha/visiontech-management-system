"""
app/crud/crud_plan_day.py
Baca hari kerja rencana mingguan beserta item tugas dan laporannya Master Schema V2.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.repository import CRUDBase


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

    async def get_daily_schedule_detail(self, daily_plan_id: UUID | str) -> dict[str, Any] | None:
        """Mengambil detail jadwal harian multi-slot lengkap beserta SOP dan order klien."""
        daily_row = await self.fetchone(
            """
            SELECT
                d.daily_plan_id,
                d.work_date,
                d.status,
                d.site_name,
                d.site_lat,
                d.site_lng,
                d.attendance_radius_m,
                d.clock_in_time,
                d.clock_out_time,
                w.weekly_plan_id,
                w.week_number,
                w.year,
                div.division_id,
                div.name AS division_name,
                t.team_id,
                t.name AS team_name
            FROM work_plan_daily d
            JOIN work_plan_weekly w ON w.weekly_plan_id = d.weekly_plan_id
            JOIN division div ON div.division_id = w.division_id
            JOIN team t ON t.team_id = w.team_id
            WHERE d.daily_plan_id = CAST(:did AS uuid) AND d.delete_at IS NULL
            """,
            {"did": str(daily_plan_id)},
        )
        if not daily_row:
            return None

        d = daily_row if isinstance(daily_row, dict) else daily_row._mapping

        items_rows = await self.fetchall(
            """
            SELECT
                wi.item_id,
                wi.start_time,
                wi.end_time,
                wi.title,
                wi.location_name,
                wi.site_lat,
                wi.site_lng,
                wi.target_qty,
                wi.completed_qty,
                wi.progress_percent,
                wi.status,
                wi.assigned_employee_ids,
                wt.work_type_id,
                wt.name AS work_type_name,
                wt.description AS work_type_description,
                wc.completion_id,
                wc.order_number,
                wc.client_name,
                wc.project_title,
                wc.total_target_unit,
                wc.unit_measure,
                wc.order_status,
                wc.priority_level
            FROM work_plan_item wi
            LEFT JOIN work_type wt ON wt.work_type_id = wi.work_type_id
            LEFT JOIN work_completion wc ON wc.completion_id = wi.completion_id
            WHERE wi.daily_plan_id = CAST(:did AS uuid) AND wi.delete_at IS NULL
            ORDER BY wi.start_time ASC, wi.create_at ASC
            """,
            {"did": str(daily_plan_id)},
        )

        slots = []
        for it_raw in items_rows:
            it = it_raw if isinstance(it_raw, dict) else it_raw._mapping
            sop_list = []
            if it.get("work_type_id"):
                sop_rows = await self.fetchall(
                    """
                    SELECT name AS title, description, path_image
                    FROM image_requirement
                    WHERE work_type_id = CAST(:wtid AS uuid) AND delete_at IS NULL
                    ORDER BY sort_order ASC
                    """,
                    {"wtid": str(it["work_type_id"])},
                )
                sop_list = [dict(s if isinstance(s, dict) else s._mapping) for s in sop_rows]

            slot = {
                "item_id": it["item_id"],
                "start_time": str(it["start_time"]) if it.get("start_time") else None,
                "end_time": str(it["end_time"]) if it.get("end_time") else None,
                "title": it["title"],
                "location_name": it["location_name"],
                "site_lat": float(it["site_lat"]) if it.get("site_lat") is not None else None,
                "site_lng": float(it["site_lng"]) if it.get("site_lng") is not None else None,
                "target_qty": float(it["target_qty"] or 0),
                "completed_qty": float(it["completed_qty"] or 0),
                "progress_percent": float(it["progress_percent"] or 0),
                "status": it["status"],
                "assigned_employee_ids": it["assigned_employee_ids"] or [],
                "work_type": {
                    "work_type_id": it["work_type_id"],
                    "name": it["work_type_name"],
                    "description": it["work_type_description"],
                    "sop_image_requirements": sop_list,
                }
                if it.get("work_type_id")
                else None,
                "work_completion_order": {
                    "completion_id": it["completion_id"],
                    "order_number": it["order_number"],
                    "client_name": it["client_name"],
                    "project_title": it["project_title"],
                    "total_target_unit": float(it["total_target_unit"])
                    if it.get("total_target_unit") is not None
                    else None,
                    "unit_measure": it["unit_measure"],
                    "order_status": it["order_status"],
                    "priority_level": it["priority_level"],
                }
                if it.get("completion_id")
                else None,
            }
            slots.append(slot)

        return {
            "daily_plan_id": d["daily_plan_id"],
            "work_date": d["work_date"],
            "status": d["status"],
            "can_pm_edit": True,
            "preview_pdf_url": f"/work-plans/daily/{daily_plan_id}/pdf",
            "weekly_context": {
                "weekly_plan_id": d["weekly_plan_id"],
                "week_number": d["week_number"],
                "year": d["year"],
                "division": {
                    "division_id": d["division_id"],
                    "name": d["division_name"],
                },
                "team": {
                    "team_id": d["team_id"],
                    "name": d["team_name"],
                },
            },
            "default_attendance_site": {
                "site_name": d["site_name"],
                "site_lat": float(d["site_lat"]) if d.get("site_lat") is not None else None,
                "site_lng": float(d["site_lng"]) if d.get("site_lng") is not None else None,
                "attendance_radius_m": d["attendance_radius_m"],
                "clock_in_time": str(d["clock_in_time"]) if d.get("clock_in_time") else None,
                "clock_out_time": str(d["clock_out_time"]) if d.get("clock_out_time") else None,
            },
            "items_schedule_slots": slots,
        }
