"""
app/modules/offboarding/routes/offboarding_route.py
Rute offboarding PKWT & clearance aset (Milestone 9, docs/35 §7).
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import require_permission
from app.core.list_params import ListParams, apply_list
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.offboarding.controllers.offboarding_controller import OffboardingController
from app.modules.offboarding.schemas.offboarding_schema import (
    ClearanceItemVerify,
    CompleteDueResult,
    OffboardingApprove,
    OffboardingCancel,
    OffboardingCreate,
    OffboardingDetail,
    OffboardingListItem,
    OffboardingStatus,
    PkwtExpiringRow,
)

router = APIRouter(prefix="/offboarding", tags=["Offboarding"])
_VIEW = Depends(require_permission(Permission.VIEW_OFFBOARDING))
_MANAGE = Depends(require_permission(Permission.MANAGE_OFFBOARDING))


@router.get("", response_model=list[OffboardingListItem])
async def list_offboardings(
    response: Response,
    params: ListParams = Depends(),
    status: OffboardingStatus | None = None,
    current_user: CurrentUser = _VIEW,
    controller: OffboardingController = Depends(),
) -> list[OffboardingListItem]:
    """Daftar offboarding (PM hanya karyawan divisinya)."""
    rows = await controller.list_all(current_user, status.value if status else None)
    hay = lambda r: (r.employee_name, r.employee_no, r.division_name, r.reason_type)  # noqa: E731
    return list(apply_list(rows, params, response, hay))


@router.get("/pkwt-expiring", response_model=list[PkwtExpiringRow])
async def pkwt_expiring(
    days: int = Query(30, ge=0, le=180),
    current_user: CurrentUser = _VIEW,
    controller: OffboardingController = Depends(),
) -> list[PkwtExpiringRow]:
    """Karyawan PKWT yang kontraknya berakhir dalam `days` hari (atau sudah lewat) dan belum diproses."""
    return await controller.pkwt_expiring(current_user, days)


@router.post("/complete-due", response_model=CompleteDueResult)
async def complete_due_offboardings(
    current_user: CurrentUser = Depends(require_permission(Permission.RUN_SYSTEM_JOBS)),
    controller: OffboardingController = Depends(),
) -> CompleteDueResult:
    """Penjadwal harian: selesaikan offboarding yang disetujui dan tanggal efektifnya tiba."""
    return await controller.complete_due()


@router.get("/{offboarding_id}", response_model=OffboardingDetail)
async def get_offboarding(
    offboarding_id: UUID,
    current_user: CurrentUser = _VIEW,
    controller: OffboardingController = Depends(),
) -> OffboardingDetail:
    """Detail offboarding + daftar barang yang harus dikembalikan."""
    return await controller.detail(current_user, offboarding_id)


@router.post("", response_model=OffboardingDetail, status_code=201)
async def create_offboarding(
    data: OffboardingCreate,
    current_user: CurrentUser = _MANAGE,
    controller: OffboardingController = Depends(),
) -> OffboardingDetail:
    """HR memulai offboarding: pinjaman aset yang belum kembali otomatis menjadi item clearance."""
    return await controller.create(data, current_user)


@router.post("/clearance-items/{clearance_item_id}/verify", response_model=OffboardingDetail)
async def verify_clearance_item(
    clearance_item_id: UUID,
    data: ClearanceItemVerify,
    current_user: CurrentUser = _MANAGE,
    controller: OffboardingController = Depends(),
) -> OffboardingDetail:
    """HR/GA memverifikasi barang yang dikembalikan (GOOD/DAMAGED/LOST + foto); pinjaman aset ditutup."""
    return await controller.verify_item(current_user, clearance_item_id, data)


@router.post("/{offboarding_id}/approve", response_model=OffboardingDetail)
async def approve_offboarding(
    offboarding_id: UUID,
    data: OffboardingApprove,
    current_user: CurrentUser = _VIEW,
    controller: OffboardingController = Depends(),
) -> OffboardingDetail:
    """Persetujuan PM (PM/OM divisi karyawan) atau HR — hanya setelah clearance lengkap."""
    return await controller.approve(current_user, offboarding_id, data.approval_type)


@router.post("/{offboarding_id}/cancel")
async def cancel_offboarding(
    offboarding_id: UUID,
    data: OffboardingCancel,
    current_user: CurrentUser = _MANAGE,
    controller: OffboardingController = Depends(),
) -> dict[str, str]:
    """Batalkan offboarding yang belum selesai; karyawan aktif kembali."""
    return await controller.cancel(current_user, offboarding_id, data.reason)
