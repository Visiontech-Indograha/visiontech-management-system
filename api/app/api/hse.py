from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_db_with_user
from app.api.guards import (
    PlanAccess,
    PlanNeed,
    check_plan_access,
    day_plan_access,
    ensure_same_org,
    incident_plan_access,
)
from app.core.errors import ForbiddenError, ValidationError
from app.core.permissions import RoleCode
from app.repositories.org_clock_repo import OrgClockRepo
from app.schemas.hse import (
    DailyReportCreate,
    DailyReportResponse,
    IncidentCreate,
    IncidentResolve,
    IncidentResponse,
)

router = APIRouter(prefix="/hse", tags=["HSE & Reports"])
_INCIDENT_VIEW_ACCESS = Depends(incident_plan_access(PlanNeed.VIEW))
_DAY_LEADER_ACCESS = Depends(day_plan_access(PlanNeed.LEADER))  # domain.js SAVE/SUBMIT_REPORT


async def _ensure_day_reached(db: AsyncSession, day_id: UUID) -> None:
    """R6 · domain.js SAVE_REPORT/SUBMIT_REPORT: laporan hanya pada atau setelah tanggal pelaksanaan
    (tanggal server menurut zona waktu organisasi, V-10)."""
    if not await OrgClockRepo(db).day_reached(day_id):
        raise ValidationError("Laporan hanya dapat diisi pada atau setelah tanggal pelaksanaan.")

@router.post("/incidents", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def report_incident(
    data: IncidentCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user)
):
    # domain.js REPORT_INCIDENT: hanya ketua atau anggota pekerjaan ini (V-09). SK asing/tak terlihat → 404.
    await check_plan_access(db, data.work_plan_id, current_user, PlanNeed.LEADER_OR_MEMBER)
    await ensure_same_org(db, current_user.organization_id, files=data.evidence_file_ids)
    emp_q = text("SELECT employee_id FROM vms.app_user WHERE id = :uid")
    my_emp = (await db.execute(emp_q, {"uid": current_user.user_id})).scalar()

    # Tanggal insiden = hari ini menurut server & zona waktu organisasi (V-10, domain.js REPORT_INCIDENT
    # memakai tanggal sistem) — tanggal kiriman klien tidak dipakai.
    ins = text("""
        INSERT INTO vms.incident_report (
            organization_id, work_plan_id, reported_by, occurred_on,
            category, severity, description
        ) VALUES (
            :org, :plan, :emp, :occ, :cat, :sev, :desc
        ) RETURNING *
    """)
    today = (await OrgClockRepo(db).local_now(current_user.organization_id)).today
    res = await db.execute(ins, {
        "org": current_user.organization_id, "plan": data.work_plan_id,
        "emp": my_emp, "occ": today, "cat": data.category,
        "sev": data.severity, "desc": data.description
    })
    incident = res.fetchone()
    
    # Insert evidence
    if data.evidence_file_ids:
        ins_ev = text("INSERT INTO vms.incident_evidence (incident_id, file_id) VALUES (:inc, :fid)")
        for fid in data.evidence_file_ids:
            await db.execute(ins_ev, {"inc": incident.id, "fid": fid})
            
    return IncidentResponse(**incident._mapping)

@router.post("/incidents/{inc_id}/resolve", response_model=IncidentResponse)
async def resolve_incident(
    inc_id: UUID,
    data: IncidentResolve,
    access: PlanAccess = _INCIDENT_VIEW_ACCESS,
    db: AsyncSession = Depends(get_db_with_user)
):
    # domain.js RESOLVE_INCIDENT: PM (unit SK), OPS, ASSET. R2: PM unit lain tidak melihat SK ini → 404.
    current_user = access.user
    if not (access.manages or RoleCode.ASSET in current_user.roles):
        raise ForbiddenError("Hanya PM unit pekerjaan ini atau petugas aset yang dapat menyelesaikan insiden.")
    emp_q = text("SELECT employee_id FROM vms.app_user WHERE id = :uid")
    my_emp = (await db.execute(emp_q, {"uid": current_user.user_id})).scalar()
    
    upd = text("""
        UPDATE vms.incident_report
        SET status = 'RESOLVED', resolved_by = :emp, resolved_at = now(), resolution_note = :note
        WHERE id = :id AND organization_id = :org
        RETURNING *
    """)
    res = await db.execute(upd, {
        "emp": my_emp, "note": data.resolution_note,
        "id": inc_id, "org": current_user.organization_id
    })
    row = res.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Insiden tidak ditemukan.")
        
    return IncidentResponse(**row._mapping)

@router.post("/daily-reports/{day_id}", response_model=DailyReportResponse)
async def upsert_daily_report(
    day_id: UUID,
    data: DailyReportCreate,
    access: PlanAccess = _DAY_LEADER_ACCESS,
    db: AsyncSession = Depends(get_db_with_user)
):
    current_user = access.user
    await _ensure_day_reached(db, day_id)
    await ensure_same_org(db, current_user.organization_id, files=data.evidence_file_ids)
    emp_q = text("SELECT employee_id FROM vms.app_user WHERE id = :uid")
    my_emp = (await db.execute(emp_q, {"uid": current_user.user_id})).scalar()
    
    # Upsert
    ups = text("""
        INSERT INTO vms.daily_report (work_plan_day_id, body, obstacle)
        VALUES (:day, :body, :obs)
        ON CONFLICT (work_plan_day_id) DO UPDATE 
        SET body = EXCLUDED.body, obstacle = EXCLUDED.obstacle, updated_at = now()
        RETURNING *
    """)
    res = await db.execute(ups, {
        "day": day_id, "body": data.body, "obs": data.obstacle
    })
    report = res.fetchone()
    
    if data.evidence_file_ids:
        await db.execute(text("DELETE FROM vms.report_evidence WHERE daily_report_id = :rid"), {"rid": report.id})
        ins_ev = text("INSERT INTO vms.report_evidence (daily_report_id, file_id) VALUES (:rid, :fid)")
        for fid in data.evidence_file_ids:
            await db.execute(ins_ev, {"rid": report.id, "fid": fid})
            
    return DailyReportResponse(**report._mapping)

@router.post("/daily-reports/{day_id}/submit", response_model=DailyReportResponse)
async def submit_daily_report(
    day_id: UUID,
    access: PlanAccess = _DAY_LEADER_ACCESS,
    db: AsyncSession = Depends(get_db_with_user)
):
    current_user = access.user
    await _ensure_day_reached(db, day_id)
    emp_q = text("SELECT employee_id FROM vms.app_user WHERE id = :uid")
    my_emp = (await db.execute(emp_q, {"uid": current_user.user_id})).scalar()
    
    sub = text("""
        UPDATE vms.daily_report
        SET status = 'SUBMITTED', submitted_by = :emp, submitted_at = now()
        WHERE work_plan_day_id = :day AND status = 'DRAFT'
        RETURNING *
    """)
    try:
        res = await db.execute(sub, {"emp": my_emp, "day": day_id})
        report = res.fetchone()
        if not report:
            raise HTTPException(status_code=400, detail="Report tidak ditemukan atau bukan DRAFT.")
        return DailyReportResponse(**report._mapping)
    except Exception as e:
        if "check" in str(e).lower():
            raise HTTPException(status_code=400, detail="Laporan terlalu singkat (minimal 10 karakter).")
        raise HTTPException(status_code=400, detail={"code": "DB_ERROR", "message": str(e)})
