"""Controller proyek."""
from __future__ import annotations

from datetime import date  # noqa: F401
from typing import Any  # noqa: F401
from uuid import UUID

from fastapi import Depends

from app.core.security import CurrentUser
from app.modules.projects.dependencies import get_project_service
from app.modules.projects.schemas.project_schema import ProjectCreate, ProjectOut, ProjectUpdate
from app.modules.projects.services.project_service import ProjectService


class ProjectController:
    def __init__(self, service: ProjectService = Depends(get_project_service)) -> None:
        self.service = service

    async def list_all(self, user: CurrentUser, division_id: UUID | None, client_id: UUID | None,
                       status: str | None, q: str | None) -> list[ProjectOut]:
        rows = await self.service.list(user, division_id=division_id, client_id=client_id, status=status, q=q)
        return [ProjectOut(**dict(r._mapping)) for r in rows]

    async def create(self, user: CurrentUser, data: ProjectCreate) -> ProjectOut:
        return ProjectOut(**dict((await self.service.create(user, data))._mapping))

    async def update(self, user: CurrentUser, item_id: UUID, data: ProjectUpdate) -> ProjectOut:
        return ProjectOut(**dict((await self.service.update(user, item_id, data))._mapping))

    async def delete(self, user: CurrentUser, item_id: UUID) -> dict[str, str]:
        await self.service.delete(user, item_id)
        return {"message": "Proyek dihapus."}
