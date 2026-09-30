"""
Susunan tim SK draft (V-05). Tipis: aturan di services/plan_member_service.py, SQL di
crud/crud_plan_member.py; transaksi dibuka dependency sesi (get_db).
"""
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import PlanAccess, PlanNeed, get_db_with_user, plan_access
from app.crud.crud_plan_member import CRUDPlanMember
from app.schemas.plan_member import TeamMemberOut, TeamRequest, TeamResponse
from app.services.plan_member_service import PlanMemberService

router = APIRouter(prefix="/work-plans/{plan_id}", tags=["Plan Members"])
_PM_UNIT_ACCESS = Depends(plan_access(PlanNeed.PM_UNIT))
_VIEW_ACCESS = Depends(plan_access(PlanNeed.VIEW))




@router.get("/members", response_model=list[TeamMemberOut])
async def get_plan_team(
    plan_id: UUID,
    access: PlanAccess = _VIEW_ACCESS,
    db: AsyncSession = Depends(get_db_with_user),
) -> list[TeamMemberOut]:
    """Tim aktif SK (ketua dulu). SK tak terlihat / organisasi lain → 404 (penjaga VIEW)."""
    rows = await PlanMemberService(CRUDPlanMember(db)).team(plan_id)
    return [TeamMemberOut(**r._mapping) for r in rows]






@router.put("/members", response_model=TeamResponse)
async def set_plan_team(
    plan_id: UUID,
    payload: TeamRequest,
    access: PlanAccess = _PM_UNIT_ACCESS,
    db: AsyncSession = Depends(get_db_with_user),
) -> TeamResponse:
    team = await PlanMemberService(CRUDPlanMember(db)).set_team(
        access.user, plan_id, payload.leader_employee_id,
        payload.member_employee_ids, payload.row_version,
    )
    return TeamResponse(leader_employee_id=team.leader_employee_id,
                        member_employee_ids=team.member_employee_ids, row_version=team.row_version)
