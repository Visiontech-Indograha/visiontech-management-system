"""
app/modules/offices/controllers/office_controller.py

Controller orkestrasi use case master kantor.
Mengikuti Panduan Standar Arofficektur API FastAPI Modular §4 & §5.2.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import Depends

from app.core.security import CurrentUser
from app.modules.offices.dependencies import get_office_service
from app.modules.offices.schemas.office_schema import GeoPoint, OfficeCreate, OfficeResponse, OfficeUpdate
from app.modules.offices.services.office_service import OfficeService


class OfficeController:
    """Controller master kantor (pusat & cabang)."""

    def __init__(self, office_service: OfficeService = Depends(get_office_service)) -> None:
        self.office_service = office_service

    @staticmethod
    def map_row_to_response(r: Any, can_manage: bool = False) -> OfficeResponse:
        """Baris office → OfficeResponse."""
        return OfficeResponse(
            id=r.id,
            name=r.name,
            address=r.address,
            location=GeoPoint(lat=r.lat, lng=r.lng),
            radius_m=r.radius_m,
            city_boundary_radius_m=r.city_boundary_radius_m,
            clock_in_time=r.clock_in_time,
            clock_out_time=r.clock_out_time,
            in_city_meal_rate=r.in_city_meal_rate,
            out_city_meal_rate=r.out_city_meal_rate,
            is_main_office=r.is_main_office,
            unit_id=r.unit_id,
            can_manage=can_manage,
        )

    async def handle_list_offices(self, current_user: CurrentUser, for_attendance: bool) -> list[OfficeResponse]:
        manage = self.office_service.can_manage(current_user)
        rows = await self.office_service.list_offices(current_user, for_attendance=for_attendance)
        return [self.map_row_to_response(r, manage) for r in rows]

    async def handle_create_office(self, current_user: CurrentUser, data: OfficeCreate) -> OfficeResponse:
        row = await self.office_service.create_office(current_user, data)
        return self.map_row_to_response(row, True)

    async def handle_update_office(
        self, current_user: CurrentUser, office_id: UUID, data: OfficeUpdate
    ) -> OfficeResponse:
        row = await self.office_service.update_office(current_user, office_id, data)
        return self.map_row_to_response(row, True)

    async def handle_delete_office(self, current_user: CurrentUser, office_id: UUID) -> dict[str, str]:
        await self.office_service.delete_office(current_user, office_id)
        return {"message": "Kantor dihapus."}
