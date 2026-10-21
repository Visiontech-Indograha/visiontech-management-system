"""Controller jabatan."""
from __future__ import annotations

from datetime import date  # noqa: F401
from typing import Any  # noqa: F401
from uuid import UUID

from fastapi import Depends

from app.core.security import CurrentUser
from app.modules.job_positions.dependencies import get_job_position_service
from app.modules.job_positions.schemas.job_position_schema import JobPositionCreate, JobPositionOut, JobPositionUpdate
from app.modules.job_positions.services.job_position_service import JobPositionService


class JobPositionController:
    def __init__(self, service: JobPositionService = Depends(get_job_position_service)) -> None:
        self.service = service

    async def list_all(self, user: CurrentUser, division_id: UUID | None, active_only: bool) -> list[JobPositionOut]:
        return [JobPositionOut(**dict(r._mapping)) for r in await self.service.list(division_id, active_only)]

    async def create(self, user: CurrentUser, data: JobPositionCreate) -> JobPositionOut:
        return JobPositionOut(**dict((await self.service.create(data))._mapping))

    async def update(self, user: CurrentUser, item_id: UUID, data: JobPositionUpdate) -> JobPositionOut:
        return JobPositionOut(**dict((await self.service.update(item_id, data))._mapping))

    async def delete(self, user: CurrentUser, item_id: UUID) -> dict[str, str]:
        await self.service.delete(item_id)
        return {"message": "Jabatan dihapus."}
