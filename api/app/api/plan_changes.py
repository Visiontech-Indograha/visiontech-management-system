from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.api.guards import PlanAccess, PlanNeed, plan_access
from app.core.enums import ChangeStatus, ChangeType, PlanStatus

router = APIRouter(prefix="/work-plans/{plan_id}/changes", tags=["Plan Changes / Addendums"])
_LEADER_ACCESS = Depends(plan_access(PlanNeed.LEADER))
_PM_UNIT_ACCESS = Depends(plan_access(PlanNeed.PM_UNIT))

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
    access: PlanAccess = _LEADER_ACCESS,
    db: AsyncSession = Depends(get_db_with_user)
):
    """Mengajukan Adendum Perpanjangan Waktu (P3-4). Diajukan ketua menurut SK (domain.js REQUEST_CHANGE)."""
    current_user = access.user
    # 1. Pastikan SK dalam status yang bisa diperpanjang (IN_PROGRESS)
    check = text("SELECT status, upper(period) - integer '1' as current_end, revision FROM vms.work_plan WHERE id = :id FOR UPDATE")
    row = (await db.execute(check, {"id": plan_id})).fetchone()
    
    if not row or row.status not in (PlanStatus.IN_PROGRESS, PlanStatus.ACCEPTED):
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
            :plan, :extend, :pending, :reason,
            daterange(NULL, CAST(:old_end AS date) + 1, '[)'),
            daterange(NULL, CAST(:new_end AS date) + 1, '[)'),
            :rev, :rev + 1, :emp
        ) RETURNING id
    """)
    res = await db.execute(ins, {
        "plan": plan_id, "reason": data.reason,
        "old_end": row.current_end, "new_end": data.new_period_end,
        "rev": row.revision, "emp": my_emp,
        "extend": ChangeType.EXTEND, "pending": ChangeStatus.PENDING_PM,
    })
    
    return {"change_id": res.scalar(), "message": "Usulan perpanjangan diajukan."}

@router.post("/{change_id}/approve")
async def approve_change(
    plan_id: UUID,
    change_id: UUID,
    access: PlanAccess = _PM_UNIT_ACCESS,
    db: AsyncSession = Depends(get_db_with_user)
):
    """Menyetujui adendum (P3-4, P3-5) dan menerapkannya."""
    current_user = access.user
    check = text("SELECT * FROM vms.plan_change WHERE id = :id AND work_plan_id = :plan FOR UPDATE")
    change = (await db.execute(check, {"id": change_id, "plan": plan_id})).fetchone()
    
    if not change or change.status not in (ChangeStatus.PENDING_PM, ChangeStatus.AWAITING_LEADER_ACCEPTANCE):
        raise HTTPException(status_code=400, detail="Usulan tidak ditemukan atau tidak dalam status pending.")
        
    emp_q = text("SELECT employee_id FROM vms.app_user WHERE id = :uid")
    my_emp = (await db.execute(emp_q, {"uid": current_user.user_id})).scalar()
    
    # Update change status
    upd_change = text("""
        UPDATE vms.plan_change 
        SET status = :effective, decided_by = :emp
        WHERE id = :id
    """)
    await db.execute(upd_change, {"emp": my_emp, "id": change_id, "effective": ChangeStatus.EFFECTIVE})
    
    # Apply logic based on type
    if change.change_type == ChangeType.EXTEND:
        # Update upper bound of period
        apply_ext = text("""
            UPDATE vms.work_plan 
            SET period = daterange(lower(period), upper(CAST(:new_period AS daterange)), '[)'),
                revision = revision + 1, row_version = row_version + 1
            WHERE id = :plan
        """)
        await db.execute(apply_ext, {"new_period": change.new_period, "plan": plan_id})
        # Baris anggota TIDAK diubah: anggota aktif = valid_period terbuka (is_plan_member), dan bentrok
        # jadwal dihitung dari work_plan.period. Memberi batas atas justru membuat anggota tidak aktif.
        
    elif change.change_type == ChangeType.PERSONNEL:
        # Penutupan baris anggota lama
        close_old = text("""
            WITH effective AS (
                SELECT GREATEST(lower(wp.period), (now() AT TIME ZONE o.timezone)::date) AS effective_date
                FROM vms.work_plan wp
                JOIN vms.organization o ON o.id = wp.organization_id
                WHERE wp.id = :plan
            )
            UPDATE vms.work_plan_member AS m
            SET valid_period = daterange(lower(m.valid_period), GREATEST(lower(m.valid_period), effective.effective_date), '[)')
            FROM effective
            WHERE m.work_plan_id = :plan AND m.role_in_plan = 'LEADER' AND upper_inf(m.valid_period)
        """)
        await db.execute(close_old, {"plan": plan_id})
        
        # Pembukaan baris anggota baru
        open_new = text("""
            INSERT INTO vms.work_plan_member (work_plan_id, employee_id, role_in_plan, valid_period)
            SELECT wp.id, :new_leader, 'LEADER', daterange(
                GREATEST(lower(wp.period), (now() AT TIME ZONE o.timezone)::date), NULL, '[)')
            FROM vms.work_plan wp
            JOIN vms.organization o ON o.id = wp.organization_id
            WHERE wp.id = :plan
        """)
        await db.execute(open_new, {"new_leader": change.proposed_leader_id, "plan": plan_id})
        
        # Update leader di work_plan
        upd_leader = text("UPDATE vms.work_plan SET leader_employee_id = :new_leader, revision = revision + 1, row_version = row_version + 1 WHERE id = :plan")
        await db.execute(upd_leader, {"new_leader": change.proposed_leader_id, "plan": plan_id})
        
    return {"message": "Adendum disetujui dan diterapkan."}
