from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_db_with_user, require_permission
from app.api.guards import PlanAccess, PlanNeed, allocation_plan_access, ensure_same_org
from app.core.enums import PlanStatus
from app.core.errors import AppError, ForbiddenError, ValidationError, trigger_rule_message
from app.core.permissions import Permission, RoleCode
from app.schemas.asset import (
    AssetAllocationCreate,
    AssetAllocationResponse,
    AssetCreate,
    AssetResponse,
    AssetReturnCreate,
    AssetReturnResponse,
    AssetReturnVerify,
)

router = APIRouter(prefix="/assets", tags=["Assets"])
_ALLOCATION_LEADER_ACCESS = Depends(allocation_plan_access(PlanNeed.LEADER))

@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    data: AssetCreate,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_ASSETS)),
    db: AsyncSession = Depends(get_db_with_user)
):
    ins = text("""
        INSERT INTO vms.asset (organization_id, kind, vehicle_type, code, name, condition)
        VALUES (:org, :kind, :vtype, :code, :name, :cond)
        RETURNING *
    """)
    try:
        res = await db.execute(ins, {
            "org": current_user.organization_id, "kind": data.kind,
            "vtype": data.vehicle_type, "code": data.code,
            "name": data.name, "cond": data.condition
        })
        return AssetResponse(**res.fetchone()._mapping)
    except Exception as e:
        raise HTTPException(status_code=400, detail={"code": "DB_ERROR", "message": str(e)})

@router.get("", response_model=list[AssetResponse])
async def get_assets(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user)
):
    query = text("SELECT * FROM vms.asset WHERE organization_id = :org AND deleted_at IS NULL ORDER BY name")
    rows = (await db.execute(query, {"org": current_user.organization_id})).fetchall()
    return [AssetResponse(**r._mapping) for r in rows]

@router.post("/allocate", response_model=AssetAllocationResponse)
async def allocate_asset(
    data: AssetAllocationCreate,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_ASSETS)),
    db: AsyncSession = Depends(get_db_with_user)
):
    await ensure_same_org(db, current_user.organization_id, assets=[data.asset_id],
                          work_plans=[data.work_plan_id], employees=[data.driver_employee_id])
    emp_q = text("SELECT employee_id FROM vms.app_user WHERE id = :uid")
    my_emp = (await db.execute(emp_q, {"uid": current_user.user_id})).scalar()

    # Check asset status
    check_asset = text("SELECT status, kind FROM vms.asset WHERE id = :id FOR UPDATE")
    asset = (await db.execute(check_asset, {"id": data.asset_id})).fetchone()
    
    if not asset or asset.status != 'AVAILABLE':
        raise HTTPException(status_code=400, detail="Aset tidak tersedia atau sudah dialokasikan.")

    # domain.js RESERVE_ASSET (V-11): SK masih aktif; kendaraan wajib berpengemudi dari tim penugasan.
    plan_q = text("""
        SELECT wp.status,
               wp.leader_employee_id = CAST(:driver AS uuid) OR EXISTS (
                   SELECT 1 FROM vms.work_plan_member m
                   WHERE m.work_plan_id = wp.id AND m.employee_id = CAST(:driver AS uuid)
                     AND upper_inf(m.valid_period)) AS driver_on_team
        FROM vms.work_plan wp WHERE wp.id = :plan
    """)
    plan = (await db.execute(plan_q, {"plan": data.work_plan_id, "driver": data.driver_employee_id})).fetchone()
    if plan.status in (PlanStatus.COMPLETED, PlanStatus.CANCELLED):
        raise AppError("INVALID_STATE", "Pilih work plan yang masih aktif.", status=409)
    if asset.kind == 'VEHICLE':
        if not data.driver_employee_id:
            raise ValidationError("Pilih pengemudi untuk aset kendaraan.")
        if not plan.driver_on_team:
            raise ValidationError("Pengemudi harus bagian dari tim penugasan.")

    ins = text("""
        INSERT INTO vms.asset_allocation (
            asset_id, work_plan_id, driver_employee_id, allocated_by
        ) VALUES (
            :asset, :plan, :driver, :emp
        ) RETURNING *
    """)
    try:
        res = await db.execute(ins, {
            "asset": data.asset_id, "plan": data.work_plan_id,
            "driver": data.driver_employee_id, "emp": my_emp
        })
        allocation = res.fetchone()
        
        # Update asset status
        await db.execute(text("UPDATE vms.asset SET status = 'IN_USE' WHERE id = :id"), {"id": data.asset_id})
        
        return AssetAllocationResponse(**allocation._mapping)
    except IntegrityError as e:
        # Aturan SIM hidup di trigger asset_allocation_driver — teruskan pesannya (V-11).
        rule = trigger_rule_message(e)
        if rule:
            raise ValidationError(rule) from None
        if "asset_allocation_no_overlap" in str(e):
            raise HTTPException(status_code=409, detail="Aset sudah dialokasikan ke pekerjaan lain pada waktu yang sama (overlap).")
        raise HTTPException(status_code=400, detail={"code": "DB_ERROR", "message": str(e)})
    except Exception as e:
        if "asset_allocation_no_overlap" in str(e):
            raise HTTPException(status_code=409, detail="Aset sudah dialokasikan ke pekerjaan lain pada waktu yang sama (overlap).")
        raise HTTPException(status_code=400, detail={"code": "DB_ERROR", "message": str(e)})

@router.post("/allocations/{alloc_id}/return", response_model=AssetReturnResponse)
async def request_asset_return(
    alloc_id: UUID,
    data: AssetReturnCreate,
    access: PlanAccess = _ALLOCATION_LEADER_ACCESS,
    db: AsyncSession = Depends(get_db_with_user)
):
    """P6-3: Formulir BAST pengembalian aset — diajukan ketua tim menurut SK peminjam (V-09)."""
    current_user = access.user
    if RoleCode.ASSET in current_user.roles:  # domain.js RETURN_ASSET
        raise ForbiddenError("Pengajuan pengembalian tidak dapat dilakukan oleh petugas aset. Gunakan ketua tim.")
    emp_q = text("SELECT employee_id FROM vms.app_user WHERE id = :uid")
    my_emp = (await db.execute(emp_q, {"uid": current_user.user_id})).scalar()
    
    ins = text("""
        INSERT INTO vms.asset_return (
            asset_allocation_id, requested_by, condition_on_return, note
        ) VALUES (
            :alloc, :emp, :cond, :note
        ) RETURNING *
    """)
    res = await db.execute(ins, {
        "alloc": alloc_id, "emp": my_emp, 
        "cond": data.condition_on_return, "note": data.note
    })
    return AssetReturnResponse(**res.fetchone()._mapping)

@router.post("/returns/{return_id}/verify", response_model=AssetReturnResponse)
async def verify_asset_return(
    return_id: UUID,
    data: AssetReturnVerify,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_ASSETS)),
    db: AsyncSession = Depends(get_db_with_user)
):
    """P6-3: Verifikasi BAST oleh OPS."""
    emp_q = text("SELECT employee_id FROM vms.app_user WHERE id = :uid")
    my_emp = (await db.execute(emp_q, {"uid": current_user.user_id})).scalar()
    
    # Dapatkan asset_id dari return ini
    get_a = text("""
        SELECT r.requested_by, a.asset_id, a.id as alloc_id
        FROM vms.asset_return r
        JOIN vms.asset_allocation a ON a.id = r.asset_allocation_id
        WHERE r.id = :id
    """)
    ret_info = (await db.execute(get_a, {"id": return_id})).fetchone()
    
    if not ret_info:
        raise HTTPException(status_code=404, detail="Return tidak ditemukan.")
    if ret_info.requested_by == my_emp:
        raise HTTPException(status_code=403, detail="Anda tidak boleh memverifikasi pengembalian yang Anda ajukan sendiri.")
        
    # Update return
    upd = text("""
        UPDATE vms.asset_return
        SET verified_by = :emp, verified_at = now(), is_accepted = :acc, note = COALESCE(note, '') || '\n' || :note
        WHERE id = :id
        RETURNING *
    """)
    res = await db.execute(upd, {"emp": my_emp, "acc": data.is_accepted, "note": data.note or "", "id": return_id})
    row = res.fetchone()
    
    if data.is_accepted:
        # Lepas alokasi & kembalikan status aset
        await db.execute(text("UPDATE vms.asset_allocation SET released_at = now() WHERE id = :id"), {"id": ret_info.alloc_id})
        await db.execute(text("UPDATE vms.asset SET status = 'AVAILABLE' WHERE id = :id"), {"id": ret_info.asset_id})
        
    return AssetReturnResponse(**row._mapping)
