"""Baca hari kerja SK: tugas + laporan harian per hari (untuk layar laporan harian web/mobile)."""
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import PlanAccess, PlanNeed, get_db_with_user, plan_access
from app.schemas.plan_day import PlanDayOut
from app.services.plan_day_service import PlanDayService

router = APIRouter(prefix="/work-plans/{plan_id}/days", tags=["Daily Reports"])
_VIEW_ACCESS = Depends(plan_access(PlanNeed.VIEW))








def _out(row: Any) -> PlanDayOut:
    return PlanDayOut(**row._mapping)


@router.get("", response_model=list[PlanDayOut])
async def list_plan_days(access: PlanAccess = _VIEW_ACCESS,
                         db: AsyncSession = Depends(get_db_with_user)) -> list[PlanDayOut]:
    """Siapa pun yang melihat SK (V-07); SK tak terlihat / organisasi lain → 404."""
    return [_out(row) for row in await PlanDayService(db).list_days(access)]
