"""
app/shared/access/org_ref_repository.py
Kepemilikan rujukan di badan permintaan Master Schema V2. Rencana kerja = `work_plan_daily` (model daily-first;
`work_plan_weekly` tidak ada lagi di test_migration).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.core.repository import CRUDBase


class CRUDOrgRef(CRUDBase):
    """
    Kelas CRUD untuk verifikasi kepemilikan entitas (referensi silang) Master Schema V2.
    """

    async def owned_counts(
        self,
        org_id: str,
        *,
        work_plans: Sequence[str],
        sites: Sequence[str],
        assets: Sequence[str],
        files: Sequence[str],
        employees: Sequence[str],
        units: Sequence[str],
    ) -> Any:
        """Jumlah id per jenis yang valid di Master Schema V2."""
        return await self.fetchone(
            """
            SELECT
                (SELECT count(*) FROM work_plan_daily WHERE daily_plan_id = ANY(CAST(:work_plans AS uuid[]))
                    AND delete_at IS NULL) AS work_plans,
                (SELECT count(*) FROM (
                    SELECT office_id AS id FROM office
                    WHERE office_id = ANY(CAST(:sites AS uuid[])) AND delete_at IS NULL
                    UNION
                    SELECT daily_plan_id AS id FROM work_plan_daily
                    WHERE daily_plan_id = ANY(CAST(:sites AS uuid[])) AND delete_at IS NULL
                ) s) AS sites,
                (SELECT count(*) FROM (
                    SELECT tool_id AS id FROM tool
                    WHERE tool_id = ANY(CAST(:assets AS uuid[])) AND delete_at IS NULL
                    UNION
                    SELECT vehicle_id AS id FROM vehicle
                    WHERE vehicle_id = ANY(CAST(:assets AS uuid[])) AND delete_at IS NULL
                ) a) AS assets,
                (SELECT count(*) FROM (
                    SELECT employee_file_id AS id FROM employee_file
                    WHERE employee_file_id = ANY(CAST(:files AS uuid[])) AND delete_at IS NULL
                    UNION
                    SELECT id FROM file_object
                    WHERE id = ANY(CAST(:files AS uuid[]))
                ) f) AS files,
                (SELECT count(*) FROM employee WHERE employee_id = ANY(CAST(:employees AS uuid[]))
                    AND delete_at IS NULL) AS employees,
                (SELECT count(*) FROM division WHERE division_id = ANY(CAST(:units AS uuid[]))
                    AND delete_at IS NULL) AS units
            """,
            {
                "work_plans": list(work_plans),
                "sites": list(sites),
                "assets": list(assets),
                "files": list(files),
                "employees": list(employees),
                "units": list(units),
            },
        )
