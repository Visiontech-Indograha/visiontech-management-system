"""
app/shared/access/plan_access_repository.py
Kedudukan pengguna terhadap SK (V-07): siapa yang boleh melihat dan mengelola, dan apakah ia ketua
atau anggota menurut SK yang berlaku. Satu kueri dipakai penjaga `plan_access` dan daftar SK agar
aturan "terlihat" hanya ditulis sekali.

Terlihat (`domain.js` visiblePlans; `db/03` work_plan_visibility):
- ADMIN, OPS — semua SK organisasi;
- PM — SK unitnya (termasuk draf);
- ketua/anggota menurut SK, ASSET — SK yang sudah terbit (bukan DRAFT).
Mengelola (kewenangan PM) = ADMIN, OPS (`domain.js` permissions.OPS), atau PM unit SK itu.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from app.core.repository import CRUDBase

# `:plan` NULL → semua SK terlihat (daftar); terisi → satu SK (penjaga). `:status` NULL → semua status.
_STANDING = """
    WITH weekly_plans AS (
        SELECT
            CAST(MIN(CAST(wpd.daily_plan_id AS text)) AS uuid) AS id,
            wpd.division_id,
            wpd.team_id,
            CAST(EXTRACT(WEEK FROM wpd.work_date) AS integer) AS week_number,
            CAST(EXTRACT(YEAR FROM wpd.work_date) AS integer) AS year,
            DATE_TRUNC('week', wpd.work_date)::date AS period_start,
            (DATE_TRUNC('week', wpd.work_date) + interval '6 days')::date AS period_end,
            CASE
                WHEN bool_and(wpd.status = 'APPROVED') THEN 'APPROVED'
                WHEN bool_or(wpd.status = 'ONGOING') THEN 'ONGOING'
                ELSE 'SUBMITTED'
            END AS status,
            MIN(wpd.site_name) AS site_name,
            CAST(MIN(CAST(wpd.approved_by_pm_id AS text)) AS uuid) AS approved_by_pm_id,
            MIN(wpd.create_at) AS create_at
        FROM work_plan_daily wpd
        WHERE wpd.delete_at IS NULL
        GROUP BY wpd.division_id, wpd.team_id,
                 EXTRACT(YEAR FROM wpd.work_date), EXTRACT(WEEK FROM wpd.work_date),
                 DATE_TRUNC('week', wpd.work_date)
    )
    SELECT
        w.id AS id,
        w.division_id AS unit_id,
        div.name AS division_name,
        o.office_id AS site_id,
        'SK/W' || w.week_number || '/' || w.year AS number,
        'Rencana Kerja Mingguan W' || w.week_number || ' - ' || t.name AS title,
        COALESCE(w.site_name, 'Site Operasional ' || t.name) AS location_text,
        'Rencana kerja mingguan terintegrasi tim ' || t.name AS description,
        w.period_start,
        w.period_end,
        w.status,
        COALESCE(w.approved_by_pm_id, div.pm_id) AS pm_employee_id,
        t.leader_employee_id,
        0 AS revision,
        1 AS row_version,
        NULL::text AS cancellation_reason,
        NULL::text AS appeal_reason,
        'INSTALASI' AS category,
        FALSE AS is_out_of_town,
        CAST(MIN(CAST(item.work_type_id AS text)) AS uuid) AS work_type_id,
        COALESCE(MIN(item.work_type_name), 'Instalasi & Maintenance') AS work_type_name,
        EXISTS (
            SELECT 1 FROM work_plan_item wpi
            JOIN work_plan_daily d ON d.daily_plan_id = wpi.daily_plan_id
            WHERE d.division_id = w.division_id AND d.team_id = w.team_id
              AND d.work_date BETWEEN w.period_start AND w.period_end
              AND wpi.rollover_approval_status = 'WAITING_PM'
        ) AS pending_request,
        today_d.daily_plan_id AS today_site_id,
        TRUE AS today_included,
        w.create_at AS created_at,
        TRUE AS manages,
        (t.leader_employee_id = emp.employee_id) AS is_leader,
        EXISTS (SELECT 1 FROM member m WHERE m.team_id = w.team_id AND m.employee_id = emp.employee_id AND m.is_active = TRUE) AS is_member,
        TRUE AS visible
    FROM weekly_plans w
    JOIN division div ON div.division_id = w.division_id
    JOIN team t ON t.team_id = w.team_id
    LEFT JOIN office o ON o.office_id = t.office_id
    LEFT JOIN LATERAL (
        SELECT wpd.daily_plan_id
        FROM work_plan_daily wpd
        WHERE wpd.division_id = w.division_id AND wpd.team_id = w.team_id
          AND wpd.work_date = CURRENT_DATE
          AND wpd.delete_at IS NULL
        LIMIT 1
    ) today_d ON TRUE
    LEFT JOIN LATERAL (
        SELECT wpi.work_type_id, wt.name AS work_type_name
        FROM work_plan_item wpi
        JOIN work_plan_daily d ON d.daily_plan_id = wpi.daily_plan_id
        LEFT JOIN work_type wt ON wt.work_type_id = wpi.work_type_id
        WHERE d.division_id = w.division_id AND d.team_id = w.team_id
          AND d.work_date BETWEEN w.period_start AND w.period_end
          AND wpi.delete_at IS NULL
        LIMIT 1
    ) item ON TRUE
    LEFT JOIN LATERAL (
        SELECT u.employee_id
        FROM users u
        WHERE u.user_id = CAST(:user AS uuid)
    ) emp ON TRUE
    WHERE (CAST(:plan AS uuid) IS NULL OR w.id = CAST(:plan AS uuid))
      AND (CAST(:status AS text) IS NULL OR w.status = CAST(:status AS text))
    GROUP BY w.id, w.division_id, div.name, div.pm_id, o.office_id, t.name, t.leader_employee_id, w.team_id,
             w.week_number, w.year, w.period_start, w.period_end, w.status, w.site_name, w.approved_by_pm_id,
             w.create_at, today_d.daily_plan_id, emp.employee_id
    ORDER BY w.period_start DESC
"""


class CRUDPlanAccess(CRUDBase):
    """
    Kelas CRUD untuk mengelola dan memverifikasi akses pengguna terhadap Work Plan (SK).
    """

    async def standing(
        self, plan_id: UUID | str, org_id: UUID | str, user_id: UUID | str, archived: bool | None = False
    ) -> Any:
        return await self.fetchone(
            _STANDING, {"plan": str(plan_id), "org": org_id, "user": user_id, "status": None, "archived": archived}
        )

    async def visible_plans(
        self, org_id: UUID | str, user_id: UUID | str, status: str | None, archived: bool = False
    ) -> Sequence[Any]:
        return await self.fetchall(
            _STANDING, {"plan": None, "org": org_id, "user": user_id, "status": status, "archived": archived}
        )

    async def plan_of_day(self, day_id: UUID | str) -> Any:
        return await self.scalar(
            "SELECT weekly_plan_id AS work_plan_id FROM work_plan_daily WHERE daily_plan_id = CAST(:day AS uuid) AND delete_at IS NULL",
            {"day": day_id},
        )

    async def plan_of_allocation(self, allocation_id: UUID | str) -> Any:
        return await self.scalar(
            """
            SELECT wpd.weekly_plan_id AS work_plan_id
            FROM asset_assignment aa
            JOIN work_plan_daily wpd ON wpd.daily_plan_id = aa.daily_plan_id
            WHERE aa.assignment_id = CAST(:alloc AS uuid) AND aa.delete_at IS NULL
            """,
            {"alloc": allocation_id},
        )

    async def plan_of_incident(self, incident_id: UUID | str, org_id: UUID | str) -> Any:
        return None

    async def unit_standing(self, unit_id: UUID | str, org_id: UUID | str, user_id: UUID | str) -> Any:
        return await self.fetchone(
            """
            SELECT EXISTS (
                SELECT 1 FROM division div
                WHERE div.division_id = CAST(:unit AS uuid) AND div.delete_at IS NULL
            ) AS manages
            """,
            {"unit": str(unit_id)},
        )
