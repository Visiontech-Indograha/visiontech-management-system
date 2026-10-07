from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_with_user, incident_plan_access, plan_day_access
from app.core.enums import PlanStatus
from app.core.errors import AppError, ForbiddenError, NotFoundError, ValidationError
from app.core.permissions import RoleCode
from app.core.security import CurrentUser
from app.crud.crud_org_clock import CRUDOrgClock
from app.schemas.hse import (
    DailyReportCreate,
    DailyReportResponse,
    IncidentCreate,
    IncidentResolve,
    IncidentResponse,
    ReportReviewRequest,
)
from app.services.access_service import (
    PlanAccess,
    PlanNeed,
    check_plan_access,
    ensure_same_org,
    require_plan_status,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/hse", tags=["HSE & Reports"])
_INCIDENT_VIEW_ACCESS = Depends(incident_plan_access(PlanNeed.VIEW))
_DAY_LEADER_ACCESS = Depends(plan_day_access(PlanNeed.LEADER))  # domain.js SAVE/SUBMIT_REPORT
_DAY_PM_UNIT_ACCESS = Depends(plan_day_access(PlanNeed.PM_UNIT))  # domain.js REVIEW_REPORT
# Laporan harian di bawah SK-nya (dok 05 §3.6, V-16); sebelumnya /hse/daily-reports/{day_id}.
days_router = APIRouter(prefix="/work-plans/{plan_id}/days", tags=["Daily Reports"])


async def _ensure_day_reached(db: AsyncSession, day_id: UUID) -> None:
    """R6 · domain.js SAVE_REPORT/SUBMIT_REPORT: laporan hanya pada atau setelah tanggal pelaksanaan
    (tanggal server menurut zona waktu organisasi, V-10)."""
    if not await CRUDOrgClock(db).day_reached(day_id):
        raise ValidationError("Laporan hanya dapat diisi pada atau setelah tanggal pelaksanaan.")

@router.get("/incidents", response_model=list[IncidentResponse])
async def list_incidents(
    plan_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user)
) -> list[IncidentResponse]:
    """
    Mendapatkan daftar insiden untuk satu Surat Kerja (SK).
    Menampilkan insiden terbaru di urutan awal.
    SK asing/tak terlihat → 404.

    Query params:
    - plan_id: UUID dari Surat Kerja

    Return: Daftar insiden (list[IncidentResponse])
    """
    # Memeriksa hak akses user untuk melihat SK terkait menggunakan dependensi dan fungsi utilitas
    await check_plan_access(db, plan_id, current_user, PlanNeed.VIEW)
    # Menjalankan query pada database sesi untuk mendapatkan list insiden organisasi
    rows = (await db.execute(text("""
        SELECT ir.id, ir.work_plan_id, ir.reported_by, ir.occurred_on, ir.category, ir.severity,
               ir.description, ir.status, ir.resolved_by, ir.resolved_at, ir.resolution_note, ir.created_at,
               COALESCE(ARRAY(SELECT ie.file_id FROM vms.incident_evidence ie WHERE ie.incident_id = ir.id),
                        '{}') AS evidence_file_ids
        FROM vms.incident_report ir
        WHERE ir.work_plan_id = :plan AND ir.organization_id = :org
        ORDER BY ir.created_at DESC
    """), {"plan": plan_id, "org": current_user.organization_id})).fetchall()
    return [IncidentResponse(**r._mapping) for r in rows]


@router.post("/incidents", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def report_incident(
    data: IncidentCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user)
) -> IncidentResponse:
    """
    Melaporkan insiden baru untuk SK yang sedang berlangsung.
    (Hanya ketua atau anggota pekerjaan ini, SK harus IN_PROGRESS).

    Body params:
    - data: Detail insiden yang dilaporkan (IncidentCreate)

    Return: Detail insiden yang direkam (IncidentResponse)
    """
    # Menggunakan dependensi db dan current_user
    # domain.js REPORT_INCIDENT: hanya ketua atau anggota pekerjaan ini (V-09). SK asing/tak terlihat → 404.
    standing = await check_plan_access(db, data.work_plan_id, current_user, PlanNeed.LEADER_OR_MEMBER)
    require_plan_status(standing, PlanStatus.IN_PROGRESS)  # domain.js REPORT_INCIDENT (V-11)
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
        ) RETURNING id, work_plan_id, reported_by, occurred_on, category, severity,
                    description, status, resolved_by, resolved_at, resolution_note, created_at
    """)
    today = (await CRUDOrgClock(db).local_now(current_user.organization_id)).today
    res = await db.execute(ins, {
        "org": current_user.organization_id, "plan": data.work_plan_id,
        "emp": my_emp, "occ": today, "cat": data.category,
        "sev": data.severity, "desc": data.description
    })
    incident = res.one()

    # Insert evidence
    if data.evidence_file_ids:
        ins_ev = text("""
            INSERT INTO vms.incident_evidence (incident_id, file_id)
            SELECT :inc, unnest(CAST(:fids AS uuid[]))
        """)
        await db.execute(ins_ev, {"inc": incident.id, "fids": [str(f) for f in data.evidence_file_ids]})

    return IncidentResponse(**incident._mapping)

@router.post("/incidents/{inc_id}/resolve", response_model=IncidentResponse)
async def resolve_incident(
    inc_id: UUID,
    data: IncidentResolve,
    access: PlanAccess = _INCIDENT_VIEW_ACCESS,
    db: AsyncSession = Depends(get_db_with_user)
) -> IncidentResponse:
    """
    Menyelesaikan masalah insiden. Hanya PM (unit SK), OPS, atau ASSET yang bisa mengeksekusi.

    Path params:
    - inc_id: UUID dari insiden

    Body params:
    - data: Catatan resolusi (IncidentResolve)

    Return: Detail insiden yang telah diselesaikan (IncidentResponse)
    """
    # Injeksi dependensi kontrol akses Plan (_INCIDENT_VIEW_ACCESS) dan db sesi
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
        RETURNING id, work_plan_id, reported_by, occurred_on, category, severity,
                  description, status, resolved_by, resolved_at, resolution_note, created_at,
                  COALESCE(ARRAY(SELECT ie.file_id FROM vms.incident_evidence ie
                                 WHERE ie.incident_id = vms.incident_report.id), '{}') AS evidence_file_ids
    """)
    res = await db.execute(upd, {
        "emp": my_emp, "note": data.resolution_note,
        "id": inc_id, "org": current_user.organization_id
    })
    row = res.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Insiden tidak ditemukan.")

    return IncidentResponse(**row._mapping)

@days_router.put("/{day_id}", response_model=DailyReportResponse)
async def upsert_daily_report(
    day_id: UUID,
    data: DailyReportCreate,
    access: PlanAccess = _DAY_LEADER_ACCESS,
    db: AsyncSession = Depends(get_db_with_user)
) -> DailyReportResponse:
    """
    Membuat atau memperbarui DRAFT laporan harian pekerjaan (Hanya Ketua Tim, SK IN_PROGRESS).

    Path params:
    - plan_id: UUID dari SK (di-routing)
    - day_id: UUID hari pelaksanaan SK

    Body params:
    - data: Data laporan harian (DailyReportCreate)

    Return: Laporan harian (DailyReportResponse)
    """
    # Menggunakan injeksi dependensi access Plan (_DAY_LEADER_ACCESS)
    current_user = access.user
    require_plan_status(access, PlanStatus.IN_PROGRESS)  # domain.js SAVE/SUBMIT_REPORT (V-11)
    await _ensure_day_reached(db, day_id)
    await ensure_same_org(db, current_user.organization_id, files=data.evidence_file_ids)
    emp_q = text("SELECT employee_id FROM vms.app_user WHERE id = :uid")
    my_emp = (await db.execute(emp_q, {"uid": current_user.user_id})).scalar()

    # Upsert — hanya selagi DRAFT / CHANGES_REQUESTED (domain.js SAVE_REPORT, V-24)
    ups = text("""
        INSERT INTO vms.daily_report (work_plan_day_id, body, obstacle)
        VALUES (:day, :body, :obs)
        ON CONFLICT (work_plan_day_id) DO UPDATE
        SET body = EXCLUDED.body, obstacle = EXCLUDED.obstacle, updated_at = now()
        WHERE vms.daily_report.status IN ('DRAFT', 'CHANGES_REQUESTED')
        RETURNING id, work_plan_day_id, status, body, obstacle, submitted_by, submitted_at, reviewed_at, resubmitted
    """)
    res = await db.execute(ups, {
        "day": day_id, "body": data.body, "obs": data.obstacle
    })
    report = res.fetchone()
    if report is None:
        raise AppError("INVALID_STATE", "Laporan yang sudah diserahkan tidak dapat diubah.", status=409)

    if data.evidence_file_ids:
        await db.execute(text("DELETE FROM vms.report_evidence WHERE daily_report_id = :rid"), {"rid": report.id})
        ins_ev = text("""
            INSERT INTO vms.report_evidence (daily_report_id, file_id)
            SELECT :rid, unnest(CAST(:fids AS uuid[]))
        """)
        await db.execute(ins_ev, {"rid": report.id, "fids": [str(f) for f in data.evidence_file_ids]})

    return DailyReportResponse(**report._mapping)

@days_router.post("/{day_id}/submit", response_model=DailyReportResponse)
async def submit_daily_report(
    day_id: UUID,
    access: PlanAccess = _DAY_LEADER_ACCESS,
    db: AsyncSession = Depends(get_db_with_user)
) -> DailyReportResponse:
    """
    Menyerahkan (submit) laporan harian yang berstatus DRAFT atau minta revisi ke manajer/PM.

    Path params:
    - plan_id: UUID dari SK
    - day_id: UUID hari pelaksanaan SK

    Return: Laporan harian dengan status tersubmit (DailyReportResponse)
    """
    # Mengambil objek kontrol akses Plan (ketua tim) lewat dependensi
    current_user = access.user
    require_plan_status(access, PlanStatus.IN_PROGRESS)  # domain.js SAVE/SUBMIT_REPORT (V-11)
    await _ensure_day_reached(db, day_id)
    emp_q = text("SELECT employee_id FROM vms.app_user WHERE id = :uid")
    my_emp = (await db.execute(emp_q, {"uid": current_user.user_id})).scalar()

    # Ajukan dari DRAFT atau setelah dikembalikan PM (domain.js SUBMIT_REPORT, V-24)
    sub = text("""
        UPDATE vms.daily_report
        SET status = 'SUBMITTED', submitted_by = :emp, submitted_at = now(),
            resubmitted = resubmitted OR status = 'CHANGES_REQUESTED'   -- "Dikirim ulang" (alur SK v2)
        WHERE work_plan_day_id = :day AND status IN ('DRAFT', 'CHANGES_REQUESTED')
        RETURNING id, work_plan_day_id, status, body, obstacle, submitted_by, submitted_at, reviewed_at, resubmitted
    """)
    try:
        res = await db.execute(sub, {"emp": my_emp, "day": day_id})
    except Exception as e:
        if "check" in str(e).lower():
            raise HTTPException(status_code=400, detail="Laporan terlalu singkat (minimal 10 karakter).")
        raise HTTPException(status_code=400, detail={"code": "DB_ERROR", "message": str(e)})
    report = res.fetchone()
    if not report:
        raise AppError("INVALID_STATE", "Laporan sudah diserahkan atau belum dibuat.", status=409)
    await NotificationService(db).report_submitted(access.plan.id, "Laporan harian", bool(report.resubmitted))
    return DailyReportResponse(**report._mapping)




@days_router.post("/{day_id}/review", response_model=DailyReportResponse)
async def review_daily_report(
    day_id: UUID,
    data: ReportReviewRequest,
    access: PlanAccess = _DAY_PM_UNIT_ACCESS,
    db: AsyncSession = Depends(get_db_with_user)
) -> DailyReportResponse:
    """
    domain.js REVIEW_REPORT (V-24): PM unit/OPS menyetujui atau mengembalikan laporan harian yang diserahkan.

    Path params:
    - plan_id: UUID dari SK
    - day_id: UUID hari pelaksanaan SK

    Body params:
    - data: Data hasil review laporan (ReportReviewRequest)

    Return: Detail laporan harian pasca-review (DailyReportResponse)
    """
    # Menggunakan injeksi dependensi access PM Unit (_DAY_PM_UNIT_ACCESS)
    require_plan_status(access, PlanStatus.IN_PROGRESS, PlanStatus.COMPLETION_REVIEW)
    if data.decision not in ("APPROVE", "RETURN"):
        raise ValidationError("Keputusan tidak valid.")
    note = (data.note or "").strip()
    if data.decision == "RETURN" and not note:
        raise ValidationError("Catatan revisi wajib diisi.")
    upd = text("""
        UPDATE vms.daily_report
        SET status = CAST(:status AS vms.report_status), review_note = :note, reviewed_at = now(),
            reviewed_by = (SELECT employee_id FROM vms.app_user WHERE id = :uid)
        WHERE work_plan_day_id = :day AND status = 'SUBMITTED'
        RETURNING id, work_plan_day_id, status, body, obstacle, submitted_by, submitted_at, reviewed_at, resubmitted
    """)
    report = (await db.execute(upd, {
        "status": "APPROVED" if data.decision == "APPROVE" else "CHANGES_REQUESTED",
        "note": note or None, "uid": access.user.user_id, "day": day_id,
    })).fetchone()
    if report is None:
        raise AppError("INVALID_STATE", "Laporan belum menunggu pemeriksaan.", status=409)
    # Memanggil service Notifikasi di layer terpisah
    await NotificationService(db).report_reviewed(access.plan.id, "Laporan harian", data.decision == "APPROVE", note or None)
    return DailyReportResponse(**report._mapping)


@days_router.post("/{day_id}/tasks/{task_id}/toggle")
async def toggle_task(
    day_id: UUID,
    task_id: UUID,
    access: PlanAccess = _DAY_LEADER_ACCESS,
    db: AsyncSession = Depends(get_db_with_user)
) -> dict[str, object]:
    """
    domain.js TOGGLE_TASK (V-23): ketua mencentang/menghapus centang tugas hari tersebut, selama laporan belum diserahkan.

    Path params:
    - plan_id: UUID SK (di-routing)
    - day_id: UUID hari eksekusi
    - task_id: UUID tugas yang dicentang

    Return: Status toggle (is_done) dari tugas tersebut
    """
    # Injeksi db dan level akses ketua tim
    require_plan_status(access, PlanStatus.IN_PROGRESS)
    await _ensure_day_reached(db, day_id)
    report_status = (await db.execute(text(
        "SELECT status FROM vms.daily_report WHERE work_plan_day_id = :day"), {"day": day_id})).scalar()
    if report_status in ("SUBMITTED", "APPROVED"):
        raise AppError("INVALID_STATE", "Checklist tidak dapat diubah setelah laporan diserahkan.", status=409)
    row = (await db.execute(text("""
        UPDATE vms.work_plan_task
           SET is_done = NOT is_done,
               done_at = CASE WHEN is_done THEN NULL ELSE now() END,
               done_by = CASE WHEN is_done THEN NULL
                              ELSE (SELECT employee_id FROM vms.app_user WHERE id = :uid) END
         WHERE id = :task AND work_plan_day_id = :day
        RETURNING id, is_done
    """), {"task": task_id, "day": day_id, "uid": access.user.user_id})).fetchone()
    if row is None:
        raise NotFoundError("Tugas")
    return {"id": str(row.id), "is_done": row.is_done}
