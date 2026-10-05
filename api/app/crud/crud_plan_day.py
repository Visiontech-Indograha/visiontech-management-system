"""
app/crud/crud_plan_day.py
Baca hari kerja SK beserta tugas & laporan hariannya (satu kueri, tanpa N+1).
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDPlanDay(CRUDBase):
    """
    Kelas CRUD untuk pengambilan data terkait hari kerja SK beserta laporannya secara hierarki.
    """

    async def days_with_tasks_and_reports(self, plan_id: UUID | str) -> list[Any]:
        """Mendapatkan data hari kerja Work Plan beserta tasks (tugas harian) dan report-nya.
        
        Args:
            plan_id (UUID | str): ID Work Plan.
            
        Returns:
            list[Any]: Daftar hari kerja beserta tasks (JSON array) dan report (JSON object).
        """
        # Melakukan kueri komprehensif dalam satu kali hit (tanpa N+1 query).
        # LEFT JOIN dilakukan ke vms.daily_report untuk memuat data laporannya.
        # Penggunaan JSONB_AGG untuk merangkum seluruh vms.work_plan_task milik setiap hari ke dalam bentuk array.
        # Fungsi JSONB_BUILD_OBJECT digunakan untuk menstruktur objek JSON kolom 'report' secara rapi.
        # Subkueri skalar count(*) digunakan untuk menghitung status pengiriman member_daily_report.
        return list(await self.fetchall(
            """
            SELECT d.id, d.work_date, d.title, d.sort_order,
                   COALESCE((SELECT jsonb_agg(jsonb_build_object(
                                 'id', t.id, 'title', t.title, 'sort_order', t.sort_order,
                                 'is_done', t.is_done, 'done_at', t.done_at) ORDER BY t.sort_order, t.title)
                             FROM vms.work_plan_task t WHERE t.work_plan_day_id = d.id), '[]') AS tasks,
                   CASE WHEN r.id IS NULL THEN NULL ELSE jsonb_build_object(
                       'status', CAST(r.status AS text), 'body', r.body, 'obstacle', r.obstacle,
                       'review_note', r.review_note, 'submitted_at', r.submitted_at, 'reviewed_at', r.reviewed_at,
                       'resubmitted', r.resubmitted,
                       'evidence_file_ids', COALESCE((SELECT jsonb_agg(e.file_id)
                                                      FROM vms.report_evidence e WHERE e.daily_report_id = r.id),
                                                     '[]')) END AS report,
                   (SELECT count(*) FROM vms.member_daily_report m
                     WHERE m.work_plan_day_id = d.id AND m.status = 'SENT') AS member_reports_sent
            FROM vms.work_plan_day d
            LEFT JOIN vms.daily_report r ON r.work_plan_day_id = d.id
            WHERE d.work_plan_id = :plan
            ORDER BY d.work_date, d.sort_order
            """,
            {"plan": plan_id},
        ))
