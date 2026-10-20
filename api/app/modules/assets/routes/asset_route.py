"""
app/modules/assets/routes/asset_route.py

Rute endpoint HTTP untuk manajemen aset (/assets).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import allocation_plan_access, get_current_user, require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.assets.controllers.asset_controller import AssetController
from app.modules.assets.schemas.asset_schema import (
    AssetAllocationResponse,
    AssetCheckRequest,
    AssetCreate,
    AssetListItem,
    AssetReleaseRequest,
    AssetReserveRequest,
    AssetResponse,
    AssetReturnCreate,
    AssetReturnHistoryItem,
    AssetReturnResponse,
    AssetReturnVerify,
    AssetStatusResponse,
)
from app.shared.access.access_service import PlanAccess, PlanNeed

router = APIRouter(prefix="/assets", tags=["Assets"])
_ALLOCATION_LEADER_ACCESS = Depends(allocation_plan_access(PlanNeed.LEADER))


@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    data: AssetCreate,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_ASSETS)),
    controller: AssetController = Depends(),
) -> AssetResponse:
    """Membuat aset baru."""
    return await controller.handle_create_asset(current_user, data)


@router.get("", response_model=list[AssetListItem])
async def get_assets(
    current_user: CurrentUser = Depends(get_current_user),
    controller: AssetController = Depends(),
) -> list[AssetListItem]:
    """Aset organisasi + alokasi berjalan + pengajuan pengembalian yang menunggu."""
    return await controller.handle_list_assets(current_user)


@router.get("/{asset_id}/returns", response_model=list[AssetReturnHistoryItem])
async def get_asset_returns(
    asset_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: AssetController = Depends(),
) -> list[AssetReturnHistoryItem]:
    """Riwayat pengembalian aset (terbaru dulu)."""
    return await controller.handle_return_history(current_user, asset_id)


@router.get("/returns/{return_id}/pdf", response_class=Response)
async def get_bast_pdf(
    return_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: AssetController = Depends(),
) -> Response:
    """Berita acara serah terima (BAST) untuk pengembalian yang sudah diperiksa."""
    return await controller.handle_bast_pdf(current_user, return_id)


@router.post("/{asset_id}/reserve", response_model=AssetAllocationResponse)
async def reserve_asset(
    asset_id: UUID,
    data: AssetReserveRequest,
    current_user: CurrentUser = Depends(get_current_user),
    controller: AssetController = Depends(),
) -> AssetAllocationResponse:
    """Petugas aset atau PM unit/OPS memesan aset untuk SK aktif."""
    return await controller.handle_reserve(current_user, asset_id, data)


@router.post("/{asset_id}/release", response_model=AssetStatusResponse)
async def release_asset(
    asset_id: UUID,
    data: AssetReleaseRequest,
    current_user: CurrentUser = Depends(get_current_user),
    controller: AssetController = Depends(),
) -> AssetStatusResponse:
    """Reservasi yang belum dipakai dilepas."""
    return await controller.handle_release(current_user, asset_id, data)


@router.post("/{asset_id}/check", response_model=AssetStatusResponse)
async def check_asset(
    asset_id: UUID,
    data: AssetCheckRequest,
    current_user: CurrentUser = Depends(get_current_user),
    controller: AssetController = Depends(),
) -> AssetStatusResponse:
    """Pengemudi yang ditunjuk menyatakan kendaraan layak atau banding."""
    return await controller.handle_check(current_user, asset_id, data)


@router.post("/allocations/{alloc_id}/return", response_model=AssetReturnResponse)
async def request_asset_return(
    alloc_id: UUID,
    data: AssetReturnCreate,
    access: PlanAccess = _ALLOCATION_LEADER_ACCESS,
    controller: AssetController = Depends(),
) -> AssetReturnResponse:
    """Formulir BAST pengembalian aset — diajukan ketua tim menurut SK peminjam."""
    return await controller.handle_request_return(access, alloc_id, data)


@router.post("/returns/{return_id}/verify", response_model=AssetReturnResponse)
async def verify_asset_return(
    return_id: UUID,
    data: AssetReturnVerify,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_ASSETS)),
    controller: AssetController = Depends(),
) -> AssetReturnResponse:
    """Verifikasi BAST pengembalian aset oleh petugas OPS/Aset."""
    return await controller.handle_verify_return(current_user, return_id, data)
