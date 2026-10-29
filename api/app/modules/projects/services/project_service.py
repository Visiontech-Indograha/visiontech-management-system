"""
Proyek/SPK (Milestone 10): satu SPK klien yang dikerjakan satu divisi, dipimpin PM.
- Kelola: PM/OM divisi proyek atau SUPER_ADMIN (check_division_manager); PM proyek wajib ber-peran PROJECT_MANAGER.
- Baca: SUPER_ADMIN & HR semua; PM/OM divisinya / proyeknya; lapangan hanya proyek yang punya jadwal timnya.
- Nomor SPK unik; tanggal selesai ≥ mulai; proyek yang sudah punya jadwal/order tidak bisa dihapus (batalkan saja).
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.errors import AppError, NotFoundError, ValidationError
from app.core.security import CurrentUser
from app.modules.projects.repositories.project_repository import ProjectRepository
from app.modules.projects.schemas.project_schema import ProjectCreate, ProjectUpdate
from app.shared.access.access_service import check_division_manager

SEE_ALL = ("SUPER_ADMIN", "ADMIN_HR_GA")
SPK_TAKEN = "Nomor SPK sudah dipakai proyek lain."


class ProjectService:
    def __init__(self, repo: ProjectRepository) -> None:
        self.repo = repo

    def _scope(self, user: CurrentUser) -> dict[str, Any]:
        return {"see_all": user.role in SEE_ALL, "employee_id": user.employee_id}

    async def list(self, user: CurrentUser, *, division_id: UUID | None, client_id: UUID | None,
                   status: str | None, q: str | None) -> list[Any]:
        return await self.repo.list(**self._scope(user), division_id=division_id, client_id=client_id,
                                    status=status, q=(q or "").strip() or None)

    async def get(self, user: CurrentUser, project_id: UUID) -> Any:
        row = await self.repo.get(project_id, **self._scope(user))
        if row is None:
            raise NotFoundError("Proyek")
        return row

    async def _check_refs(self, client_id: UUID | None, office_id: UUID | None, pm_id: UUID | None,
                          current: Any = None) -> None:
        client_ok, office_ok = await self.repo.refs_ok(client_id or current.client_id, office_id or current.office_id)
        if not client_ok:
            raise ValidationError("Klien tidak ditemukan atau nonaktif.")
        if not office_ok:
            raise ValidationError("Kantor tidak ditemukan.")
        if pm_id and await self.repo.employee_role(pm_id) != "PROJECT_MANAGER":
            raise ValidationError("PM proyek harus karyawan aktif dengan peran Project Manager.")

    async def create(self, user: CurrentUser, data: ProjectCreate) -> Any:
        await check_division_manager(self.repo.db, data.division_id, user)
        pm_id = data.pm_id or await self.repo.division_pm(data.division_id)
        await self._check_refs(data.client_id, data.office_id, pm_id)
        spk = data.spk_number.strip()
        if await self.repo.spk_taken(spk):
            raise AppError("SPK_TAKEN", SPK_TAKEN, status=409)
        return await self.repo.insert({**data.model_dump(), "pm_id": pm_id, "spk_number": spk,
                                       "project_title": data.project_title.strip()})

    async def update(self, user: CurrentUser, project_id: UUID, data: ProjectUpdate) -> Any:
        current = await self.get(user, project_id)
        await check_division_manager(self.repo.db, current.division_id, user)
        # Null eksplisit dari form (mis. pm_id kosong) berarti "tidak diubah", bukan menimpa kolom dengan NULL/'None'.
        fields = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
        if current.status in ("COMPLETED", "CANCELLED") and set(fields) - {"status"}:
            raise AppError("PROJECT_CLOSED", "Proyek sudah selesai/dibatalkan; hanya status yang bisa diubah.",
                           status=409)
        await self._check_refs(fields.get("client_id"), fields.get("office_id"), fields.get("pm_id"), current)
        start, end = fields.get("start_date", current.start_date), fields.get("end_date", current.end_date)
        if end < start:
            raise ValidationError("Tanggal selesai tidak boleh sebelum tanggal mulai.")
        if fields.get("spk_number"):
            fields["spk_number"] = fields["spk_number"].strip()
            if await self.repo.spk_taken(fields["spk_number"], exclude=project_id):
                raise AppError("SPK_TAKEN", SPK_TAKEN, status=409)
        return await self.repo.update(project_id, fields)

    async def delete(self, user: CurrentUser, project_id: UUID) -> None:
        current = await self.get(user, project_id)
        await check_division_manager(self.repo.db, current.division_id, user)
        if current.daily_plan_count or current.order_count:
            raise AppError("PROJECT_IN_USE", "Proyek sudah punya jadwal atau order. Batalkan lewat status saja.",
                           status=409)
        await self.repo.archive(project_id)
