"""
app/modules/leaves/routes/leave_route.py

Rute endpoint HTTP untuk modul cuti & izin karyawan (/leaves).
"""
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import IdempotencyGuard, get_current_user, idempotency_guard
from app.core.list_params import ListParams, apply_list, check_date_range
from app.core.security import CurrentUser
from app.core.time import jakarta_now
from app.modules.leaves.controllers.leave_controller import LeaveController
from app.modules.leaves.schemas.leave_schema import (
    LeaveBalanceResponse,
    LeaveCancel,
    LeaveCreate,
    LeaveResponse,
    LeaveReview,
    LeaveTypeOption,
)

router = APIRouter(prefix="/leaves", tags=["Leaves"])


@router.post("", response_model=LeaveResponse, status_code=status.HTTP_201_CREATED)
async def apply_leave(
    data: LeaveCreate,
    current_user: CurrentUser = Depends(get_current_user),
    controller: LeaveController = Depends(),
    idem: IdempotencyGuard = Depends(idempotency_guard),
) -> LeaveResponse | Response:
    """Mengajukan permohonan cuti atau sakit (karyawan, ketua tim, atau HR). Mendukung Idempotency-Key."""
    tersimpan = idem.tersimpan()
    if tersimpan is not None:
        return tersimpan
    hasil = await controller.handle_apply(current_user, data)
    return await idem.simpan(hasil, status.HTTP_201_CREATED)


@router.get("", response_model=list[LeaveResponse])
async def list_leaves(
    response: Response,
    employee_id: UUID | None = Query(None, description="Filter per karyawan"),
    status: str | None = Query(None, max_length=30, description="Filter status cuti"),
    year: int | None = Query(None, ge=2000, le=2100, description="Tahun cuti"),
    leave_type: str | None = Query(None, max_length=30, description="Filter jenis cuti"),
    date_from: date | None = Query(None, description="Cuti yang berakhir pada/setelah tanggal ini"),
    date_to: date | None = Query(None, description="Cuti yang mulai pada/sebelum tanggal ini"),
    params: ListParams = Depends(),
    current_user: CurrentUser = Depends(get_current_user),
    controller: LeaveController = Depends(),
) -> list[LeaveResponse]:
    """Mengambil riwayat atau daftar permohonan cuti. Cari `q`: nama, NIP, divisi, alasan."""
    check_date_range(date_from, date_to)
    rows = await controller.handle_list(current_user, employee_id=employee_id, status=status, year=year)
    return list(
        apply_list(
            rows,
            params,
            response,
            lambda r: (r.employee_name, r.employee_no, r.division_name, r.reason),
            extra=lambda r: (
                (leave_type is None or str(getattr(r.leave_type, "value", r.leave_type)) == leave_type)
                and (date_from is None or r.end_date >= date_from)
                and (date_to is None or r.start_date <= date_to)
            ),
        )
    )


@router.get("/balances/{employee_id}", response_model=LeaveBalanceResponse)
async def get_leave_balance(
    employee_id: UUID,
    year: int | None = Query(None, ge=2000, le=2100, description="Tahun kuota cuti (default: tahun berjalan WIB)"),
    current_user: CurrentUser = Depends(get_current_user),
    controller: LeaveController = Depends(),
) -> LeaveBalanceResponse:
    """Mengambil kuota dan sisa cuti tahunan karyawan."""
    return await controller.handle_balance(current_user, employee_id, year or jakarta_now().year)


@router.get("/types", response_model=list[LeaveTypeOption])
async def list_leave_types(
    current_user: CurrentUser = Depends(get_current_user),
    controller: LeaveController = Depends(),
) -> list[LeaveTypeOption]:
    """Daftar jenis cuti beserta keterangan pemakaian kuota."""
    return controller.handle_types()


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


@router.post("/{leave_id}/cancel", response_model=LeaveResponse)
async def cancel_leave(
    leave_id: UUID,
    data: LeaveCancel | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    controller: LeaveController = Depends(),
) -> LeaveResponse:
    """Pembatalan cuti oleh pemohon, HR, atau OM (PENDING/APPROVED_BY_PM/APPROVED_BY_HR, sebelum hari cuti berakhir)."""
    return await controller.handle_cancel(current_user, leave_id, data)
