"""
app/modules/work_plans/controllers/work_plan_location_controller.py

Controller orkestrasi use case pencarian lokasi geospasial dan penetapan titik absensi SK.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""
from __future__ import annotations

from fastapi import Depends

from app.api.deps import get_plan_location_service
from app.modules.work_plans.schemas.work_plan_schema import (
    GeoResult,
    PlanLocationIn,
    PlanLocationOut,
)
from app.modules.work_plans.services.work_plan_service import (
    GeocodeService,
    PlanLocationService,
)
from app.services.access_service import PlanAccess


class WorkPlanLocationController:
    """Controller pencarian kota/tempat (Nominatim) dan konfigurasi titik absensi penugasan SK."""

    def __init__(
        self,
        plan_location_service: PlanLocationService = Depends(get_plan_location_service),
    ) -> None:
        self.service = plan_location_service

    async def handle_geo_search(
        self,
        q: str,
    ) -> list[GeoResult]:
        """Pencarian nama tempat atau wilayah geospasial di Indonesia."""
        return [GeoResult(**r) for r in await GeocodeService().search(q)]

    async def handle_get_location(
        self,
        access: PlanAccess,
    ) -> PlanLocationOut | None:
        """Mengambil data koordinat dan radius titik absensi rencana kerja."""
        row = await self.service.location(access)
        return None if row is None else PlanLocationOut(**row)

    async def handle_set_location(
        self,
        access: PlanAccess,
        data: PlanLocationIn,
    ) -> PlanLocationOut:
        """Menyetel atau memperbarui titik absensi lokasi kerja."""
        row = await self.service.set_location(
            access,
            name=data.name,
            address=data.address,
            lat=data.lat,
            lng=data.lng,
            radius_m=data.radius_m,
            reason=data.reason,
        )
        return PlanLocationOut(**row)


__all__ = ["WorkPlanLocationController"]

