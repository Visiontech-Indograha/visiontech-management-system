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
    """
    Kelas CRUD untuk verifikasi kepemilikan entitas (referensi silang) terhadap sebuah organisasi.
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
        """Jumlah id per jenis yang benar-benar milik organisasi (dan belum dihapus).

        Args:
            org_id (str): ID dari organisasi.
            work_plans (Sequence[str]): Daftar ID Work Plan.
            sites (Sequence[str]): Daftar ID Site.
            assets (Sequence[str]): Daftar ID Asset.
            files (Sequence[str]): Daftar ID File Object.
            employees (Sequence[str]): Daftar ID Employee.
            units (Sequence[str]): Daftar ID Business Unit.

        Returns:
            Any: Baris data yang menyimpan penghitungan dari ID valid per masing-masing jenis.
        """
        # Mengeksekusi beberapa subkueri `SELECT count(*)` secara independen dalam sebuah pernyataan SELECT
        # untuk memverifikasi jumlah kemunculan id (yang ada di dalam array argument parameter)
        # yang match dengan organization_id dan dipastikan belum di-soft-delete (deleted_at IS NULL).
        # Cara ini sangat efisien untuk menghitung kevalidan referensi dalam satu buah panggilan query ke database.
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

