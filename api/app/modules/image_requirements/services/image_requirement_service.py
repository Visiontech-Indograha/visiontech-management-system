"""
app/modules/image_requirements/services/image_requirement_service.py
Service logika bisnis untuk persyaratan foto dokumentasi jenis pekerjaan.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.core.errors import NotFoundError
from app.modules.image_requirements.repositories.image_requirement_repository import ImageRequirementRepository
from app.modules.image_requirements.schemas.image_requirement_schema import (
    ImageRequirementCreate,
    ImageRequirementUpdate,
)


class ImageRequirementService:
    """Service use case persyaratan foto lapangan."""

    def __init__(self, db: AsyncSession = Depends(get_db_with_user)) -> None:
        self.repo = ImageRequirementRepository(db)

    async def list_by_work_type(self, work_type_id: UUID) -> Sequence[Any]:
        return await self.repo.list_by_work_type(work_type_id)

    async def get_by_id(self, requirement_id: UUID) -> Any:
        record = await self.repo.get_by_id(requirement_id)
        if not record:
            raise NotFoundError("Persyaratan foto tidak ditemukan.")
        return record

    async def create_requirement(self, data: ImageRequirementCreate) -> Any:
        return await self.repo.create_requirement(data)

    async def update_requirement(self, requirement_id: UUID, data: ImageRequirementUpdate) -> Any:
        record = await self.repo.update_requirement(requirement_id, data)
        if not record:
            raise NotFoundError("Persyaratan foto tidak ditemukan.")
        return record

    async def delete_requirement(self, requirement_id: UUID) -> None:
        await self.repo.delete_requirement(requirement_id)
