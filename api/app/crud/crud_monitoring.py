"""
app/crud/crud_monitoring.py
Pemantauan OPS (V-30): hari kerja per SK untuk lini masa, dan rekap absensi per karyawan.
"""
from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDMonitoring(CRUDBase):

    async def plan_days(self, plan_ids: list[str]) -> list[Any]:
        """Hari kerja + status laporan hariannya untuk sekumpulan SK, urut tanggal."""
        return list(await self.fetchall(
            """
            SELECT CAST(wpd.work_plan_id AS text) AS work_plan_id, wpd.id, wpd.work_date, wpd.title,
                   CAST(dr.status AS text) AS report_status
            FROM vms.work_plan_day wpd
            LEFT JOIN vms.daily_report dr ON dr.work_plan_day_id = wpd.id
            WHERE wpd.work_plan_id = ANY(CAST(:plans AS uuid[]))
            ORDER BY wpd.work_date, wpd.sort_order
            """,
            {"plans": plan_ids},
        ))

    async def names(self, employee_ids: list[str]) -> dict[str, str]:
        rows = await self.fetchall(
            "SELECT CAST(id AS text) AS id, full_name FROM vms.employee WHERE id = ANY(CAST(:ids AS uuid[]))",
            {"ids": employee_ids})
        return {row.id: row.full_name for row in rows}

    async def attendance_recap(self, org_id: UUID | str, starts: date, ends: date, viewer_user_id: str,
                               scope: str) -> list[Any]:
        """Hitungan absensi per karyawan dalam [starts, ends). `scope` (R-33): 'all' (Finance/OPS),
        'subordinates' (PM — pekerja lapangan di unitnya, tanpa dirinya), 'own' (milik sendiri)."""
        return list(await self.fetchall(
            """
            SELECT CAST(e.id AS text) AS employee_id, e.full_name,
                   count(*) FILTER (WHERE a.status IN ('AUTO_VALID', 'APPROVED')) AS days_present,
                   count(*) FILTER (WHERE a.status = 'AUTO_VALID') AS auto_valid,
                   count(*) FILTER (WHERE a.status = 'NEEDS_REVIEW') AS needs_review,
                   count(*) FILTER (WHERE a.status = 'APPROVED') AS approved,
                   count(*) FILTER (WHERE a.status = 'REJECTED') AS rejected
            FROM vms.attendance a
            JOIN vms.employee e ON e.id = a.employee_id
            WHERE a.organization_id = :org AND a.work_date >= :starts AND a.work_date < :ends
              AND (CAST(:scope AS text) = 'all'
                   OR (CAST(:scope AS text) = 'subordinates'
                       AND vms.attendance_pm_subordinate(CAST(:viewer AS uuid), a.employee_id))
                   OR (CAST(:scope AS text) = 'own'
                       AND a.employee_id = (SELECT employee_id FROM vms.app_user WHERE id = CAST(:viewer AS uuid))))
            GROUP BY e.id, e.full_name
            ORDER BY e.full_name
            """,
            {"org": org_id, "starts": starts, "ends": ends, "viewer": viewer_user_id, "scope": scope},
        ))

    async def attendance_recap_days(self, org_id: UUID | str, starts: date, ends: date, viewer_user_id: str,
                                    scope: str) -> list[Any]:
        """Riwayat per absensi (jam masuk & keluar) dalam [starts, ends), cakupan sama dengan rekap (R-33)."""
        return list(await self.fetchall(
            """
            SELECT CAST(a.id AS text) AS id, CAST(e.id AS text) AS employee_id, e.full_name, a.work_date,
                   a.site_label, a.check_in_at, a.check_out_at, CAST(a.status AS text) AS status,
                   a.is_late, a.is_early_leave
            FROM vms.attendance a
            JOIN vms.employee e ON e.id = a.employee_id
            WHERE a.organization_id = :org AND a.work_date >= :starts AND a.work_date < :ends
              AND (CAST(:scope AS text) = 'all'
                   OR (CAST(:scope AS text) = 'subordinates'
                       AND vms.attendance_pm_subordinate(CAST(:viewer AS uuid), a.employee_id))
                   OR (CAST(:scope AS text) = 'own'
                       AND a.employee_id = (SELECT employee_id FROM vms.app_user WHERE id = CAST(:viewer AS uuid))))
            ORDER BY a.work_date DESC, e.full_name, a.check_in_at DESC
            """,
            {"org": org_id, "starts": starts, "ends": ends, "viewer": viewer_user_id, "scope": scope},
        ))
