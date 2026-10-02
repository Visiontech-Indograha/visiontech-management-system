"""
Susunan tim SK draft (V-05). Tipis: aturan di services/plan_member_service.py, SQL di
crud/crud_plan_member.py; transaksi dibuka dependency sesi (get_db).
"""
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import get_plan_member_service, plan_access
from app.schemas.plan_member import TeamMemberOut, TeamRequest, TeamResponse
from app.services.access_service import PlanAccess, PlanNeed
from app.services.plan_member_service import PlanMemberService

router = APIRouter(prefix="/work-plans/{plan_id}", tags=["Plan Members"])
_PM_UNIT_ACCESS = Depends(plan_access(PlanNeed.PM_UNIT))
_VIEW_ACCESS = Depends(plan_access(PlanNeed.VIEW))




@router.get("/members", response_model=list[TeamMemberOut])
async def get_plan_team(
    plan_id: UUID,
    access: PlanAccess = _VIEW_ACCESS,
    plan_member_service: PlanMemberService = Depends(get_plan_member_service),
) -> list[TeamMemberOut]:
    """Tim aktif SK (ketua dulu). SK tak terlihat / organisasi lain → 404 (penjaga VIEW)."""
    rows = await plan_member_service.team(plan_id)
    return [TeamMemberOut(**r._mapping) for r in rows]






@router.put("/members", response_model=TeamResponse)
async def set_plan_team(
    plan_id: UUID,
    payload: TeamRequest,
    access: PlanAccess = _PM_UNIT_ACCESS,
    plan_member_service: PlanMemberService = Depends(get_plan_member_service),
) -> TeamResponse:
    team = await plan_member_service.set_team(
        access.user, plan_id, payload.leader_employee_id,
        payload.member_employee_ids, payload.row_version,
    )
    return TeamResponse(leader_employee_id=team.leader_employee_id,
                        member_employee_ids=team.member_employee_ids, row_version=team.row_version)
