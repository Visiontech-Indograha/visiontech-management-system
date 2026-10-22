"""
Jabatan (Milestone 10): HR (`manage:users`) mengelola; semua yang login boleh membaca (form karyawan).
Kode unik (tanpa beda huruf besar/kecil); jabatan yang masih dipakai karyawan aktif tidak bisa dihapus.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.errors import AppError, NotFoundError
from app.modules.job_positions.repositories.job_position_repository import JobPositionRepository
from app.modules.job_positions.schemas.job_position_schema import JobPositionCreate, JobPositionUpdate


class JobPositionService:
    def __init__(self, repo: JobPositionRepository) -> None:
        self.repo = repo

    async def list(self, division_id: UUID | None, active_only: bool) -> list[Any]:
        return await self.repo.list(division_id, active_only)

    async def create(self, data: JobPositionCreate) -> Any:
        if await self.repo.code_taken(data.code.strip()):
            raise AppError("POSITION_CODE_TAKEN", "Kode jabatan sudah dipakai.", status=409)
        return await self.repo.insert(
            {**data.model_dump(), "code": data.code.strip().upper(), "name": data.name.strip()})

    async def update(self, position_id: UUID, data: JobPositionUpdate) -> Any:
        if await self.repo.get(position_id) is None:
            raise NotFoundError("Jabatan")
        fields = data.model_dump(exclude_unset=True)
        if fields.get("code"):
            fields["code"] = fields["code"].strip().upper()
            if await self.repo.code_taken(fields["code"], exclude=position_id):
                raise AppError("POSITION_CODE_TAKEN", "Kode jabatan sudah dipakai.", status=409)
        return await self.repo.update(position_id, fields)

    async def delete(self, position_id: UUID) -> None:
        row = await self.repo.get(position_id)
        if row is None:
            raise NotFoundError("Jabatan")
        if row.employee_count:
            raise AppError("POSITION_IN_USE", f"Jabatan masih dipakai {row.employee_count} karyawan. "
                           "Nonaktifkan saja, atau pindahkan karyawannya dulu.", status=409)
        await self.repo.archive(position_id)
