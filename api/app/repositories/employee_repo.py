"""
app/repositories/employee_repo.py
Kueri karyawan untuk servis baru (V-29). Rute lama di api/employees.py belum dipindah ke sini.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base_repo import BaseRepo


class EmployeeRepo(BaseRepo):

    async def lock(self, employee_id: UUID | str, org_id: UUID | str) -> Any:
        return await self.fetchone(
            """
            SELECT id, deleted_at IS NOT NULL AS deleted, is_active
            FROM vms.employee WHERE id = :id AND organization_id = :org
            FOR UPDATE
            """,
            {"id": employee_id, "org": org_id},
        )

    async def restore(self, employee_id: UUID | str) -> None:
        """domain.js RESTORE_EMPLOYEE: data kembali sebagai NONAKTIF; akun tetap dicabut."""
        await self.execute(
            "UPDATE vms.employee SET deleted_at = NULL, is_active = false, updated_at = now() WHERE id = :id",
            {"id": employee_id})
        await self.execute("UPDATE vms.app_user SET is_active = false WHERE employee_id = :id", {"id": employee_id})

    async def archive(self, employee_id: UUID | str) -> None:
        """Hapus lunak: tersembunyi dari daftar, data historis (SK, absensi, dokumen) tetap."""
        await self.execute(
            "UPDATE vms.employee SET deleted_at = now(), is_active = false, updated_at = now() WHERE id = :id",
            {"id": employee_id})
        await self.execute("UPDATE vms.app_user SET is_active = false WHERE employee_id = :id", {"id": employee_id})
