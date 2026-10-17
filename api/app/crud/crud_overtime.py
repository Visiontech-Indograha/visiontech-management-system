"""
app/crud/crud_overtime.py
Kueri lembur Master Schema V2.
Mendukung pengajuan lembur per rencana kerja mingguan (work_plan_weekly)
serta rekapitulasi bulanan per karyawan.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDOvertime(CRUDBase):
    """
    Kelas CRUD untuk mengelola pencatatan dan peninjauan lembur karyawan (overtime).
    """

    async def employee_of(self, user_id: UUID | str) -> str | None:
        """UUID karyawan yang terhubung ke akun pengguna."""
        employee: str | None = await self.scalar(
            "SELECT CAST(employee_id AS text) FROM users WHERE user_id = CAST(:uid AS uuid) AND delete_at IS NULL",
            {"uid": str(user_id)},
        )
        return employee

    async def effective_document_id(self, plan_id: UUID | str) -> str | None:
        """Di Master Schema V2, ID dokumen mereferensikan weekly_plan_id secara langsung."""
        return str(plan_id)

    async def insert(
        self,
        org_id: str,
        plan_id: UUID | str,
        doc_id: str | None,
        employee_id: str,
        work_date: Any,
        hours: float,
        reason: str,
    ) -> Any:
        """Menyisipkan baris pengajuan lembur baru."""
        return await self.fetchone(
            """
            INSERT INTO overtime (
                weekly_plan_id, employee_id, work_date, hours, reason, status
            ) VALUES (
                CAST(:plan AS uuid), CAST(:emp AS uuid), CAST(:date AS date),
                CAST(:hours AS numeric), :reason, 'PENDING_PM'
            )
            RETURNING overtime_id AS id, weekly_plan_id AS work_plan_id, NULL::uuid AS plan_document_id,
                      employee_id, work_date, hours::float AS hours, reason, status,
                      reviewed_by_id AS reviewed_by, reviewed_at, review_note, create_at AS created_at
            """,
            {
                "plan": str(plan_id),
                "emp": str(employee_id),
                "date": work_date,
                "hours": hours,
                "reason": reason,
            },
        )

    async def get_for_review(self, overtime_id: UUID | str, org_id: str) -> Any:
        """Ambil data lembur untuk pemeriksaan kewenangan PM/OM."""
        return await self.fetchone(
            """
            SELECT o.overtime_id AS id,
                   o.weekly_plan_id AS work_plan_id,
                   o.employee_id,
                   o.work_date,
                   o.hours::float AS hours,
                   o.reason,
                   o.status,
                   o.reviewed_by_id AS reviewed_by,
                   o.reviewed_at,
                   o.review_note,
                   o.create_at AS created_at,
                   NULL::uuid AS plan_document_id,
                   wp.division_id AS unit_id
            FROM overtime o
            JOIN work_plan_weekly wp ON wp.weekly_plan_id = o.weekly_plan_id
            WHERE o.overtime_id = CAST(:ot AS uuid) AND o.delete_at IS NULL
            """,
            {"ot": str(overtime_id)},
        )

    async def review(
        self,
        overtime_id: UUID | str,
        reviewer_emp: str,
        decision: str,
        note: str | None,
    ) -> Any:
        """Setujui atau tolak pengajuan lembur yang berstatus PENDING_PM."""
        return await self.fetchone(
            """
            UPDATE overtime
               SET status         = :decision,
                   reviewed_by_id = CAST(:emp AS uuid),
                   reviewed_at    = NOW(),
                   review_note    = :note,
                   update_at      = NOW()
             WHERE overtime_id = CAST(:ot AS uuid)
               AND status = 'PENDING_PM'
               AND delete_at IS NULL
            RETURNING overtime_id AS id, weekly_plan_id AS work_plan_id, NULL::uuid AS plan_document_id,
                      employee_id, work_date, hours::float AS hours, reason, status,
                      reviewed_by_id AS reviewed_by, reviewed_at, review_note, create_at AS created_at
            """,
            {"ot": str(overtime_id), "decision": decision, "emp": str(reviewer_emp), "note": note},
        )

    async def list_by_plan(self, plan_id: UUID | str, org_id: str) -> Sequence[Any]:
        """Daftar riwayat lembur per rencana kerja mingguan."""
        return await self.fetchall(
            """
            SELECT o.overtime_id AS id,
                   o.weekly_plan_id AS work_plan_id,
                   NULL::uuid AS plan_document_id,
                   o.employee_id,
                   o.work_date,
                   o.hours::float AS hours,
                   o.reason,
                   o.status,
                   o.reviewed_by_id AS reviewed_by,
                   o.reviewed_at,
                   o.review_note,
                   o.create_at AS created_at
            FROM overtime o
            WHERE o.weekly_plan_id = CAST(:plan AS uuid)
              AND o.delete_at IS NULL
            ORDER BY o.create_at DESC
            """,
            {"plan": str(plan_id)},
        )

    async def recap(self, org_id: str, month: date | None, pm_user_id: str | None) -> Sequence[Any]:
        """Rekap lembur per karyawan per bulan."""
        return await self.fetchall(
            """
            SELECT CAST(date_trunc('month', o.work_date) AS date) AS period_month,
                   o.employee_id,
                   e.full_name AS employee_name,
                   count(*) FILTER (WHERE o.status = 'APPROVED') AS approved_entries,
                   count(*) FILTER (WHERE o.status = 'PENDING_PM') AS pending_entries,
                   COALESCE(sum(o.hours) FILTER (WHERE o.status = 'APPROVED'), 0)::float AS approved_hours
            FROM overtime o
            JOIN employee e ON e.employee_id = o.employee_id
            JOIN work_plan_weekly wp ON wp.weekly_plan_id = o.weekly_plan_id
            WHERE o.delete_at IS NULL
              AND (CAST(:month AS date) IS NULL
                   OR CAST(date_trunc('month', o.work_date) AS date) = CAST(:month AS date))
            GROUP BY period_month, o.employee_id, e.full_name
            ORDER BY period_month DESC, employee_name ASC
            """,
            {"month": month},
        )
