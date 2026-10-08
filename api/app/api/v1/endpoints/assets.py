from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.concurrency import run_in_threadpool

from app.api.deps import (
    allocation_plan_access,
    get_asset_reservation_service,
    get_current_user,
    plan_access,
    require_permission,
)
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.schemas.asset import (
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
    PlanAssetItem,
)
from app.services.access_service import PlanAccess, PlanNeed
from app.services.asset_reservation_service import AssetReservationService
from app.services.pdf_service import html_to_pdf, render_bast_html

router = APIRouter(prefix="/assets", tags=["Assets"])
plan_assets_router = APIRouter(prefix="/work-plans/{plan_id}", tags=["Assets"])
_PLAN_VIEW_ACCESS = Depends(plan_access(PlanNeed.VIEW))
_ALLOCATION_LEADER_ACCESS = Depends(allocation_plan_access(PlanNeed.LEADER))

@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    data: AssetCreate,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_ASSETS)),
    asset_reservation_service: AssetReservationService = Depends(get_asset_reservation_service)
) -> AssetResponse:
    """
    Membuat aset baru.

    Body params:
    - data: Data pembuatan aset baru (AssetCreate)

    Return: Detail aset yang baru dibuat (AssetResponse)
    """
    try:
        row = await asset_reservation_service.create_asset(
            current_user.organization_id, kind=data.kind, vehicle_type=data.vehicle_type, code=data.code,
            name=data.name, condition=data.condition)
    except Exception as e:
        # Pesan DB_ERROR diganti teks umum oleh handler galat; isi aslinya hanya ke log (T-06).
        raise HTTPException(status_code=400, detail={"code": "DB_ERROR", "message": str(e)}) from e
    return AssetResponse(**row._mapping)

@router.get("", response_model=list[AssetListItem])
async def get_assets(
    current_user: CurrentUser = Depends(get_current_user),
    asset_reservation_service: AssetReservationService = Depends(get_asset_reservation_service)
) -> list[AssetListItem]:
    """
    Aset organisasi + alokasi berjalan + pengajuan pengembalian yang menunggu (M6/R9 dari layar).

    Return: Daftar ringkasan aset organisasi (list[AssetListItem])
    """
    # Menggunakan injeksi dependensi untuk mendapatkan pengguna saat ini dan AssetReservationService
    # Memanggil service layer untuk mengambil list aset organisasi terkait
    rows = await asset_reservation_service.list_assets(current_user.organization_id)
    return [AssetListItem(**r._mapping) for r in rows]

@router.get("/{asset_id}/returns", response_model=list[AssetReturnHistoryItem])
async def get_asset_returns(
    asset_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    asset_reservation_service: AssetReservationService = Depends(get_asset_reservation_service)
) -> list[AssetReturnHistoryItem]:
    """
    Riwayat pengembalian aset (terbaru dulu). Aset organisasi lain → 404.

    Path params:
    - asset_id: UUID aset

    Return: Riwayat pengembalian aset (list[AssetReturnHistoryItem])
    """
    # Memanggil method return_history dari service layer yang diinjeksi
    rows = await asset_reservation_service.return_history(current_user.organization_id, asset_id)
    return [AssetReturnHistoryItem(**r._mapping) for r in rows]


@router.get("/returns/{return_id}/pdf", response_class=Response)
async def get_bast_pdf(
    return_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    asset_reservation_service: AssetReservationService = Depends(get_asset_reservation_service)
) -> Response:
    """
    Berita acara serah terima (P6-4) untuk pengembalian yang sudah diperiksa. Render → threadpool.

    Path params:
    - return_id: UUID catatan pengembalian

    Return: File PDF (Response)
    """
    # Memanggil fungsi bast dari service layer yang diinjeksi
    record = await asset_reservation_service.bast(current_user.organization_id, return_id)
    pdf = await run_in_threadpool(html_to_pdf, render_bast_html(record))
    filename = f"BAST-{record.asset_code}-{record.plan_number}.pdf".replace("/", "-")
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{filename}"'})


@router.post("/{asset_id}/reserve", response_model=AssetAllocationResponse)
async def reserve_asset(
    asset_id: UUID,
    data: AssetReserveRequest,
    current_user: CurrentUser = Depends(get_current_user),
    asset_reservation_service: AssetReservationService = Depends(get_asset_reservation_service)
) -> AssetAllocationResponse:
    """
    domain.js RESERVE_ASSET (V-27): petugas aset atau PM unit/OPS SK memesan aset untuk SK aktif.

    Path params:
    - asset_id: UUID aset yang dipesan

    Body params:
    - data: Data reservasi aset (AssetReserveRequest)

    Return: Detail alokasi aset yang direkam (AssetAllocationResponse)
    """
    # Melakukan delegasi logika ke service layer
    await asset_reservation_service.ensure_refs(current_user.organization_id, assets=[asset_id],
                                                work_plans=[data.work_plan_id], employees=[data.driver_employee_id])
    allocation = await asset_reservation_service.reserve(current_user, asset_id, data.work_plan_id,
                                                           data.driver_employee_id)
    return AssetAllocationResponse(**allocation._mapping)


@router.post("/{asset_id}/release", response_model=AssetStatusResponse)
async def release_asset(
    asset_id: UUID,
    data: AssetReleaseRequest,
    current_user: CurrentUser = Depends(get_current_user),
    asset_reservation_service: AssetReservationService = Depends(get_asset_reservation_service)
) -> AssetStatusResponse:
    """
    domain.js RELEASE_ASSET (V-27): reservasi yang belum dipakai dilepas.

    Path params:
    - asset_id: UUID aset yang akan dilepas

    Body params:
    - data: Data identifikasi SK (AssetReleaseRequest)

    Return: Status pelepasan aset
    """
    # Referensi aset & SK diperiksa satu organisasi lewat asset_reservation_service
    await asset_reservation_service.ensure_refs(current_user.organization_id, assets=[asset_id],
                                                work_plans=[data.work_plan_id])
    status_ = await asset_reservation_service.release(current_user, asset_id, data.work_plan_id)
    return AssetStatusResponse(asset_id=asset_id, status=status_)


@router.post("/{asset_id}/check", response_model=AssetStatusResponse)
async def check_asset(
    asset_id: UUID,
    data: AssetCheckRequest,
    current_user: CurrentUser = Depends(get_current_user),
    asset_reservation_service: AssetReservationService = Depends(get_asset_reservation_service)
) -> AssetStatusResponse:
    """
    domain.js CHECK_ASSET (V-27): pengemudi yang ditunjuk menyatakan kendaraan layak atau banding.

    Path params:
    - asset_id: UUID aset yang dicek

    Body params:
    - data: Data laporan kelayakan (AssetCheckRequest)

    Return: Status aset pasca-pengecekan
    """
    # Melakukan logika checking menggunakan service layer dari Dependensi
    await asset_reservation_service.ensure_refs(current_user.organization_id, assets=[asset_id])
    status_ = await asset_reservation_service.check(current_user, asset_id, data.decision, data.reason)
    return AssetStatusResponse(asset_id=asset_id, status=status_)


@router.post("/allocations/{alloc_id}/return", response_model=AssetReturnResponse)
async def request_asset_return(
    alloc_id: UUID,
    data: AssetReturnCreate,
    access: PlanAccess = _ALLOCATION_LEADER_ACCESS,
    asset_reservation_service: AssetReservationService = Depends(get_asset_reservation_service)
) -> AssetReturnResponse:
    """
    P6-3: Formulir BAST pengembalian aset — diajukan ketua tim menurut SK peminjam (V-09).

    Path params:
    - alloc_id: UUID alokasi aset yang dikembalikan

    Body params:
    - data: Data pengembalian aset (AssetReturnCreate)

    Return: Detail pengajuan pengembalian
    """
    row = await asset_reservation_service.request_return(access.user, alloc_id, data.condition_on_return, data.note)
    return AssetReturnResponse(**row._mapping)

@router.post("/returns/{return_id}/verify", response_model=AssetReturnResponse)
async def verify_asset_return(
    return_id: UUID,
    data: AssetReturnVerify,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_ASSETS)),
    asset_reservation_service: AssetReservationService = Depends(get_asset_reservation_service)
) -> AssetReturnResponse:
    """
    P6-3: Verifikasi BAST oleh OPS.

    Path params:
    - return_id: UUID pengembalian aset

    Body params:
    - data: Verifikasi kondisi (AssetReturnVerify)

    Return: Detail pengembalian terverifikasi
    """
    row = await asset_reservation_service.verify_return(current_user, return_id, data.is_accepted, data.note)
    return AssetReturnResponse(**row._mapping)


@plan_assets_router.get("/assets", response_model=list[PlanAssetItem])
async def get_plan_assets(
    plan_id: UUID,
    access: PlanAccess = _PLAN_VIEW_ACCESS,
    asset_reservation_service: AssetReservationService = Depends(get_asset_reservation_service)
) -> list[PlanAssetItem]:
    """
    Aset yang dipakai SK beserta kondisi saat dikembalikan (mode presentasi, M5). SK tak terlihat → 404.

    Path params:
    - plan_id: UUID SK (di-routing)

    Return: Daftar aset SK
    """
    # Menerapkan kontrol akses melalui dependensi injeksi access (_PLAN_VIEW_ACCESS)
    # Memanggil layanan AssetReservationService untuk mengambil list
    return [PlanAssetItem(**r._mapping) for r in await asset_reservation_service.plan_assets(plan_id)]

