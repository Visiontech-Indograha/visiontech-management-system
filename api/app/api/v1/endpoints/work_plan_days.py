"""Baca hari kerja SK: tugas + laporan harian per hari (untuk layar laporan harian web/mobile)."""
from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_plan_day_service, plan_access
from app.schemas.plan_day import PlanDayOut
from app.services.access_service import PlanAccess, PlanNeed
from app.services.plan_day_service import PlanDayService

router = APIRouter(prefix="/work-plans/{plan_id}/days", tags=["Daily Reports"])
_VIEW_ACCESS = Depends(plan_access(PlanNeed.VIEW))








def _out(row: Any) -> PlanDayOut:
    return PlanDayOut(**row._mapping)


@router.get("", response_model=list[PlanDayOut])
async def list_plan_days(access: PlanAccess = _VIEW_ACCESS,
                         plan_day_service: PlanDayService = Depends(get_plan_day_service)) -> list[PlanDayOut]:
    """Siapa pun yang melihat SK (V-07); SK tak terlihat / organisasi lain → 404."""
    return [_out(row) for row in await plan_day_service.list_days(access)]
