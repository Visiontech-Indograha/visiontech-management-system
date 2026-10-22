"""
app/modules/divisions/services/division_service.py
Divisi operasional (Milestone 2, docs/36; struktur docs/35 §2: OM → divisi → PM → tim).

- Daftar divisi terbuka untuk semua pengguna (dipakai form karyawan, tim, rencana kerja).
- Kelola butuh izin `manage:divisions` (SUPER_ADMIN, OPERATIONAL_MANAGER).
- `om_id` wajib karyawan aktif ber-peran OPERATIONAL_MANAGER, `pm_id` ber-peran PROJECT_MANAGER.
- Divisi yang masih punya tim atau karyawan aktif tidak dapat dihapus (nonaktifkan lewat `status`).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.errors import AppError, NotFoundError, ValidationError
from app.modules.divisions.repositories.division_repository import CRUDDivision
from app.modules.divisions.schemas.division_schema import DivisionCreate, DivisionUpdate

_ROLE_LABEL = {"OPERATIONAL_MANAGER": "Operational Manager", "PROJECT_MANAGER": "Project Manager"}


class DivisionService:
    """Layanan divisi operasional."""

    def __init__(self, repo: CRUDDivision) -> None:
        self.repo = repo

    async def list_divisions(self, org_id: UUID | str) -> list[Any]:
        return await self.repo.list_for_org(org_id)

    async def _require_role(self, employee_id: UUID, role: str, field: str) -> None:
        if await self.repo.employee_role(employee_id) != role:
            raise ValidationError(f"{field} harus karyawan aktif dengan peran {_ROLE_LABEL[role]}.")

    async def create_division(self, data: DivisionCreate) -> Any:
        await self._require_role(data.om_id, "OPERATIONAL_MANAGER", "OM divisi")
        await self._require_role(data.pm_id, "PROJECT_MANAGER", "PM divisi")
        return await self.repo.insert(data.name.strip(), data.om_id, data.pm_id)

    async def update_division(self, division_id: UUID, data: DivisionUpdate) -> Any:
        if await self.repo.get(division_id) is None:
            raise NotFoundError("Divisi")
        if data.om_id:
            await self._require_role(data.om_id, "OPERATIONAL_MANAGER", "OM divisi")
        if data.pm_id:
            await self._require_role(data.pm_id, "PROJECT_MANAGER", "PM divisi")
        return await self.repo.update(
            division_id, name=data.name.strip() if data.name else None, om_id=data.om_id, pm_id=data.pm_id,
            status=data.status,
        )

    async def delete_division(self, division_id: UUID) -> None:
        if await self.repo.get(division_id) is None:
            raise NotFoundError("Divisi")
        teams, employees = await self.repo.in_use(division_id)
        if teams or employees:
            raise AppError(
                "DIVISION_IN_USE",
                f"Divisi masih dipakai {teams} tim dan {employees} karyawan aktif. "
                "Pindahkan dulu, atau nonaktifkan divisi.",
                status=409,
            )
        await self.repo.archive(division_id)
