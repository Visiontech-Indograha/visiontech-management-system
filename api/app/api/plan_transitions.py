"""
Transisi SK: terbitkan (PM), terima & mulai (ketua menurut SK). Tipis (dok 12 §2): aturan di
services/plan_transition_service.py, SQL di repositories/plan_transition_repo.py.
"""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_db_with_user, require_permission
from app.core.permissions import Permission
from app.repositories.plan_member_repo import PlanMemberRepo
from app.repositories.plan_transition_repo import PlanTransitionRepo
from app.schemas.plan import WorkPlanResponse
from app.services.plan_transition_service import PlanTransitionService

router = APIRouter(prefix="/plans/{plan_id}", tags=["Work Plan Transitions"])


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
    current_user: CurrentUser = Depends(require_permission(Permission.PUBLISH_PLAN)),
    db: AsyncSession = Depends(get_db_with_user),
) -> WorkPlanResponse:
    plan = await _service(db).publish(plan_id, current_user.organization_id, current_user.user_id, data.row_version)
    return _response(plan)


@router.post("/accept", response_model=WorkPlanResponse)
async def accept_plan(
    plan_id: UUID,
    data: TransitionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user),
) -> WorkPlanResponse:
    plan = await _service(db).accept(plan_id, current_user.organization_id, current_user.user_id, data.row_version)
    return _response(plan)


@router.post("/start", response_model=WorkPlanResponse)
async def start_plan(
    plan_id: UUID,
    data: TransitionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user),
) -> WorkPlanResponse:
    plan = await _service(db).start(plan_id, current_user.organization_id, current_user.user_id, data.row_version)
    return _response(plan)
