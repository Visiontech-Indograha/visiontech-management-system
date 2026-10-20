"""
app/modules/sites/controllers/site_controller.py

Controller orkestrasi use case master kantor.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import Depends

from app.core.security import CurrentUser
from app.modules.sites.dependencies import get_site_service
from app.modules.sites.schemas.site_schema import GeoPoint, SiteCreate, SiteResponse, SiteUpdate
from app.modules.sites.services.site_service import SiteService


class SiteController:
    """Controller master kantor (pusat & cabang)."""

    def __init__(self, site_service: SiteService = Depends(get_site_service)) -> None:
        self.site_service = site_service

    @staticmethod
    def map_row_to_response(r: Any, can_manage: bool = False) -> SiteResponse:
        """Baris office → SiteResponse."""
        return SiteResponse(
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

    async def handle_list_sites(self, current_user: CurrentUser, for_attendance: bool) -> list[SiteResponse]:
        manage = self.site_service.can_manage(current_user)
        rows = await self.site_service.list_sites(current_user, for_attendance=for_attendance)
        return [self.map_row_to_response(r, manage) for r in rows]

    async def handle_create_site(self, current_user: CurrentUser, data: SiteCreate) -> SiteResponse:
        row = await self.site_service.create_site(current_user, data)
        return self.map_row_to_response(row, True)

    async def handle_update_site(self, current_user: CurrentUser, site_id: UUID, data: SiteUpdate) -> SiteResponse:
        row = await self.site_service.update_site(current_user, site_id, data)
        return self.map_row_to_response(row, True)

    async def handle_delete_site(self, current_user: CurrentUser, site_id: UUID) -> dict[str, str]:
        await self.site_service.delete_site(current_user, site_id)
        return {"message": "Kantor dihapus."}
