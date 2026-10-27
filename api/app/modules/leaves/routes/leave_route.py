"""
app/modules/leaves/routes/leave_route.py

Rute endpoint HTTP untuk modul cuti & izin karyawan (/leaves).
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_user
from app.core.security import CurrentUser
from app.modules.leaves.controllers.leave_controller import LeaveController
from app.modules.leaves.schemas.leave_schema import (
    LeaveBalanceResponse,
    LeaveCreate,
    LeaveResponse,
    LeaveReview,
)

router = APIRouter(prefix="/leaves", tags=["Leaves"])


@router.post("", response_model=LeaveResponse, status_code=status.HTTP_201_CREATED)
async def apply_leave(
    data: LeaveCreate,
    current_user: CurrentUser = Depends(get_current_user),
    controller: LeaveController = Depends(),
) -> LeaveResponse:
    """Mengajukan permohonan cuti atau sakit (karyawan, ketua tim, atau HR)."""
    return await controller.handle_apply(current_user, data)


@router.get("", response_model=list[LeaveResponse])
async def list_leaves(
    employee_id: UUID | None = Query(None, description="Filter per karyawan"),
    status: str | None = Query(None, description="Filter status cuti"),
    year: int | None = Query(None, description="Tahun cuti"),
    current_user: CurrentUser = Depends(get_current_user),
    controller: LeaveController = Depends(),
) -> list[LeaveResponse]:
    """Mengambil riwayat atau daftar permohonan cuti."""
    return await controller.handle_list(current_user, employee_id=employee_id, status=status, year=year)


@router.get("/balances/{employee_id}", response_model=LeaveBalanceResponse)
async def get_leave_balance(
    employee_id: UUID,
    year: int = Query(2026, description="Tahun kuota cuti"),
    current_user: CurrentUser = Depends(get_current_user),
    controller: LeaveController = Depends(),
) -> LeaveBalanceResponse:
    """Mengambil kuota dan sisa cuti tahunan karyawan."""
    return await controller.handle_balance(current_user, employee_id, year)


@router.get("/{leave_id}", response_model=LeaveResponse)
async def get_leave(
    leave_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: LeaveController = Depends(),
) -> LeaveResponse:
    """Detail permohonan cuti."""
    return await controller.handle_get(current_user, leave_id)


@router.post("/{leave_id}/review", response_model=LeaveResponse)
async def review_leave(
    leave_id: UUID,
    data: LeaveReview,
    current_user: CurrentUser = Depends(get_current_user),
    controller: LeaveController = Depends(),
) -> LeaveResponse:
    """Persetujuan atau penolakan cuti oleh PM atau HR/OM/Super Admin."""
    return await controller.handle_review(current_user, leave_id, data)
