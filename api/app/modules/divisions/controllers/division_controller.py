"""
app/modules/divisions/controllers/division_controller.py

Controller orkestrasi use case divisi operasional.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""

from uuid import UUID

from fastapi import Depends

from app.modules.divisions.dependencies import get_division_service
from app.modules.divisions.schemas.division_schema import DivisionCreate, DivisionOut, DivisionUpdate
from app.modules.divisions.services.division_service import DivisionService


class DivisionController:
    """Controller divisi operasional."""

    def __init__(self, division_service: DivisionService = Depends(get_division_service)) -> None:
        self.division_service = division_service

    async def handle_list_divisions(self, organization_id: str) -> list[DivisionOut]:
        rows = await self.division_service.list_divisions(organization_id)
        return [DivisionOut(**r._mapping) for r in rows]

    async def handle_create_division(self, data: DivisionCreate) -> DivisionOut:
        return DivisionOut(**(await self.division_service.create_division(data))._mapping)

    async def handle_update_division(self, division_id: UUID, data: DivisionUpdate) -> DivisionOut:
        return DivisionOut(**(await self.division_service.update_division(division_id, data))._mapping)

    async def handle_delete_division(self, division_id: UUID) -> dict[str, str]:
        await self.division_service.delete_division(division_id)
        return {"message": "Divisi dihapus."}
