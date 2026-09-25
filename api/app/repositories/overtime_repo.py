"""
app/repositories/overtime_repo.py
Kueri lembur (V-28) — domain.js REPORT_OVERTIME, REVIEW_OVERTIME, rekap v_overtime_recap.
SQL statis; tidak ada f-string; CAST(:x AS tipe) sesuai standar backend.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Any
from uuid import UUID

from .base_repo import BaseRepo


class OvertimeRepo(BaseRepo):

    async def employee_of(self, user_id: UUID | str) -> str | None:
        """UUID karyawan yang terhubung ke akun pengguna."""
        employee: str | None = await self.scalar(
            "SELECT CAST(employee_id AS text) FROM vms.app_user WHERE id = :uid",
            {"uid": user_id},
        )
        return employee

    async def effective_document_id(self, plan_id: UUID | str) -> str | None:
        """SK aktif yang berlaku saat ini (domain.js baris 612: filter status EFFECTIVE)."""
        doc_id: str | None = await self.scalar(
            """
            SELECT CAST(id AS text) FROM vms.plan_document
             WHERE work_plan_id = :plan AND CAST(status AS text) = 'EFFECTIVE'
             ORDER BY version DESC LIMIT 1
            """,
            {"plan": plan_id},
        )
        return doc_id

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
        """Sisipkan baris lembur baru; unique index mencegah duplikat non-REJECTED."""
        return await self.fetchone(
            """
            INSERT INTO vms.overtime_log (
                organization_id, work_plan_id, plan_document_id,
                employee_id, work_date, hours, reason
            ) VALUES (
                CAST(:org AS uuid), CAST(:plan AS uuid), CAST(:doc AS uuid),
                CAST(:emp AS uuid), CAST(:date AS date),
                CAST(:hours AS numeric), :reason
            ) RETURNING *
            """,
            {
                "org": org_id, "plan": plan_id, "doc": doc_id,
                "emp": employee_id, "date": work_date,
                "hours": hours, "reason": reason,
            },
        )

    async def get_for_review(self, overtime_id: UUID | str, org_id: str) -> Any:
        """Ambil baris lembur + unit SK untuk pemeriksaan kewenangan PM (domain.js baris 619–620)."""
        return await self.fetchone(
            """
            SELECT o.id, o.work_plan_id, o.employee_id, o.work_date, o.hours,
                   o.reason, CAST(o.status AS text) AS status,
                   o.reviewed_by, o.reviewed_at, o.review_note,
                   o.created_at, o.plan_document_id,
                   wp.unit_id
              FROM vms.overtime_log o
              JOIN vms.work_plan wp ON wp.id = o.work_plan_id
             WHERE o.id = CAST(:ot AS uuid) AND o.organization_id = CAST(:org AS uuid)
            """,
            {"ot": overtime_id, "org": org_id},
        )

    async def review(
        self,
        overtime_id: UUID | str,
        reviewer_emp: str,
        decision: str,
        note: str | None,
    ) -> Any:
        """Setujui atau tolak pengajuan lembur yang masih PENDING_PM."""
        return await self.fetchone(
            """
            UPDATE vms.overtime_log
               SET status      = CAST(:decision AS vms.approval_status),
                   reviewed_by = CAST(:emp AS uuid),
                   reviewed_at = now(),
                   review_note = :note
             WHERE id = CAST(:ot AS uuid) AND CAST(status AS text) = 'PENDING_PM'
            RETURNING *
            """,
            {"ot": overtime_id, "decision": decision, "emp": reviewer_emp, "note": note},
        )

    async def list_by_plan(self, plan_id: UUID | str, org_id: str) -> Sequence[Any]:
        """Semua lembur SK (terurut terbaru dahulu) — untuk tampilan per SK."""
        return await self.fetchall(
            """
            SELECT id, work_plan_id, plan_document_id, employee_id, work_date,
                   hours, reason, CAST(status AS text) AS status,
                   reviewed_by, reviewed_at, review_note, created_at
              FROM vms.overtime_log
             WHERE work_plan_id = CAST(:plan AS uuid)
               AND organization_id = CAST(:org AS uuid)
             ORDER BY created_at DESC
            """,
            {"plan": plan_id, "org": org_id},
        )

    async def recap(self, org_id: str, month: date | None, pm_user_id: str | None) -> Sequence[Any]:
        """Rekap per karyawan per bulan (padanan v_overtime_recap). `month` = tanggal 1 bulan itu atau None.
        `pm_user_id`: hanya lembur pada SK di unit yang dipegang PM itu (keputusan pemilik, dok 10 V-28)."""
        return await self.fetchall(
            """
            SELECT o.organization_id, CAST(date_trunc('month', o.work_date) AS date) AS period_month,
                   o.employee_id, e.full_name AS employee_name,
                   count(*) FILTER (WHERE o.status = 'APPROVED') AS approved_entries,
                   count(*) FILTER (WHERE o.status = 'PENDING_PM') AS pending_entries,
                   COALESCE(sum(o.hours) FILTER (WHERE o.status = 'APPROVED'), 0) AS approved_hours
              FROM vms.overtime_log o
              JOIN vms.employee e ON e.id = o.employee_id
              JOIN vms.work_plan wp ON wp.id = o.work_plan_id
             WHERE o.organization_id = CAST(:org AS uuid)
               AND (CAST(:month AS date) IS NULL
                    OR CAST(date_trunc('month', o.work_date) AS date) = CAST(:month AS date))
               AND (CAST(:pm AS uuid) IS NULL OR EXISTS (
                    SELECT 1 FROM vms.user_role ur
                     WHERE ur.user_id = CAST(:pm AS uuid) AND ur.role = 'PM'
                       AND (ur.unit_id IS NULL OR ur.unit_id = wp.unit_id)))
             GROUP BY o.organization_id, period_month, o.employee_id, e.full_name
             ORDER BY period_month DESC, employee_name
            """,
            {"org": org_id, "month": month, "pm": pm_user_id},
        )
