"""
app/modules/sites/controllers/site_controller.py

Controller orkestrasi use case lokasi kerja.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import Depends

from app.core.security import CurrentUser
from app.modules.sites.dependencies import get_site_service
from app.modules.sites.schemas.site_schema import GeoPoint, SiteCreate, SiteResponse
from app.modules.sites.services.site_service import SiteService


class SiteController:
    """
    Controller use case manajemen lokasi kerja organisasi.
    """

    def __init__(self, site_service: SiteService = Depends(get_site_service)) -> None:
        self.site_service = site_service

    @staticmethod
    def map_row_to_response(r: Any, can_manage: bool = False) -> SiteResponse:
        """Memetakan data row database ke model SiteResponse."""
        return SiteResponse(
            id=r.id,
            name=r.name,
            address=r.address,
            radius_m=r.radius_m or 50,
            unit_id=r.unit_id,
            can_manage=can_manage,
            location=GeoPoint(lat=r.lat, lng=r.lng),
        )

    async def handle_list_sites(self, current_user: CurrentUser, for_attendance: bool) -> list[SiteResponse]:
        """Mengambil daftar lokasi yang dapat diakses pengguna."""
        manager, unit = await self.site_service.manageable(current_user)
        rows = await self.site_service.list_sites(current_user, for_attendance=for_attendance)
        return [self.map_row_to_response(r, manager and r.unit_id == unit) for r in rows]

    async def handle_create_site(self, current_user: CurrentUser, data: SiteCreate) -> SiteResponse:
        """Membuat lokasi kerja baru."""
        row = await self.site_service.create_site(
            current_user,
            name=data.name,
            address=data.address,
            radius_m=data.radius_m,
            lat=data.location.lat,
            lng=data.location.lng,
        )
        return self.map_row_to_response(row, True)

    async def handle_delete_site(self, current_user: CurrentUser, site_id: UUID) -> dict[str, str]:
        """Menghapus lokasi kerja."""
        await self.site_service.delete_site(current_user, site_id)
        return {"message": "Lokasi dihapus."}
