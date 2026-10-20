"""
app/modules/units/controllers/unit_controller.py

Controller orkestrasi use case divisi operasional.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""

from uuid import UUID

from fastapi import Depends

from app.modules.units.dependencies import get_unit_service
from app.modules.units.schemas.unit_schema import UnitCreate, UnitOut, UnitUpdate
from app.modules.units.services.unit_service import UnitService


class UnitController:
    """Controller divisi operasional."""

    def __init__(self, unit_service: UnitService = Depends(get_unit_service)) -> None:
        self.unit_service = unit_service

    async def handle_list_units(self, organization_id: str) -> list[UnitOut]:
        rows = await self.unit_service.list_units(organization_id)
        return [UnitOut(**r._mapping) for r in rows]

    async def handle_create_unit(self, data: UnitCreate) -> UnitOut:
        return UnitOut(**(await self.unit_service.create_unit(data))._mapping)

    async def handle_update_unit(self, division_id: UUID, data: UnitUpdate) -> UnitOut:
        return UnitOut(**(await self.unit_service.update_unit(division_id, data))._mapping)

    async def handle_delete_unit(self, division_id: UUID) -> dict[str, str]:
        await self.unit_service.delete_unit(division_id)
        return {"message": "Divisi dihapus."}
