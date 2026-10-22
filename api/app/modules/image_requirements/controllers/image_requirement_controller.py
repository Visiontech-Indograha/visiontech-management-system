"""
app/modules/image_requirements/controllers/image_requirement_controller.py
Controller orkestrasi use case persyaratan foto dokumentasi jenis pekerjaan.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import Depends

from app.core.security import CurrentUser
from app.modules.image_requirements.dependencies import get_image_requirement_service
from app.modules.image_requirements.schemas.image_requirement_schema import (
    ImageRequirementCreate,
    ImageRequirementOut,
    ImageRequirementUpdate,
)
from app.modules.image_requirements.services.image_requirement_service import ImageRequirementService


class ImageRequirementController:
    """Controller pengelolaan persyaratan foto dokumentasi jenis pekerjaan."""

    def __init__(self, service: ImageRequirementService = Depends(get_image_requirement_service)) -> None:
        self.service = service

    async def handle_list_by_work_type(
        self,
        current_user: CurrentUser,
        work_type_id: UUID,
    ) -> list[ImageRequirementOut]:
        rows = await self.service.list_by_work_type(work_type_id)
        return [ImageRequirementOut(**dict(r._mapping)) for r in rows]

    async def handle_get_by_id(
        self,
        current_user: CurrentUser,
        requirement_id: UUID,
    ) -> ImageRequirementOut:
        row = await self.service.get_by_id(requirement_id)
        return ImageRequirementOut(**dict(row._mapping))

    async def handle_create(
        self,
        current_user: CurrentUser,
        data: ImageRequirementCreate,
    ) -> ImageRequirementOut:
        row = await self.service.create_requirement(data)
        return ImageRequirementOut(**dict(row._mapping))

    async def handle_update(
        self,
        current_user: CurrentUser,
        requirement_id: UUID,
        data: ImageRequirementUpdate,
    ) -> ImageRequirementOut:
        row = await self.service.update_requirement(requirement_id, data)
        return ImageRequirementOut(**dict(row._mapping))

    async def handle_delete(
        self,
        current_user: CurrentUser,
        requirement_id: UUID,
    ) -> dict[str, str]:
        await self.service.delete_requirement(requirement_id)
        return {"message": "Persyaratan foto berhasil dihapus."}
