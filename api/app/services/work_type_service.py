"""
app/services/work_type_service.py
Jenis pekerjaan + template foto laporan (T9). PM/OPS mengelola; semua yang masuk boleh membaca yang aktif.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, NotFoundError, ValidationError
from app.crud.crud_work_type import CRUDWorkType
from app.schemas.work_type import WorkTypeIn
from app.services.access_service import ensure_same_org


class WorkTypeService:
    """Aturan jenis pekerjaan: nama unik per organisasi, label slot tidak boleh kembar, hapus = nonaktifkan."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = CRUDWorkType(db)

    async def list_types(self, org_id: str, include_inactive: bool) -> list[Any]:
        return await self.repo.list_types(org_id, include_inactive)

    async def get(self, org_id: str, type_id: UUID) -> Any:
        row = await self.repo.get_type(org_id, type_id)
        if row is None:
            raise NotFoundError("Jenis pekerjaan")
        return row

    @staticmethod
    def _clean(data: WorkTypeIn) -> tuple[str, list[dict[str, Any]]]:
        name = data.name.strip()
        if not name:
            raise ValidationError("Nama jenis pekerjaan wajib diisi.")
        photos = [{"label": p.label.strip(), "hint": (p.hint or "").strip() or None, "required": p.required,
                   "example_file_id": p.example_file_id} for p in data.photos]
        labels = [str(p["label"]).lower() for p in photos]
        if any(not label for label in labels):
            raise ValidationError("Label slot foto wajib diisi.")
        if len(set(labels)) != len(labels):
            raise ValidationError("Label slot foto tidak boleh kembar.")
        return name, photos

    async def _check_examples(self, org_id: str, photos: list[dict[str, Any]]) -> None:
        """Foto contoh harus berkas milik organisasi ini (V-08)."""
        await ensure_same_org(self.db, org_id, files=[p["example_file_id"] for p in photos])

    async def create(self, org_id: str, data: WorkTypeIn) -> Any:
        name, photos = self._clean(data)
        if await self.repo.name_taken(org_id, name, None):
            raise AppError("DUPLICATE", "Jenis pekerjaan dengan nama itu sudah ada.", status=409)
        await self._check_examples(org_id, photos)
        type_id = await self.repo.insert_type(org_id, name)
        await self.repo.replace_photos(org_id, type_id, photos)
        return await self.get(org_id, UUID(type_id))

    async def update(self, org_id: str, type_id: UUID, data: WorkTypeIn) -> Any:
        await self.get(org_id, type_id)
        name, photos = self._clean(data)
        if await self.repo.name_taken(org_id, name, type_id):
            raise AppError("DUPLICATE", "Jenis pekerjaan dengan nama itu sudah ada.", status=409)
        await self._check_examples(org_id, photos)
        await self.repo.update_type(type_id, name, True)
        await self.repo.replace_photos(org_id, type_id, photos)
        return await self.get(org_id, type_id)

    async def deactivate(self, org_id: str, type_id: UUID) -> None:
        row = await self.get(org_id, type_id)
        await self.repo.update_type(type_id, row.name, False)

    async def ensure_usable(self, org_id: str, type_id: UUID | None) -> None:
        """Jenis yang dipilih rencana kerja harus ada di organisasi ini dan aktif."""
        if type_id is not None and not await self.repo.type_is_usable(org_id, type_id):
            raise ValidationError("Jenis pekerjaan tidak ditemukan atau sudah dinonaktifkan.")

    async def ensure_plan_type(self, org_id: str, plan_id: UUID | None, type_id: UUID | None) -> None:
        """Jenis pada rencana kerja: harus aktif bila baru dipilih; yang sudah terpasang boleh tetap walau nonaktif."""
        if type_id is None:
            return
        if plan_id is not None and await self.repo.plan_type(plan_id) == str(type_id):
            return
        await self.ensure_usable(org_id, type_id)

    async def ensure_day_types(self, org_id: str, plan_id: UUID | None, type_ids: set[UUID]) -> None:
        """Jenis khusus per hari: aktif bila baru dipilih; yang sudah terpasang di rencana boleh tetap."""
        for type_id in type_ids:
            if plan_id is not None and await self.repo.type_in_plan(plan_id, type_id):
                continue
            await self.ensure_usable(org_id, type_id)

    async def template_of_plan(self, plan_id: UUID, day_id: UUID | None = None) -> list[Any]:
        return await self.repo.template_of_plan(plan_id, day_id)

    async def ensure_daily_complete(self, plan_id: UUID, day_id: UUID) -> None:
        """Saat laporan harian ketua dikirim: setiap slot wajib punya ≥ 1 foto."""
        self._raise_missing(await self.repo.missing_required_daily(plan_id, day_id))

    async def ensure_member_complete(self, plan_id: UUID, report_id: UUID | str) -> None:
        """Saat laporan anggota dikirim: setiap slot wajib punya ≥ 1 foto."""
        self._raise_missing(await self.repo.missing_required_member(plan_id, report_id))

    @staticmethod
    def _raise_missing(missing: list[str]) -> None:
        if missing:
            raise ValidationError(f"Foto wajib belum lengkap: {', '.join(missing)}.")
