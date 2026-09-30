"""Lokasi penugasan SK: cari kota → tetapkan titik koordinat & radius absensi (revisi PM 2026-09-26)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, PlanAccess, PlanNeed, get_db_with_user, plan_access, require_permission
from app.core.permissions import Permission
from app.schemas.plan_location import GeoResult, PlanLocationIn, PlanLocationOut
from app.services.geocode_service import GeocodeService
from app.services.plan_location_service import PlanLocationService

router = APIRouter(tags=["Plan Location"])
_VIEW = Depends(plan_access(PlanNeed.VIEW))
_PM_UNIT = Depends(plan_access(PlanNeed.PM_UNIT))








@router.get("/geo/search", response_model=list[GeoResult])
async def geo_search(q: str = Query(min_length=1, max_length=120),
                     _: CurrentUser = Depends(require_permission(Permission.CREATE_PLAN))) -> list[GeoResult]:
    """Cari kota/tempat di Indonesia (Nominatim, di-cache). Hanya pengelola SK."""
    return [GeoResult(**r) for r in await GeocodeService().search(q)]


@router.get("/work-plans/{plan_id}/location", response_model=PlanLocationOut | None)
async def get_plan_location(access: PlanAccess = _VIEW,
                            db: AsyncSession = Depends(get_db_with_user)) -> PlanLocationOut | None:
    row = await PlanLocationService(db).location(access)
    return None if row is None else PlanLocationOut(**row)


@router.put("/work-plans/{plan_id}/location", response_model=PlanLocationOut)
async def set_plan_location(data: PlanLocationIn,
                            access: PlanAccess = _PM_UNIT,
                            db: AsyncSession = Depends(get_db_with_user)) -> PlanLocationOut:
    """SK draf maupun berjalan; teks lokasi dokumen tetap, hanya titik absensi yang berubah."""
    row = await PlanLocationService(db).set_location(
        access, name=data.name, address=data.address, lat=data.lat, lng=data.lng, radius_m=data.radius_m)
    return PlanLocationOut(**row)
