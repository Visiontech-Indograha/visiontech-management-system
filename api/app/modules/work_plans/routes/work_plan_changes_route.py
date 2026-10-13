"""
app/modules/work_plans/routes/work_plan_changes_route.py

Rute endpoint HTTP untuk adendum perpanjangan & personel (/work-plans/{plan_id}/changes, /changes).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user
from app.core.security import CurrentUser
from app.modules.work_plans.controllers.work_plan_changes_controller import (
    WorkPlanChangesController,
)
from app.modules.work_plans.schemas.work_plan_schema import (
    ChangeRequest,
    ChangeResponse,
    DecisionRequest,
)

plan_router = APIRouter(prefix="/work-plans/{plan_id}/changes", tags=["Plan Changes / Addendums"])
router = APIRouter(prefix="/changes", tags=["Plan Changes / Addendums"])


@plan_router.post("", response_model=ChangeResponse, status_code=status.HTTP_201_CREATED)
async def request_change(
    plan_id: UUID,
    data: ChangeRequest,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkPlanChangesController = Depends(),
) -> ChangeResponse:
    """Mengajukan adendum perubahan pada SK (POST)."""
    return await controller.handle_request_change(plan_id, current_user, data)


@router.post("/{change_id}/approve", response_model=ChangeResponse)
async def approve_change(
    change_id: UUID,
    data: DecisionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkPlanChangesController = Depends(),
) -> ChangeResponse:
    """Menyetujui adendum perpanjangan SK (POST)."""
    return await controller.handle_approve_change(change_id, current_user, data)


@router.post("/{change_id}/accept", response_model=ChangeResponse)
async def accept_change(
    change_id: UUID,
    data: DecisionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkPlanChangesController = Depends(),
) -> ChangeResponse:
    """Menerima dan mengaktifkan adendum (POST)."""
    return await controller.handle_accept_change(change_id, current_user, data)


@router.post("/{change_id}/reject", response_model=ChangeResponse)
async def reject_change(
    change_id: UUID,
    data: DecisionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkPlanChangesController = Depends(),
) -> ChangeResponse:
    """Menolak adendum (POST)."""
    return await controller.handle_reject_change(change_id, current_user, data)


@router.post("/{change_id}/withdraw", response_model=ChangeResponse)
async def withdraw_change(
    change_id: UUID,
    data: DecisionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkPlanChangesController = Depends(),
) -> ChangeResponse:
    """Menarik kembali usulan adendum personel (POST)."""
    return await controller.handle_withdraw_change(change_id, current_user, data)


__all__ = ["plan_router", "router"]

