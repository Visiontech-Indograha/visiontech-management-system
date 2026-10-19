"""
app/services/work_type_service.py
Jenis pekerjaan + template foto laporan (T9). PM/OPS mengelola; semua yang masuk boleh membaca yang aktif.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, NotFoundError, ValidationError
from app.modules.work_types.repositories.work_type_repository import CRUDWorkType
from app.modules.work_types.schemas.work_type_schema import DefaultMaterialIn, DefaultMaterialUpdate, WorkTypeIn
from app.services.access_service import ensure_same_org


class WorkTypeService:
    """Aturan jenis pekerjaan: nama unik per organisasi, label slot tidak boleh kembar, hapus = nonaktifkan."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = CRUDWorkType(db)

    async def list_types(
        self, org_id: str, include_inactive: bool, division_id: UUID | None = None
    ) -> list[Any]:
        return await self.repo.list_types(org_id, include_inactive, division_id)

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
        photos = [
            {
                "label": p.label.strip(),
                "hint": (p.hint or "").strip() or None,
                "required": p.required,
                "example_file_id": p.example_file_id,
            }
            for p in data.photos
        ]
        labels = [str(p["label"]).lower() for p in photos]
        if any(not label for label in labels):
            raise ValidationError("Label slot foto wajib diisi.")
        if len(set(labels)) != len(labels):
            raise ValidationError("Label slot foto tidak boleh kembar.")
        return name, photos

    async def _check_examples(self, org_id: str, photos: list[dict[str, Any]]) -> None:
        """Foto contoh harus berkas milik organisasi ini (V-08)."""
        await ensure_same_org(self.db, org_id, files=[p["example_file_id"] for p in photos])

    async def create(self, org_id: str, data: WorkTypeIn, creator_division_id: UUID | None = None) -> Any:
        division_id = creator_division_id or data.division_id
        if creator_division_id is not None and data.division_id and str(data.division_id) != str(creator_division_id):
            raise AppError(
                "FORBIDDEN", "Anda tidak memiliki hak untuk membuat jenis pekerjaan di divisi lain.", status=403
            )
        if division_id is None:
            raise ValidationError("Divisi wajib ditentukan untuk jenis pekerjaan ini.")
        name, photos = self._clean(data)
        if await self.repo.name_taken(org_id, division_id, name, None):
            raise AppError("DUPLICATE", "Jenis pekerjaan dengan nama itu sudah ada di divisi ini.", status=409)
        await self._check_examples(org_id, photos)
        type_id = await self.repo.insert_type(org_id, division_id, name, data.description)
        await self.repo.replace_photos(org_id, type_id, photos)
        return await self.get(org_id, UUID(type_id))

    async def update(
        self, org_id: str, type_id: UUID, data: WorkTypeIn, creator_division_id: UUID | None = None
    ) -> Any:
        existing = await self.get(org_id, type_id)
        if creator_division_id is not None and str(existing.division_id) != str(creator_division_id):
            raise AppError(
                "FORBIDDEN", "Anda tidak memiliki hak untuk mengubah jenis pekerjaan divisi lain.", status=403
            )
        target_division = data.division_id or existing.division_id
        if creator_division_id is not None and target_division and str(target_division) != str(creator_division_id):
            raise AppError(
                "FORBIDDEN", "Anda tidak memiliki hak untuk memindahkan jenis pekerjaan ke divisi lain.", status=403
            )
        name, photos = self._clean(data)
        if await self.repo.name_taken(org_id, target_division, name, type_id):
            raise AppError("DUPLICATE", "Jenis pekerjaan dengan nama itu sudah ada di divisi ini.", status=409)
        await self._check_examples(org_id, photos)
        await self.repo.update_type(type_id, name, target_division, data.description, True)
        await self.repo.replace_photos(org_id, type_id, photos)
        return await self.get(org_id, type_id)

    async def deactivate(self, org_id: str, type_id: UUID, creator_division_id: UUID | None = None) -> None:
        existing = await self.get(org_id, type_id)
        if creator_division_id is not None and str(existing.division_id) != str(creator_division_id):
            raise AppError(
                "FORBIDDEN", "Anda tidak memiliki hak untuk menonaktifkan jenis pekerjaan divisi lain.", status=403
            )
        await self.repo.update_type(type_id, existing.name, is_active=False)

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

    async def list_default_materials(self, org_id: str, type_id: UUID) -> list[Any]:
        """Daftar template material default untuk satu jenis pekerjaan."""
        await self.get(org_id, type_id)
        return await self.repo.list_default_materials(type_id)

    async def create_default_material(
        self,
        org_id: str,
        type_id: UUID,
        data: DefaultMaterialIn,
        creator_division_id: UUID | None = None,
    ) -> Any:
        """Membuat item template material default."""
        existing = await self.get(org_id, type_id)
        if creator_division_id is not None and str(existing.division_id) != str(creator_division_id):
            raise AppError(
                "FORBIDDEN", "Anda tidak memiliki hak untuk mengelola template material divisi lain.", status=403
            )
        mat_id = await self.repo.create_default_material(type_id, data.model_dump())
        return await self.repo.get_default_material(UUID(mat_id))

    async def update_default_material(
        self,
        org_id: str,
        material_id: UUID,
        data: DefaultMaterialUpdate,
        creator_division_id: UUID | None = None,
    ) -> Any:
        """Mengubah item template material default."""
        mat = await self.repo.get_default_material(material_id)
        if not mat:
            raise NotFoundError("Template Material")
        existing_wt = await self.get(org_id, UUID(str(mat.work_type_id)))
        if creator_division_id is not None and str(existing_wt.division_id) != str(creator_division_id):
            raise AppError(
                "FORBIDDEN", "Anda tidak memiliki hak untuk mengelola template material divisi lain.", status=403
            )
        await self.repo.update_default_material(material_id, data.model_dump(exclude_unset=True))
        return await self.repo.get_default_material(material_id)

    async def delete_default_material(
        self,
        org_id: str,
        material_id: UUID,
        creator_division_id: UUID | None = None,
    ) -> None:
        """Menghapus item template material default."""
        mat = await self.repo.get_default_material(material_id)
        if not mat:
            raise NotFoundError("Template Material")
        existing_wt = await self.get(org_id, UUID(str(mat.work_type_id)))
        if creator_division_id is not None and str(existing_wt.division_id) != str(creator_division_id):
            raise AppError(
                "FORBIDDEN", "Anda tidak memiliki hak untuk mengelola template material divisi lain.", status=403
            )
        await self.repo.delete_default_material(material_id)
