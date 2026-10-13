"""
app/modules/work_plans/routes/work_plan_members_route.py

Rute endpoint HTTP untuk susunan tim SK (/work-plans/{plan_id}/members).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import plan_access
from app.modules.work_plans.controllers.work_plan_members_controller import (
    WorkPlanMembersController,
)
from app.modules.work_plans.schemas.work_plan_schema import (
    TeamMemberOut,
    TeamRequest,
    TeamResponse,
)
from app.services.access_service import PlanAccess, PlanNeed

router = APIRouter(prefix="/work-plans/{plan_id}", tags=["Plan Members"])
_PM_UNIT_ACCESS = Depends(plan_access(PlanNeed.PM_UNIT))
_VIEW_ACCESS = Depends(plan_access(PlanNeed.VIEW))


@router.get("/members", response_model=list[TeamMemberOut])
async def get_plan_team(
    plan_id: UUID,
    access: PlanAccess = _VIEW_ACCESS,
    controller: WorkPlanMembersController = Depends(),
) -> list[TeamMemberOut]:
    """Mengambil daftar tim aktif pada rencana kerja (GET)."""
    return await controller.handle_get_team(plan_id)


@router.put("/members", response_model=TeamResponse)
async def set_plan_team(
    plan_id: UUID,
    payload: TeamRequest,
    access: PlanAccess = _PM_UNIT_ACCESS,
    controller: WorkPlanMembersController = Depends(),
) -> TeamResponse:
    """Menyetel (memperbarui) daftar tim SK (ketua dan anggota) (PUT)."""
    return await controller.handle_set_team(access, plan_id, payload)


__all__ = ["router"]

