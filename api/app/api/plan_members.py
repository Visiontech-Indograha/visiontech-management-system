"""
Susunan tim SK draft (V-05). Tipis: aturan di services/plan_member_service.py, SQL di
repositories/plan_member_repo.py; transaksi dibuka dependency sesi (get_db).
"""
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.api.guards import PlanAccess, PlanNeed, plan_access
from app.repositories.plan_member_repo import PlanMemberRepo
from app.services.plan_member_service import PlanMemberService

router = APIRouter(prefix="/plans/{plan_id}", tags=["Plan Members"])
_PM_UNIT_ACCESS = Depends(plan_access(PlanNeed.PM_UNIT))


class TeamRequest(BaseModel):
    leader_employee_id: UUID | None = None
    member_employee_ids: list[UUID] = Field(default_factory=list)
    row_version: int


class TeamResponse(BaseModel):
    leader_employee_id: str | None
    member_employee_ids: list[str]
    row_version: int


@router.put("/members", response_model=TeamResponse)
async def set_plan_team(
    plan_id: UUID,
    payload: TeamRequest,
    access: PlanAccess = _PM_UNIT_ACCESS,
    db: AsyncSession = Depends(get_db_with_user),
) -> TeamResponse:
    team = await PlanMemberService(PlanMemberRepo(db)).set_team(
        access.user.organization_id, plan_id, payload.leader_employee_id,
        payload.member_employee_ids, payload.row_version,
    )
    return TeamResponse(leader_employee_id=team.leader_employee_id,
                        member_employee_ids=team.member_employee_ids, row_version=team.row_version)
