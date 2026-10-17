"""
app/modules/work_plans/routes/work_plan_days_route.py

Rute endpoint HTTP untuk membaca hari kerja SK (/work-plans/{plan_id}/days).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from fastapi import APIRouter, Depends

from app.api.deps import plan_access
from app.modules.work_plans.controllers.work_plan_days_controller import (
    WorkPlanDaysController,
)
from app.modules.work_plans.schemas.work_plan_schema import PlanDayOut
from app.services.access_service import PlanAccess, PlanNeed

router = APIRouter(prefix="/work-plans/{plan_id}/days", tags=["Daily Reports"])
_VIEW_ACCESS = Depends(plan_access(PlanNeed.VIEW))


@router.get("", response_model=list[PlanDayOut])
async def list_plan_days(
    access: PlanAccess = _VIEW_ACCESS,
    controller: WorkPlanDaysController = Depends(),
) -> list[PlanDayOut]:
    """Mengambil daftar hari kerja beserta tugas dan laporan harian dari SK (GET)."""
    return await controller.handle_list_days(access)


__all__ = ["router"]
