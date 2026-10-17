"""
app/modules/offboarding/routes/offboarding_route.py
Rute API HTTP untuk entitas offboarding karyawan dan clearance aset.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.core.security import CurrentUser
from app.modules.offboarding.controllers.offboarding_controller import OffboardingController
from app.modules.offboarding.schemas.offboarding_schema import (
    ClearanceItemVerify,
    OffboardingApprove,
    OffboardingCreate,
    OffboardingDetail,
    OffboardingListItem,
)

router = APIRouter(prefix="/offboarding", tags=["Offboarding"])


@router.get("", response_model=list[OffboardingListItem])
async def list_offboardings(
    status: str | None = Query(None, description="Filter status (active, in_process, offboarded)"),
    current_user: CurrentUser = Depends(get_current_user),
    controller: OffboardingController = Depends(),
) -> list[OffboardingListItem]:
    """Mengambil daftar seluruh permohonan offboarding karyawan."""
    return await controller.handle_list_offboardings(current_user, status)


@router.get("/{offboarding_id}", response_model=OffboardingDetail)
async def get_offboarding(
    offboarding_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: OffboardingController = Depends(),
) -> OffboardingDetail:
    """Mengambil detail offboarding beserta checklist pengembalian asetnya."""
    return await controller.handle_get_offboarding(current_user, offboarding_id)


@router.post("", response_model=OffboardingListItem, status_code=201)
async def create_offboarding(
    data: OffboardingCreate,
    current_user: CurrentUser = Depends(get_current_user),
    controller: OffboardingController = Depends(),
) -> OffboardingListItem:
    """Mengajukan proses offboarding / pengunduran diri karyawan."""
    return await controller.handle_create_offboarding(current_user, data)


@router.post("/clearance-items/{clearance_item_id}/verify")
async def verify_clearance_item(
    clearance_item_id: UUID,
    data: ClearanceItemVerify,
    current_user: CurrentUser = Depends(get_current_user),
    controller: OffboardingController = Depends(),
) -> dict[str, str]:
    """Verifikasi dan checklist fisik pengembalian aset pinjaman."""
    return await controller.handle_verify_clearance(current_user, clearance_item_id, data)


@router.post("/{offboarding_id}/approve", response_model=OffboardingListItem)
async def approve_offboarding(
    offboarding_id: UUID,
    data: OffboardingApprove,
    current_user: CurrentUser = Depends(get_current_user),
    controller: OffboardingController = Depends(),
) -> OffboardingListItem:
    """Menyetujui proses offboarding oleh PM (operasional) atau HR (final clearance)."""
    return await controller.handle_approve_offboarding(current_user, offboarding_id, data)
