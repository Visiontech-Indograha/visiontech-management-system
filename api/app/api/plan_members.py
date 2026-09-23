"""
Susunan tim SK draft (V-05). Tipis: aturan di services/plan_member_service.py, SQL di
repositories/plan_member_repo.py; transaksi dibuka dependency sesi (get_db).
"""
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db_with_user, require_permission
from app.core.permissions import Permission
from app.repositories.plan_member_repo import PlanMemberRepo
from app.services.plan_member_service import PlanMemberService

router = APIRouter(prefix="/plans/{plan_id}", tags=["Plan Members"])


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
    current_user: CurrentUser = Depends(require_permission(Permission.CREATE_PLAN)),
    db: AsyncSession = Depends(get_db_with_user),
) -> TeamResponse:
    team = await PlanMemberService(PlanMemberRepo(db)).set_team(
        current_user.organization_id, plan_id, payload.leader_employee_id,
        payload.member_employee_ids, payload.row_version,
    )
    return TeamResponse(leader_employee_id=team.leader_employee_id,
                        member_employee_ids=team.member_employee_ids, row_version=team.row_version)
