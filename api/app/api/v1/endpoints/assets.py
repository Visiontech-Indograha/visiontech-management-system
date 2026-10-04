from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    allocation_plan_access,
    get_asset_reservation_service,
    get_current_user,
    get_db_with_user,
    plan_access,
    require_permission,
)
from app.core.errors import AppError, ForbiddenError, NotFoundError
from app.core.permissions import Permission, RoleCode
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
from app.services.access_service import PlanAccess, PlanNeed, ensure_same_org
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
    db: AsyncSession = Depends(get_db_with_user)
) -> AssetResponse:
    ins = text("""
        INSERT INTO vms.asset (organization_id, kind, vehicle_type, code, name, condition)
        VALUES (:org, :kind, :vtype, :code, :name, :cond)
        RETURNING id, organization_id, kind, vehicle_type, code, name, condition, status
    """)
    try:
        res = await db.execute(ins, {
            "org": current_user.organization_id, "kind": data.kind,
            "vtype": data.vehicle_type, "code": data.code,
            "name": data.name, "cond": data.condition
        })
        return AssetResponse(**res.one()._mapping)
    except Exception as e:
        raise HTTPException(status_code=400, detail={"code": "DB_ERROR", "message": str(e)})

@router.get("", response_model=list[AssetListItem])
async def get_assets(
    current_user: CurrentUser = Depends(get_current_user),
    asset_reservation_service: AssetReservationService = Depends(get_asset_reservation_service)
) -> list[AssetListItem]:
    """Aset organisasi + alokasi berjalan + pengajuan pengembalian yang menunggu (M6/R9 dari layar)."""
    rows = await asset_reservation_service.list_assets(current_user.organization_id)
    return [AssetListItem(**r._mapping) for r in rows]

@router.get("/{asset_id}/returns", response_model=list[AssetReturnHistoryItem])
async def get_asset_returns(
    asset_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    asset_reservation_service: AssetReservationService = Depends(get_asset_reservation_service)
) -> list[AssetReturnHistoryItem]:
    """Riwayat pengembalian aset (terbaru dulu). Aset organisasi lain → 404."""
    rows = await asset_reservation_service.return_history(current_user.organization_id, asset_id)
    return [AssetReturnHistoryItem(**r._mapping) for r in rows]


@router.get("/returns/{return_id}/pdf", response_class=Response)
async def get_bast_pdf(
    return_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    asset_reservation_service: AssetReservationService = Depends(get_asset_reservation_service)
) -> Response:
    """Berita acara serah terima (P6-4) untuk pengembalian yang sudah diperiksa. Render → threadpool."""
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
    db: AsyncSession = Depends(get_db_with_user),
    asset_reservation_service: AssetReservationService = Depends(get_asset_reservation_service)
) -> AssetAllocationResponse:
    """domain.js RESERVE_ASSET (V-27): petugas aset atau PM unit/OPS SK memesan aset untuk SK aktif."""
    await ensure_same_org(db, current_user.organization_id, assets=[asset_id],
                          work_plans=[data.work_plan_id], employees=[data.driver_employee_id])
    allocation = await asset_reservation_service.reserve(current_user, asset_id, data.work_plan_id,
                                                           data.driver_employee_id)
    return AssetAllocationResponse(**allocation._mapping)


@router.post("/{asset_id}/release", response_model=AssetStatusResponse)
async def release_asset(
    asset_id: UUID,
    data: AssetReleaseRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user),
    asset_reservation_service: AssetReservationService = Depends(get_asset_reservation_service)
) -> AssetStatusResponse:
    """domain.js RELEASE_ASSET (V-27): reservasi yang belum dipakai dilepas."""
    await ensure_same_org(db, current_user.organization_id, assets=[asset_id], work_plans=[data.work_plan_id])
    status_ = await asset_reservation_service.release(current_user, asset_id, data.work_plan_id)
    return AssetStatusResponse(asset_id=asset_id, status=status_)


@router.post("/{asset_id}/check", response_model=AssetStatusResponse)
async def check_asset(
    asset_id: UUID,
    data: AssetCheckRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user),
    asset_reservation_service: AssetReservationService = Depends(get_asset_reservation_service)
) -> AssetStatusResponse:
    """domain.js CHECK_ASSET (V-27): pengemudi yang ditunjuk menyatakan kendaraan layak atau banding."""
    await ensure_same_org(db, current_user.organization_id, assets=[asset_id])
    status_ = await asset_reservation_service.check(current_user, asset_id, data.decision, data.reason)
    return AssetStatusResponse(asset_id=asset_id, status=status_)


@router.post("/allocations/{alloc_id}/return", response_model=AssetReturnResponse)
async def request_asset_return(
    alloc_id: UUID,
    data: AssetReturnCreate,
    access: PlanAccess = _ALLOCATION_LEADER_ACCESS,
    db: AsyncSession = Depends(get_db_with_user)
) -> AssetReturnResponse:
    """P6-3: Formulir BAST pengembalian aset — diajukan ketua tim menurut SK peminjam (V-09)."""
    current_user = access.user
    if RoleCode.ASSET in current_user.roles:  # domain.js RETURN_ASSET
        raise ForbiddenError("Pengajuan pengembalian tidak dapat dilakukan oleh petugas aset. Gunakan ketua tim.")
    emp_q = text("SELECT employee_id FROM vms.app_user WHERE id = :uid")
    my_emp = (await db.execute(emp_q, {"uid": current_user.user_id})).scalar()

    # domain.js RETURN_ASSET (R9): hanya aset yang sedang dipinjam — satu pengajuan terbuka per aset.
    state_q = text("""
        SELECT a.released_at IS NULL AS active, s.status AS asset_status, s.id AS asset_id
        FROM vms.asset_allocation a JOIN vms.asset s ON s.id = a.asset_id
        WHERE a.id = :alloc
        FOR UPDATE OF s
    """)
    state = (await db.execute(state_q, {"alloc": alloc_id})).fetchone()
    if state is None:
        raise NotFoundError("Peminjaman aset")  # sebelumnya AttributeError → 500
    if not (state.active and state.asset_status in ("IN_USE", "RESERVED")):
        raise AppError("INVALID_STATE", "Aset belum dipinjam atau sudah menunggu verifikasi.", status=409)

    ins = text("""
        INSERT INTO vms.asset_return (
            asset_allocation_id, requested_by, condition_on_return, note
        ) VALUES (
            :alloc, :emp, :cond, :note
        ) RETURNING id, asset_allocation_id, requested_by, requested_at, condition_on_return, note, verified_by, verified_at, is_accepted
    """)
    res = await db.execute(ins, {
        "alloc": alloc_id, "emp": my_emp,
        "cond": data.condition_on_return, "note": data.note
    })
    await db.execute(text("UPDATE vms.asset SET status = 'RETURN_PENDING' WHERE id = :id"), {"id": state.asset_id})
    return AssetReturnResponse(**res.one()._mapping)

@router.post("/returns/{return_id}/verify", response_model=AssetReturnResponse)
async def verify_asset_return(
    return_id: UUID,
    data: AssetReturnVerify,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_ASSETS)),
    db: AsyncSession = Depends(get_db_with_user)
) -> AssetReturnResponse:
    """P6-3: Verifikasi BAST oleh OPS."""
    emp_q = text("SELECT employee_id FROM vms.app_user WHERE id = :uid")
    my_emp = (await db.execute(emp_q, {"uid": current_user.user_id})).scalar()
    
    # Dapatkan asset_id dari return ini — hanya milik organisasi sendiri (V-09: jalur ber-id).
    get_a = text("""
        SELECT r.requested_by, r.verified_at, a.asset_id, a.id as alloc_id, s.status AS asset_status
        FROM vms.asset_return r
        JOIN vms.asset_allocation a ON a.id = r.asset_allocation_id
        JOIN vms.asset s ON s.id = a.asset_id
        WHERE r.id = :id AND s.organization_id = :org
        FOR UPDATE OF s
    """)
    ret_info = (await db.execute(get_a, {"id": return_id, "org": current_user.organization_id})).fetchone()

    if not ret_info:
        raise NotFoundError("Pengembalian aset")
    # domain.js VERIFY_RETURN (R9): hanya pengajuan yang masih menunggu; tidak diperiksa pengaju sendiri.
    if ret_info.verified_at is not None or ret_info.asset_status != "RETURN_PENDING":
        raise AppError("INVALID_STATE", "Aset belum menunggu verifikasi pengembalian.", status=409)
    if ret_info.requested_by == my_emp:
        raise ForbiddenError("Pengembalian tidak dapat diperiksa oleh pengaju yang sama. Gunakan ketua tim untuk serah terima.")

    # Update return
    upd = text("""
        UPDATE vms.asset_return
        SET verified_by = :emp, verified_at = now(), is_accepted = :acc, note = COALESCE(note, '') || '\n' || :note
        WHERE id = :id
        RETURNING id, asset_allocation_id, requested_by, requested_at, condition_on_return, note, verified_by, verified_at, is_accepted
    """)
    res = await db.execute(upd, {"emp": my_emp, "acc": data.is_accepted, "note": data.note or "", "id": return_id})
    row = res.one()

    if data.is_accepted:
        # Lepas alokasi & kembalikan status aset
        await db.execute(text("UPDATE vms.asset_allocation SET released_at = now() WHERE id = :id"), {"id": ret_info.alloc_id})
        await db.execute(text("UPDATE vms.asset SET status = 'AVAILABLE' WHERE id = :id"), {"id": ret_info.asset_id})
    else:
        # Ditolak: aset kembali ke tim peminjam agar dapat diperbaiki & diajukan ulang — bukan buntu (R9).
        await db.execute(text("UPDATE vms.asset SET status = 'IN_USE' WHERE id = :id"), {"id": ret_info.asset_id})

    return AssetReturnResponse(**row._mapping)


@plan_assets_router.get("/assets", response_model=list[PlanAssetItem])
async def get_plan_assets(
    plan_id: UUID,
    access: PlanAccess = _PLAN_VIEW_ACCESS,
    asset_reservation_service: AssetReservationService = Depends(get_asset_reservation_service)
) -> list[PlanAssetItem]:
    """Aset yang dipakai SK beserta kondisi saat dikembalikan (mode presentasi, M5). SK tak terlihat → 404."""
    return [PlanAssetItem(**r._mapping) for r in await asset_reservation_service.plan_assets(plan_id)]

