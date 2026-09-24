"""
app/repositories/plan_access_repo.py
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

from .base_repo import BaseRepo

# `:plan` NULL → semua SK terlihat (daftar); terisi → satu SK (penjaga). `:status` NULL → semua status.
_STANDING = """
    SELECT * FROM (
        SELECT wp.id, wp.unit_id, wp.site_id, wp.number, wp.title, wp.location_text, wp.description,
               lower(wp.period) AS period_start, upper(wp.period) - 1 AS period_end,
               wp.status, wp.pm_employee_id, wp.leader_employee_id, wp.revision, wp.row_version,
               wp.cancellation_reason, wp.created_at,
               s.oversees OR s.pm_of_unit AS manages,
               s.is_leader, s.is_member,
               s.oversees OR s.pm_of_unit
                   OR (wp.status <> 'DRAFT' AND (s.asset_officer OR s.is_leader OR s.is_member)) AS visible
        FROM vms.work_plan wp
        CROSS JOIN LATERAL (
            SELECT
                EXISTS (SELECT 1 FROM vms.user_role ur
                        WHERE ur.user_id = CAST(:user AS uuid) AND ur.role IN ('ADMIN', 'OPS')) AS oversees,
                EXISTS (SELECT 1 FROM vms.user_role ur
                        WHERE ur.user_id = CAST(:user AS uuid) AND ur.role = 'PM'
                          AND (ur.unit_id IS NULL OR ur.unit_id = wp.unit_id)) AS pm_of_unit,
                EXISTS (SELECT 1 FROM vms.user_role ur
                        WHERE ur.user_id = CAST(:user AS uuid) AND ur.role = 'ASSET') AS asset_officer,
                vms.is_plan_leader(wp.id, CAST(:user AS uuid)) AS is_leader,
                vms.is_plan_member(wp.id, CAST(:user AS uuid)) AS is_member
        ) AS s
        WHERE wp.organization_id = CAST(:org AS uuid) AND wp.deleted_at IS NULL
          AND (CAST(:plan AS uuid) IS NULL OR wp.id = CAST(:plan AS uuid))
          AND (CAST(:status AS text) IS NULL OR CAST(wp.status AS text) = CAST(:status AS text))
    ) AS standing
    WHERE standing.visible
    ORDER BY standing.created_at DESC
"""


class PlanAccessRepo(BaseRepo):

    async def standing(self, plan_id: UUID | str, org_id: UUID | str, user_id: UUID | str) -> Any:
        """Baris SK + kedudukan pengguna; None bila SK tidak ada, milik organisasi lain, atau tak terlihat."""
        return await self.fetchone(_STANDING, {"plan": str(plan_id), "org": org_id, "user": user_id, "status": None})

    async def visible_plans(self, org_id: UUID | str, user_id: UUID | str, status: str | None) -> Sequence[Any]:
        return await self.fetchall(_STANDING, {"plan": None, "org": org_id, "user": user_id, "status": status})

    async def plan_of_day(self, day_id: UUID | str) -> Any:
        return await self.scalar("SELECT work_plan_id FROM vms.work_plan_day WHERE id = :day", {"day": day_id})

    async def unit_standing(self, unit_id: UUID | str, org_id: UUID | str, user_id: UUID | str) -> Any:
        """(ada di organisasi ini?, boleh dikelola pengguna?) — untuk membuat SK di sebuah unit."""
        return await self.fetchone(
            """
            SELECT EXISTS (
                SELECT 1 FROM vms.user_role ur
                WHERE ur.user_id = CAST(:user AS uuid)
                  AND (ur.role IN ('ADMIN', 'OPS') OR (ur.role = 'PM' AND (ur.unit_id IS NULL OR ur.unit_id = bu.id)))
            ) AS manages
            FROM vms.business_unit bu
            WHERE bu.id = CAST(:unit AS uuid) AND bu.organization_id = CAST(:org AS uuid)
            """,
            {"unit": str(unit_id), "org": org_id, "user": user_id},
        )
