"""
Transisi SK: terbitkan (PM unit/OPS), terima & mulai (ketua menurut SK) — dijaga `plan_access`
(V-07). Tipis (dok 12 §2): aturan di services/plan_transition_service.py, SQL di
repositories/plan_transition_repo.py.
"""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.api.guards import PlanAccess, PlanNeed, plan_access
from app.repositories.plan_member_repo import PlanMemberRepo
from app.repositories.plan_transition_repo import PlanTransitionRepo
from app.schemas.plan import WorkPlanResponse
from app.services.plan_transition_service import PlanTransitionService

router = APIRouter(prefix="/work-plans/{plan_id}", tags=["Work Plan Transitions"])
_LEADER_ACCESS = Depends(plan_access(PlanNeed.LEADER))
_PM_UNIT_ACCESS = Depends(plan_access(PlanNeed.PM_UNIT))


class TransitionRequest(BaseModel):
    row_version: int
    reason: str = ""


def _service(db: AsyncSession) -> PlanTransitionService:
    return PlanTransitionService(PlanTransitionRepo(db), PlanMemberRepo(db))


def _response(row: Any) -> WorkPlanResponse:
    return WorkPlanResponse(**row._mapping)


@router.post("/publish", response_model=WorkPlanResponse)
async def publish_plan(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _PM_UNIT_ACCESS,
    db: AsyncSession = Depends(get_db_with_user),
) -> WorkPlanResponse:
    plan = await _service(db).publish(plan_id, access.user.organization_id, access.user.user_id, data.row_version)
    return _response(plan)


@router.post("/accept", response_model=WorkPlanResponse)
async def accept_plan(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _LEADER_ACCESS,
    db: AsyncSession = Depends(get_db_with_user),
) -> WorkPlanResponse:
    plan = await _service(db).accept(plan_id, access.user.organization_id, access.user.user_id, data.row_version)
    return _response(plan)


@router.post("/start", response_model=WorkPlanResponse)
async def start_plan(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _LEADER_ACCESS,
    db: AsyncSession = Depends(get_db_with_user),
) -> WorkPlanResponse:
    plan = await _service(db).start(plan_id, access.user.organization_id, access.user.user_id, data.row_version)
    return _response(plan)
