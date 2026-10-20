"""
app/modules/units/controllers/unit_controller.py

Controller orkestrasi operasi unit kerja organisasi.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""

from fastapi import Depends

from app.modules.units.dependencies import get_unit_service
from app.modules.units.schemas.unit_schema import UnitOut
from app.modules.units.services.unit_service import UnitService


class UnitController:
    """
    Controller use case daftar dan detail unit organisasi.
    """

    def __init__(self, unit_service: UnitService = Depends(get_unit_service)) -> None:
        self.unit_service = unit_service

    async def handle_list_units(self, organization_id: str) -> list[UnitOut]:
        """Mengambil seluruh unit milik organisasi pengguna."""
        rows = await self.unit_service.list_units(organization_id)
        return [UnitOut(**r._mapping) for r in rows]
