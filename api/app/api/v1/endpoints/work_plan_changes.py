"""
Adendum SK — perpanjangan & personel (V-22, dok 05 §3.4). Tipis: aturan di
services/plan_change_service.py, SQL di repositories/plan_change_repo.py.

Sebelumnya: `/plans/{id}/changes/extension` + `/{change_id}/approve` yang langsung MENERAPKAN
perubahan saat PM menyetujui — tanpa penerimaan ketua, tanpa dokumen adendum, dan PERSONNEL tidak
pernah bisa diajukan lewat API.
"""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_db_with_user
from app.schemas.plan_change import ChangeRequest, ChangeResponse, DecisionRequest
from app.services.plan_change_service import PlanChangeService

plan_router = APIRouter(prefix="/work-plans/{plan_id}/changes", tags=["Plan Changes / Addendums"])
router = APIRouter(prefix="/changes", tags=["Plan Changes / Addendums"])








async def _read(db: AsyncSession, change_id: Any) -> ChangeResponse:
    return ChangeResponse(**(await PlanChangeService(db).read(change_id))._mapping)


@plan_router.post("", response_model=ChangeResponse, status_code=status.HTTP_201_CREATED)
async def request_change(
    plan_id: UUID,
    data: ChangeRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user),
) -> ChangeResponse:
    """REQUEST_CHANGE (ketua, perpanjangan) · REQUEST_PERSONNEL_CHANGE (PM unit/OPS, personel)."""
    service = PlanChangeService(db)
    if data.type == "EXTEND":
        change_id = await service.request_change(plan_id, current_user, data.new_period_end, data.reason)
    else:
        change_id = await service.request_personnel_change(
            plan_id, current_user, data.leader_employee_id, data.member_employee_ids, data.reason)
    return await _read(db, change_id)


@router.post("/{change_id}/approve", response_model=ChangeResponse)
async def approve_change(
    change_id: UUID,
    data: DecisionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user),
) -> ChangeResponse:
    """APPROVE_CHANGE — PM unit/OPS menandatangani perpanjangan."""
    return await _read(db, await PlanChangeService(db).approve_change(change_id, current_user))


@router.post("/{change_id}/accept", response_model=ChangeResponse)
async def accept_change(
    change_id: UUID,
    data: DecisionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user),
) -> ChangeResponse:
    """ACCEPT_CHANGE — ketua (perpanjangan) / ketua baru (personel) mengaktifkan adendum."""
    return await _read(db, await PlanChangeService(db).accept_change(change_id, current_user))


@router.post("/{change_id}/reject", response_model=ChangeResponse)
async def reject_change(
    change_id: UUID,
    data: DecisionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user),
) -> ChangeResponse:
    """REJECT_CHANGE — alasan wajib."""
    return await _read(db, await PlanChangeService(db).reject_change(change_id, current_user, data.reason))


@router.post("/{change_id}/withdraw", response_model=ChangeResponse)
async def withdraw_change(
    change_id: UUID,
    data: DecisionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user),
) -> ChangeResponse:
    """WITHDRAW_CHANGE — PM menarik adendum personel."""
    return await _read(db, await PlanChangeService(db).withdraw_change(change_id, current_user, data.reason))
