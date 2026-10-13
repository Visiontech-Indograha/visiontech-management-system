"""
app/modules/work_types/controllers/work_type_controller.py

Controller orkestrasi use case jenis pekerjaan dan template foto laporan.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import Depends

from app.api.deps import get_work_type_service
from app.modules.work_types.schemas.work_type_schema import WorkTypeIn, WorkTypeOut, WorkTypePhotoOut
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

    async def handle_list_types(self, organization_id: str, include_inactive: bool) -> list[WorkTypeOut]:
        """Mengambil seluruh jenis pekerjaan milik organisasi."""
        rows = await self.service.list_types(organization_id, include_inactive)
        return [self.map_row_to_out(r) for r in rows]

    async def handle_create(self, organization_id: str, data: WorkTypeIn) -> WorkTypeOut:
        """Membuat jenis pekerjaan baru beserta template foto."""
        row = await self.service.create(organization_id, data)
        return self.map_row_to_out(row)

    async def handle_update(self, organization_id: str, type_id: UUID, data: WorkTypeIn) -> WorkTypeOut:
        """Mengubah jenis pekerjaan dan memperbarui slot foto."""
        row = await self.service.update(organization_id, type_id, data)
        return self.map_row_to_out(row)

    async def handle_deactivate(self, organization_id: str, type_id: UUID) -> None:
        """Menonaktifkan jenis pekerjaan."""
        await self.service.deactivate(organization_id, type_id)

    async def handle_template_of_plan(self, plan_id: UUID, day_id: UUID | None) -> list[WorkTypePhotoOut]:
        """Mengambil template foto laporan rencana kerja."""
        rows = await self.service.template_of_plan(plan_id, day_id)
        return [WorkTypePhotoOut(**r._mapping) for r in rows]

