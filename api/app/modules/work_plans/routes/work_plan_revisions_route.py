"""
app/modules/work_plans/routes/work_plan_revisions_route.py

Rute endpoint HTTP untuk revisi rencana kerja oleh PM (/work-plans/{plan_id}).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import plan_access
from app.modules.work_plans.controllers.work_plan_revisions_controller import (
    WorkPlanRevisionsController,
)
from app.modules.work_plans.schemas.work_plan_schema import (
    PlanDetailOut,
    PlanRevisionIn,
    PlanRevisionOut,
)
from app.services.access_service import PlanAccess, PlanNeed

router = APIRouter(prefix="/work-plans/{plan_id}", tags=["Work Plan Revisions"])
_VIEW = Depends(plan_access(PlanNeed.VIEW))
_PM_UNIT = Depends(plan_access(PlanNeed.PM_UNIT))


@router.post("/revisions", response_model=PlanDetailOut)
async def revise_plan(
    plan_id: UUID,
    data: PlanRevisionIn,
    access: PlanAccess = _PM_UNIT,
    controller: WorkPlanRevisionsController = Depends(),
) -> PlanDetailOut:
    """PM unit/OPS merevisi rencana kerja berstatus Terbit, Revisi diminta, Diterima, atau Berjalan (POST)."""
    return await controller.handle_revise_plan(access, data)


@router.get("/revisions", response_model=list[PlanRevisionOut])
async def list_revisions(
    plan_id: UUID,
    access: PlanAccess = _VIEW,
    controller: WorkPlanRevisionsController = Depends(),
) -> list[PlanRevisionOut]:
    """Riwayat revisi rencana kerja, terbaru dulu (GET); siapa pun yang berhak melihat rencana kerja."""
    return await controller.handle_list_revisions(plan_id)


__all__ = ["router"]

