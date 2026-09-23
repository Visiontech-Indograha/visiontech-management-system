import hashlib
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_db_with_user, require_permission
from app.core.permissions import Permission
from app.schemas.plan import WorkPlanResponse

router = APIRouter(prefix="/plans/{plan_id}", tags=["Work Plan Transitions"])

class TransitionRequest(BaseModel):
    row_version: int
    reason: str = ""

@router.post("/publish", response_model=WorkPlanResponse)
async def publish_plan(
    plan_id: UUID,
    data: TransitionRequest,
    current_user: CurrentUser = Depends(require_permission(Permission.PUBLISH_PLAN)),
    db: AsyncSession = Depends(get_db_with_user)
):
    # Cek status dan kunci
    check = text("SELECT status, row_version, revision FROM vms.work_plan WHERE id = :id FOR UPDATE")
    row = (await db.execute(check, {"id": plan_id})).fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="SK tidak ditemukan")
    if row.status not in ('DRAFT', 'APPEALED'):
        raise HTTPException(status_code=400, detail={"code": "INVALID_STATE", "message": "Hanya DRAFT atau APPEALED yang bisa di-publish."})
    if row.row_version != data.row_version:
        raise HTTPException(status_code=409, detail={"code": "CONFLICT", "message": "Dokumen ini telah diubah oleh orang lain."})
        
    # Validasi kelengkapan (Minimal 1 member (Leader), 1 day, 1 task)
    mem_check = text("SELECT count(*) FROM vms.work_plan_member WHERE work_plan_id = :id AND valid_to IS NULL")
    if (await db.execute(mem_check, {"id": plan_id})).scalar() < 1:
        raise HTTPException(status_code=400, detail="SK belum memiliki anggota aktif.")
        
    # Ambil snapshot
    snapshot_query = text("""
        SELECT 
            wp.*,
            (SELECT json_agg(row_to_json(wpm)) FROM vms.work_plan_member wpm WHERE wpm.work_plan_id = wp.id) as members,
            (SELECT json_agg(row_to_json(wpd)) FROM vms.work_plan_day wpd WHERE wpd.work_plan_id = wp.id) as days
        FROM vms.work_plan wp WHERE id = :id
    """)
    snapshot_raw = (await db.execute(snapshot_query, {"id": plan_id})).fetchone()
    snapshot_json = json.dumps(dict(snapshot_raw._mapping), default=str)
    snapshot_sha = hashlib.sha256(snapshot_json.encode('utf-8')).digest()
    
    # Dapatkan employee_id dari user_id
    emp_q = text("SELECT employee_id FROM vms.app_user WHERE id = :uid")
    my_emp = (await db.execute(emp_q, {"uid": current_user.user_id})).scalar()
    
    # 1. Update status
    upd = text("""
        UPDATE vms.work_plan 
        SET status = 'PUBLISHED', row_version = row_version + 1,
            number = COALESCE(number, 'SK-' || TO_CHAR(CURRENT_DATE, 'YYYYMM') || '-' || SUBSTR(id::text, 1, 4))
        WHERE id = :id
        RETURNING *
    """)
    res = await db.execute(upd, {"id": plan_id})
    plan_out = res.fetchone()
    
    # 2. Buat Dokumen (SK)
    doc_ins = text("""
        INSERT INTO vms.plan_document (
            work_plan_id, kind, version, number, status, 
            snapshot, snapshot_sha256, issued_by
        ) VALUES (
            :plan_id, 'SK', :rev, :num, 'AWAITING_ACCEPTANCE',
            :snap::jsonb, :hash, :emp
        )
    """)
    await db.execute(doc_ins, {
        "plan_id": plan_id, "rev": plan_out.revision,
        "num": plan_out.number, "snap": snapshot_json,
        "hash": snapshot_sha, "emp": my_emp
    })
    
    return WorkPlanResponse(**plan_out._mapping)

@router.post("/accept", response_model=WorkPlanResponse)
async def accept_plan(
    plan_id: UUID,
    data: TransitionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user)
):
    check = text("SELECT status, row_version, leader_employee_id FROM vms.work_plan WHERE id = :id FOR UPDATE")
    row = (await db.execute(check, {"id": plan_id})).fetchone()
    
    if not row or row.status != 'PUBLISHED':
        raise HTTPException(status_code=400, detail="Hanya status PUBLISHED yang bisa di-accept.")
        
    # Pastikan yang accept adalah Leader
    emp_q = text("SELECT employee_id FROM vms.app_user WHERE id = :uid")
    my_emp = (await db.execute(emp_q, {"uid": current_user.user_id})).scalar()
    
    if my_emp != row.leader_employee_id:
        raise HTTPException(status_code=403, detail="Hanya Leader yang dapat menerima SK.")
        
    upd = text("UPDATE vms.work_plan SET status = 'ACCEPTED', row_version = row_version + 1 WHERE id = :id RETURNING *")
    res = await db.execute(upd, {"id": plan_id})
    
    doc_upd = text("""
        UPDATE vms.plan_document 
        SET status = 'ACCEPTED', accepted_by = :emp, accepted_at = now()
        WHERE work_plan_id = :id AND status = 'AWAITING_ACCEPTANCE'
    """)
    await db.execute(doc_upd, {"emp": my_emp, "id": plan_id})
    
    return WorkPlanResponse(**res.fetchone()._mapping)

@router.post("/start", response_model=WorkPlanResponse)
async def start_plan(
    plan_id: UUID,
    data: TransitionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user)
):
    check = text("SELECT status FROM vms.work_plan WHERE id = :id FOR UPDATE")
    row = (await db.execute(check, {"id": plan_id})).fetchone()
    
    if not row or row.status != 'ACCEPTED':
        raise HTTPException(status_code=400, detail="Hanya status ACCEPTED yang bisa di-start.")
        
    upd = text("UPDATE vms.work_plan SET status = 'IN_PROGRESS', row_version = row_version + 1 WHERE id = :id RETURNING *")
    res = await db.execute(upd, {"id": plan_id})
    
    return WorkPlanResponse(**res.fetchone()._mapping)
