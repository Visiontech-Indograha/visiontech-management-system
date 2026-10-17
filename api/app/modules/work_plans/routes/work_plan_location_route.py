"""
app/modules/work_plans/routes/work_plan_location_route.py

Rute endpoint HTTP untuk lokasi penugasan SK (/geo/search, /work-plans/{plan_id}/location).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from fastapi import APIRouter, Depends, Query

from app.api.deps import plan_access, require_any_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.work_plans.controllers.work_plan_location_controller import (
    WorkPlanLocationController,
)
from app.modules.work_plans.schemas.work_plan_schema import (
    GeoResult,
    PlanLocationIn,
    PlanLocationOut,
)
from app.services.access_service import PlanAccess, PlanNeed

router = APIRouter(tags=["Plan Location"])
_VIEW = Depends(plan_access(PlanNeed.VIEW))
_PM_UNIT = Depends(plan_access(PlanNeed.PM_UNIT))
_GEO_SEARCH = require_any_permission(Permission.CREATE_PLAN, Permission.MANAGE_SITES)


@router.get("/geo/search", response_model=list[GeoResult])
async def geo_search(
    q: str = Query(min_length=1, max_length=120),
    _: CurrentUser = Depends(_GEO_SEARCH),
    controller: WorkPlanLocationController = Depends(),
) -> list[GeoResult]:
    """Pencarian kota/tempat di Indonesia berdasarkan kueri (Nominatim, di-cache) (GET)."""
    return await controller.handle_geo_search(q)


@router.get("/work-plans/{plan_id}/location", response_model=PlanLocationOut | None)
async def get_plan_location(
    access: PlanAccess = _VIEW,
    controller: WorkPlanLocationController = Depends(),
) -> PlanLocationOut | None:
    """Mengambil lokasi titik absensi untuk sebuah rencana kerja (SK) (GET)."""
    return await controller.handle_get_location(access)


@router.put("/work-plans/{plan_id}/location", response_model=PlanLocationOut)
async def set_plan_location(
    data: PlanLocationIn,
    access: PlanAccess = _PM_UNIT,
    controller: WorkPlanLocationController = Depends(),
) -> PlanLocationOut:
    """Menyetel titik absensi (lokasi) untuk rencana kerja (PUT)."""
    return await controller.handle_set_location(access, data)


__all__ = ["router"]
