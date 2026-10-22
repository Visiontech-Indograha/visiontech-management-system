"""
app/modules/work_types/controllers/work_type_controller.py

Controller orkestrasi use case jenis pekerjaan dan template foto laporan.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import Depends

from app.modules.work_types.dependencies import get_work_type_service
from app.modules.work_types.schemas.work_type_schema import (
    DefaultMaterialIn,
    DefaultMaterialOut,
    DefaultMaterialUpdate,
    WorkTypeIn,
    WorkTypeOut,
    WorkTypePhotoOut,
)
from app.modules.work_types.services.work_type_service import WorkTypeService


class WorkTypeController:
    """
    Controller use case manajemen jenis pekerjaan dan template foto bukti.
    """

    def __init__(self, service: WorkTypeService = Depends(get_work_type_service)) -> None:
        self.service = service

    @staticmethod
    def map_row_to_out(row: Any) -> WorkTypeOut:
        """Memetakan hasil query ke model WorkTypeOut."""
        return WorkTypeOut(**row._mapping)

    async def get_user_divisions(self, user_id: UUID | str) -> list[UUID]:
        """Mendapatkan divisi karyawan yang terikat pada akun pengguna."""
        return await self.service.repo.get_user_divisions(user_id)

    async def handle_list_types(
        self, organization_id: str, include_inactive: bool, division_ids: list[UUID] | None = None
    ) -> list[WorkTypeOut]:
        """Mengambil seluruh jenis pekerjaan milik organisasi atau divisi tertentu."""
        rows = await self.service.list_types(organization_id, include_inactive, division_ids)
        return [self.map_row_to_out(r) for r in rows]

    async def handle_create(
        self, organization_id: str, data: WorkTypeIn, allowed_divisions: list[UUID] | None = None
    ) -> WorkTypeOut:
        """Membuat jenis pekerjaan baru beserta template foto."""
        row = await self.service.create(organization_id, data, allowed_divisions)
        return self.map_row_to_out(row)

    async def handle_update(
        self, organization_id: str, type_id: UUID, data: WorkTypeIn, allowed_divisions: list[UUID] | None = None
    ) -> WorkTypeOut:
        """Mengubah jenis pekerjaan dan memperbarui slot foto."""
        row = await self.service.update(organization_id, type_id, data, allowed_divisions)
        return self.map_row_to_out(row)

    async def handle_deactivate(
        self, organization_id: str, type_id: UUID, allowed_divisions: list[UUID] | None = None
    ) -> None:
        """Menonaktifkan jenis pekerjaan."""
        await self.service.deactivate(organization_id, type_id, allowed_divisions)

    async def handle_template_of_daily(self, daily_plan_id: UUID) -> list[WorkTypePhotoOut]:
        """Template foto SOP untuk item-item jadwal harian."""
        rows = await self.service.template_of_daily(daily_plan_id)
        return [WorkTypePhotoOut(**r._mapping) for r in rows]

    async def handle_list_materials(self, organization_id: str, type_id: UUID) -> list[DefaultMaterialOut]:
        """Mengambil daftar template material default untuk jenis pekerjaan tertentu."""
        rows = await self.service.list_default_materials(organization_id, type_id)
        return [DefaultMaterialOut(**r._mapping) for r in rows]

    async def handle_create_material(
        self,
        organization_id: str,
        type_id: UUID,
        data: DefaultMaterialIn,
        allowed_divisions: list[UUID] | None = None,
    ) -> DefaultMaterialOut:
        """Membuat template material default baru untuk jenis pekerjaan."""
        row = await self.service.create_default_material(organization_id, type_id, data, allowed_divisions)
        return DefaultMaterialOut(**row._mapping)

    async def handle_update_material(
        self,
        organization_id: str,
        material_id: UUID,
        data: DefaultMaterialUpdate,
        allowed_divisions: list[UUID] | None = None,
    ) -> DefaultMaterialOut:
        """Mengubah template material default."""
        row = await self.service.update_default_material(organization_id, material_id, data, allowed_divisions)
        return DefaultMaterialOut(**row._mapping)

    async def handle_delete_material(
        self,
        organization_id: str,
        material_id: UUID,
        allowed_divisions: list[UUID] | None = None,
    ) -> None:
        """Menghapus template material default."""
        await self.service.delete_default_material(organization_id, material_id, allowed_divisions)
