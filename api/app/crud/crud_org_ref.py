"""
app/crud/crud_org_ref.py
Kepemilikan rujukan di badan permintaan (V-08). FK hanya memastikan baris ada — bukan milik
organisasi pengguna — jadi setiap id yang dikirim klien dihitung di sini per jenis.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .base import CRUDBase


class CRUDOrgRef(CRUDBase):

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
        """Jumlah id per jenis yang benar-benar milik organisasi (dan belum dihapus)."""
        return await self.fetchone(
            """
            SELECT
                (SELECT count(*) FROM vms.work_plan WHERE id = ANY(CAST(:work_plans AS uuid[]))
                    AND organization_id = CAST(:org AS uuid) AND deleted_at IS NULL) AS work_plans,
                (SELECT count(*) FROM vms.site WHERE id = ANY(CAST(:sites AS uuid[]))
                    AND organization_id = CAST(:org AS uuid) AND deleted_at IS NULL) AS sites,
                (SELECT count(*) FROM vms.asset WHERE id = ANY(CAST(:assets AS uuid[]))
                    AND organization_id = CAST(:org AS uuid) AND deleted_at IS NULL) AS assets,
                (SELECT count(*) FROM vms.file_object WHERE id = ANY(CAST(:files AS uuid[]))
                    AND organization_id = CAST(:org AS uuid)) AS files,
                (SELECT count(*) FROM vms.employee WHERE id = ANY(CAST(:employees AS uuid[]))
                    AND organization_id = CAST(:org AS uuid) AND deleted_at IS NULL) AS employees,
                (SELECT count(*) FROM vms.business_unit WHERE id = ANY(CAST(:units AS uuid[]))
                    AND organization_id = CAST(:org AS uuid) AND deleted_at IS NULL) AS units
            """,
            {"org": org_id, "work_plans": list(work_plans), "sites": list(sites), "assets": list(assets),
             "files": list(files), "employees": list(employees), "units": list(units)},
        )
