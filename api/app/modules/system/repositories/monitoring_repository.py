"""
app/modules/system/repositories/monitoring_repository.py
Pemantauan OPS (V-30): hari kerja per rencana kerja untuk lini masa, dan rekap absensi per karyawan (Master Schema V2).
"""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from app.core.repository import CRUDBase
from app.shared.attendance_sql import IS_LATE_A


class CRUDMonitoring(CRUDBase):
    """
    Kelas operasi CRUD untuk fitur pemantauan OPS (Operations) Master Schema V2.
    Menangani kueri terkait hari kerja, rekapitulasi absensi per karyawan,
    dan riwayat absensi terperinci dengan pembatasan hak akses (scope).
    """

    async def names(self, employee_ids: list[str]) -> dict[str, str]:
        """
        Mendapatkan pemetaan (mapping) antara ID karyawan dan nama lengkapnya.
        """
        rows = await self.fetchall(
            """
            SELECT CAST(employee_id AS text) AS id, full_name
            FROM employee
            WHERE employee_id = ANY(CAST(:ids AS uuid[])) AND delete_at IS NULL
            """,
            {"ids": employee_ids},
        )
        return {row.id: row.full_name for row in rows}

    async def attendance_recap(
        self, org_id: UUID | str, starts: date, ends: date, viewer_user_id: str, scope: str
    ) -> list[Any]:
        """
        Menghitung rekapitulasi jumlah hari absensi per karyawan dalam rentang tanggal tertentu [starts, ends).
        """
        return list(
            await self.fetchall(
                """
            SELECT CAST(e.employee_id AS text) AS employee_id, e.full_name,
                   count(*) FILTER (
                       WHERE a.is_within_attendance_radius = TRUE OR a.om_approval_status = 'APPROVED_BY_OM'
                   ) AS days_present,
                   count(*) FILTER (WHERE a.is_within_attendance_radius = TRUE) AS auto_valid,
                   count(*) FILTER (
                       WHERE a.is_within_attendance_radius = FALSE AND a.om_approval_status = 'PENDING_OM'
                   ) AS needs_review,
                   count(*) FILTER (
                       WHERE a.is_within_attendance_radius = FALSE AND a.om_approval_status = 'APPROVED_BY_OM'
                   ) AS approved,
                   count(*) FILTER (
                       WHERE a.is_within_attendance_radius = FALSE AND a.om_approval_status = 'REJECTED_BY_OM'
                   ) AS rejected
            FROM attendance a
            JOIN employee e ON e.employee_id = a.employee_id
            WHERE a.delete_at IS NULL
              AND a.attendance_date >= :starts AND a.attendance_date < :ends
              AND (
                  CAST(:scope AS text) = 'all'
                  OR (
                      CAST(:scope AS text) = 'subordinates'
                      AND a.employee_id IN (
                          SELECT m.employee_id FROM member m
                          JOIN team t ON t.team_id = m.team_id
                          JOIN division d ON d.division_id = t.division_id
                          JOIN users u ON u.user_id = CAST(:viewer AS uuid)
                          WHERE d.pm_id = u.employee_id OR d.om_id = u.employee_id
                      )
                  )
                  OR (
                      CAST(:scope AS text) = 'own'
                      AND a.employee_id = (SELECT employee_id FROM users WHERE user_id = CAST(:viewer AS uuid))
                  )
              )
            GROUP BY e.employee_id, e.full_name
            ORDER BY e.full_name
            """,
                {"starts": starts, "ends": ends, "viewer": str(viewer_user_id), "scope": scope},
            )
        )

    async def attendance_recap_days(
        self, org_id: UUID | str, starts: date, ends: date, viewer_user_id: str, scope: str
    ) -> list[Any]:
        """
        Mengambil rincian riwayat data absensi untuk rentang waktu tertentu.
        """
        return list(
            await self.fetchall(
                f"""
            SELECT CAST(a.attendance_id AS text) AS id,
                   CAST(e.employee_id AS text) AS employee_id,
                   e.full_name,
                   a.attendance_date AS work_date,
                   COALESCE(o.name, 'Kantor / Site') AS site_label,
                   a.clock_in_at AS check_in_at,
                   a.clock_out_at AS check_out_at,
                   CASE
                       WHEN a.is_within_attendance_radius = TRUE THEN 'AUTO_VALID'
                       WHEN a.om_approval_status = 'APPROVED_BY_OM' THEN 'APPROVED'
                       WHEN a.om_approval_status = 'REJECTED_BY_OM' THEN 'REJECTED'
                       ELSE 'NEEDS_REVIEW'
                   END AS status,
                   ({IS_LATE_A}) AS is_late,
                   (a.clock_out_at IS NOT NULL
                    AND (a.clock_out_at AT TIME ZONE 'Asia/Jakarta')::time < a.scheduled_out) AS is_early_leave,
                   CAST(a.city_zone_status AS text) AS city_category
            FROM attendance a
            JOIN employee e ON e.employee_id = a.employee_id
            LEFT JOIN office o ON o.office_id = a.office_id
            WHERE a.delete_at IS NULL
              AND a.attendance_date >= :starts AND a.attendance_date < :ends
              AND (
                  CAST(:scope AS text) = 'all'
                  OR (
                      CAST(:scope AS text) = 'subordinates'
                      AND a.employee_id IN (
                          SELECT m.employee_id FROM member m
                          JOIN team t ON t.team_id = m.team_id
                          JOIN division d ON d.division_id = t.division_id
                          JOIN users u ON u.user_id = CAST(:viewer AS uuid)
                          WHERE d.pm_id = u.employee_id OR d.om_id = u.employee_id
                      )
                  )
                  OR (
                      CAST(:scope AS text) = 'own'
                      AND a.employee_id = (SELECT employee_id FROM users WHERE user_id = CAST(:viewer AS uuid))
                  )
              )
            ORDER BY a.attendance_date DESC, e.full_name, a.clock_in_at DESC
            """,
                {"starts": starts, "ends": ends, "viewer": str(viewer_user_id), "scope": scope},
            )
        )
