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
from app.shared.access.access_service import ensure_same_org


class WorkTypeService:
    """Aturan jenis pekerjaan: nama unik per organisasi, label slot tidak boleh kembar, hapus = nonaktifkan."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = CRUDWorkType(db)

    async def list_types(
        self, org_id: str, include_inactive: bool, division_ids: list[UUID] | None = None
    ) -> list[Any]:
        return await self.repo.list_types(org_id, include_inactive, division_ids)

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

    async def create(self, org_id: str, data: WorkTypeIn, allowed_divisions: list[UUID] | None = None) -> Any:
        division_id = data.division_id or (
            allowed_divisions[0] if allowed_divisions is not None and len(allowed_divisions) == 1 else None)
        if allowed_divisions is not None and data.division_id and str(data.division_id) not in {
            str(d) for d in allowed_divisions}:
            raise AppError(
                "FORBIDDEN", "Anda tidak memiliki hak untuk membuat jenis pekerjaan di divisi lain.", status=403
            )
        if division_id is None:
            raise ValidationError("Divisi wajib ditentukan untuk jenis pekerjaan ini.")
        name, photos = self._clean(data)
        if await self.repo.name_taken(org_id, division_id, name, None):
            raise AppError("DUPLICATE", "Jenis pekerjaan dengan nama itu sudah ada di divisi ini.", status=409)
        await self._check_examples(org_id, photos)
        follow_up = await self._check_kind(data, str(division_id), None)
        type_id = await self.repo.insert_type(org_id, division_id, name, data.description, data.kind, follow_up)
        await self.repo.replace_photos(org_id, type_id, photos)
        return await self.get(org_id, UUID(type_id))

    async def update(
        self, org_id: str, type_id: UUID, data: WorkTypeIn, allowed_divisions: list[UUID] | None = None
    ) -> Any:
        existing = await self.get(org_id, type_id)
        if allowed_divisions is not None and str(existing.division_id) not in {str(d) for d in allowed_divisions}:
            raise AppError(
                "FORBIDDEN", "Anda tidak memiliki hak untuk mengubah jenis pekerjaan divisi lain.", status=403
            )
        target_division = data.division_id or existing.division_id
        if allowed_divisions is not None and target_division and str(target_division) not in {
            str(d) for d in allowed_divisions}:
            raise AppError(
                "FORBIDDEN", "Anda tidak memiliki hak untuk memindahkan jenis pekerjaan ke divisi lain.", status=403
            )
        name, photos = self._clean(data)
        if await self.repo.name_taken(org_id, target_division, name, type_id):
            raise AppError("DUPLICATE", "Jenis pekerjaan dengan nama itu sudah ada di divisi ini.", status=409)
        await self._check_examples(org_id, photos)
        await self.repo.update_type(type_id, name, target_division, data.description, True)
        await self.repo.set_kind(type_id, data.kind, await self._check_kind(data, str(target_division), type_id))
        await self.repo.replace_photos(org_id, type_id, photos)
        return await self.get(org_id, type_id)

    async def _check_kind(self, data: WorkTypeIn, division_id: str, self_id: UUID | None) -> UUID | None:
        """Pemasangan lanjutan hanya untuk jenis titik survei, dan harus pekerjaan biasa di divisi yang sama."""
        if data.kind != "SURVEY_POINT" or data.follow_up_work_type_id is None:
            return None
        if self_id and str(data.follow_up_work_type_id) == str(self_id):
            raise ValidationError("Pemasangan lanjutan tidak boleh jenis titik itu sendiri.")
        target = await self.repo.kind_of(data.follow_up_work_type_id)
        allowed_kinds = ("WORK", "INSTALLATION", "MAINTENANCE", "REPLACEMENT")
        if target is None or target[0] not in allowed_kinds or target[1] != division_id:
            raise ValidationError("Pemasangan lanjutan harus jenis pekerjaan biasa (bukan survei) di divisi yang sama.")
        return data.follow_up_work_type_id

    async def deactivate(self, org_id: str, type_id: UUID, allowed_divisions: list[UUID] | None = None) -> None:
        existing = await self.get(org_id, type_id)
        if allowed_divisions is not None and str(existing.division_id) not in {str(d) for d in allowed_divisions}:
            raise AppError(
                "FORBIDDEN", "Anda tidak memiliki hak untuk menonaktifkan jenis pekerjaan divisi lain.", status=403
            )
        await self.repo.update_type(type_id, existing.name, is_active=False)

    async def copy_to_division(
        self,
        org_id: str,
        type_id: UUID,
        target_division_id: UUID,
        allowed_divisions: list[UUID] | None = None,
    ) -> Any:
        """Salin jenis pekerjaan (slot foto + template material default) ke divisi lain sebagai jenis baru.
        Tautan pemasangan lanjutan tidak disalin (bergantung pada divisi asal)."""
        source = await self.get(org_id, type_id)
        if allowed_divisions is not None and str(target_division_id) not in {str(d) for d in allowed_divisions}:
            raise AppError(
                "FORBIDDEN", "Anda tidak memiliki hak untuk membuat jenis pekerjaan di divisi tujuan.", status=403
            )
        if await self.repo.name_taken(org_id, target_division_id, source.name, None):
            raise AppError("DUPLICATE", "Jenis pekerjaan dengan nama itu sudah ada di divisi tujuan.", status=409)
        photos = [
            {
                "label": p["label"],
                "hint": p.get("hint"),
                "required": p.get("required", True),
                "example_file_id": p.get("example_file_id"),
            }
            for p in (source.photos or [])
        ]
        new_id = await self.repo.insert_type(
            org_id, target_division_id, source.name, source.description, source.kind, None
        )
        await self.repo.replace_photos(org_id, new_id, photos)
        for m in await self.repo.list_default_materials(type_id):
            await self.repo.create_default_material(new_id, {
                "material_code": m.material_code,
                "material_name": m.material_name,
                "default_qty": m.default_qty,
                "unit": m.unit,
                "category": m.category,
                "description": m.description,
                "sort_order": m.sort_order,
            })
        return await self.get(org_id, UUID(new_id))

    async def template_of_daily(self, daily_plan_id: UUID) -> list[Any]:
        """Slot foto SOP dari jenis pekerjaan item-item jadwal harian ini."""
        return await self.repo.template_of_daily(daily_plan_id)

    async def list_default_materials(self, org_id: str, type_id: UUID) -> list[Any]:
        """Daftar template material default untuk satu jenis pekerjaan."""
        await self.get(org_id, type_id)
        return await self.repo.list_default_materials(type_id)

    async def create_default_material(
        self,
        org_id: str,
        type_id: UUID,
        data: DefaultMaterialIn,
        allowed_divisions: list[UUID] | None = None,
    ) -> Any:
        """Membuat item template material default."""
        existing = await self.get(org_id, type_id)
        if allowed_divisions is not None and str(existing.division_id) not in {str(d) for d in allowed_divisions}:
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
        allowed_divisions: list[UUID] | None = None,
    ) -> Any:
        """Mengubah item template material default."""
        mat = await self.repo.get_default_material(material_id)
        if not mat:
            raise NotFoundError("Template Material")
        existing_wt = await self.get(org_id, UUID(str(mat.work_type_id)))
        if allowed_divisions is not None and str(existing_wt.division_id) not in {str(d) for d in allowed_divisions}:
            raise AppError(
                "FORBIDDEN", "Anda tidak memiliki hak untuk mengelola template material divisi lain.", status=403
            )
        await self.repo.update_default_material(material_id, data.model_dump(exclude_unset=True))
        return await self.repo.get_default_material(material_id)

    async def delete_default_material(
        self,
        org_id: str,
        material_id: UUID,
        allowed_divisions: list[UUID] | None = None,
    ) -> None:
        """Menghapus item template material default."""
        mat = await self.repo.get_default_material(material_id)
        if not mat:
            raise NotFoundError("Template Material")
        existing_wt = await self.get(org_id, UUID(str(mat.work_type_id)))
        if allowed_divisions is not None and str(existing_wt.division_id) not in {str(d) for d in allowed_divisions}:
            raise AppError(
                "FORBIDDEN", "Anda tidak memiliki hak untuk mengelola template material divisi lain.", status=403
            )
        await self.repo.delete_default_material(material_id)
