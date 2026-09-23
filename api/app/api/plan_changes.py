from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db_with_user, require_permission
from app.core.permissions import Permission

router = APIRouter(prefix="/plans/{plan_id}/changes", tags=["Plan Changes / Addendums"])

class ExtensionRequest(BaseModel):
    new_period_end: date
    reason: str

class PersonnelRequest(BaseModel):
    proposed_leader_id: UUID
    reason: str

@router.post("/extension", response_model=dict)
async def request_extension(
    plan_id: UUID,
    data: ExtensionRequest,
    current_user: CurrentUser = Depends(require_permission(Permission.CREATE_PLAN)),
    db: AsyncSession = Depends(get_db_with_user)
):
    """Mengajukan Adendum Perpanjangan Waktu (P3-4)"""
    # 1. Pastikan SK dalam status yang bisa diperpanjang (IN_PROGRESS)
    check = text("SELECT status, upper(period) - integer '1' as current_end, revision FROM vms.work_plan WHERE id = :id FOR UPDATE")
    row = (await db.execute(check, {"id": plan_id})).fetchone()
    
    if not row or row.status not in ('IN_PROGRESS', 'ACCEPTED'):
        raise HTTPException(status_code=400, detail="Hanya SK yang aktif (IN_PROGRESS / ACCEPTED) yang dapat diperpanjang.")
        
    if data.new_period_end <= row.current_end:
        raise HTTPException(status_code=400, detail="Tanggal perpanjangan harus lebih lama dari tanggal selesai saat ini.")
        
    # 2. Ambil employee_id dari user yang request
    emp_q = text("SELECT employee_id FROM vms.app_user WHERE id = :uid")
    my_emp = (await db.execute(emp_q, {"uid": current_user.user_id})).scalar()
    
    # 3. Buat plan_change
    ins = text("""
        INSERT INTO vms.plan_change (
            work_plan_id, change_type, status, reason, 
            old_period, new_period, base_revision, proposed_revision, requested_by
        ) VALUES (
            :plan, 'EXTENSION', 'PENDING_PM', :reason, 
            daterange(null, :old_end + integer '1', '[)'), 
            daterange(null, :new_end + integer '1', '[)'), 
            :rev, :rev + 1, :emp
        ) RETURNING id
    """)
    res = await db.execute(ins, {
        "plan": plan_id, "reason": data.reason,
        "old_end": row.current_end, "new_end": data.new_period_end,
        "rev": row.revision, "emp": my_emp
    })
    
    return {"change_id": res.scalar(), "message": "Usulan perpanjangan diajukan."}

@router.post("/{change_id}/approve")
async def approve_change(
    plan_id: UUID,
    change_id: UUID,
    current_user: CurrentUser = Depends(require_permission(Permission.PUBLISH_PLAN)),
    db: AsyncSession = Depends(get_db_with_user)
):
    """Menyetujui adendum (P3-4, P3-5) dan menerapkannya."""
    check = text("SELECT * FROM vms.plan_change WHERE id = :id AND work_plan_id = :plan FOR UPDATE")
    change = (await db.execute(check, {"id": change_id, "plan": plan_id})).fetchone()
    
    if not change or change.status not in ('PENDING_PM', 'PENDING_LEADER'):
        raise HTTPException(status_code=400, detail="Usulan tidak ditemukan atau tidak dalam status pending.")
        
    emp_q = text("SELECT employee_id FROM vms.app_user WHERE id = :uid")
    my_emp = (await db.execute(emp_q, {"uid": current_user.user_id})).scalar()
    
    # Update change status
    upd_change = text("""
        UPDATE vms.plan_change 
        SET status = 'APPLIED', decided_by = :emp, updated_at = now() 
        WHERE id = :id
    """)
    await db.execute(upd_change, {"emp": my_emp, "id": change_id})
    
    # Apply logic based on type
    if change.change_type == 'EXTENSION':
        # Update upper bound of period
        apply_ext = text("""
            UPDATE vms.work_plan 
            SET period = daterange(lower(period), upper(:new_period::daterange), '[)'),
                revision = revision + 1, row_version = row_version + 1
            WHERE id = :plan
        """)
        await db.execute(apply_ext, {"new_period": change.new_period, "plan": plan_id})
        
        # Perpanjang juga valid_period member yang masih aktif
        ext_mem = text("""
            UPDATE vms.work_plan_member
            SET valid_period = daterange(lower(valid_period), upper(:new_period::daterange), '[)')
            WHERE work_plan_id = :plan AND valid_to IS NULL
        """)
        await db.execute(ext_mem, {"new_period": change.new_period, "plan": plan_id})
        
    elif change.change_type == 'PERSONNEL':
        # Penutupan baris anggota lama
        close_old = text("""
            UPDATE vms.work_plan_member
            SET valid_period = daterange(lower(valid_period), CURRENT_DATE, '[)')
            WHERE work_plan_id = :plan AND role_in_plan = 'LEADER' AND valid_to IS NULL
        """)
        await db.execute(close_old, {"plan": plan_id})
        
        # Pembukaan baris anggota baru
        open_new = text("""
            INSERT INTO vms.work_plan_member (work_plan_id, employee_id, role_in_plan, valid_period)
            SELECT id, :new_leader, 'LEADER', daterange(CURRENT_DATE, upper(period), '[)')
            FROM vms.work_plan WHERE id = :plan
        """)
        await db.execute(open_new, {"new_leader": change.proposed_leader_id, "plan": plan_id})
        
        # Update leader di work_plan
        upd_leader = text("UPDATE vms.work_plan SET leader_employee_id = :new_leader, revision = revision + 1, row_version = row_version + 1 WHERE id = :plan")
        await db.execute(upd_leader, {"new_leader": change.proposed_leader_id, "plan": plan_id})
        
    return {"message": "Adendum disetujui dan diterapkan."}
