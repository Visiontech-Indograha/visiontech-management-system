from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_db_with_user, require_permission
from app.api.guards import ensure_same_org
from app.core.permissions import Permission
from app.schemas.attendance import (
    AttendanceResponse,
    CheckInRequest,
    CheckOutRequest,
    ExplanationRequest,
    ReviewRequest,
)

router = APIRouter(prefix="/attendance", tags=["Attendance"])

@router.post("/check-in", response_model=AttendanceResponse)
async def check_in(
    data: CheckInRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user)
):
    """P4-2: Absensi Check-In dengan validasi lokasi."""
    await ensure_same_org(db, current_user.organization_id, sites=[data.site_id], files=[data.selfie_file_id])
    emp_q = text("SELECT employee_id FROM vms.app_user WHERE id = :uid")
    emp_id = (await db.execute(emp_q, {"uid": current_user.user_id})).scalar()
    
    if not emp_id:
        raise HTTPException(status_code=400, detail="User tidak tertaut ke employee.")
        
    # Ambil site detail
    site_q = text("SELECT name, location, radius_m FROM vms.site WHERE id = :site AND organization_id = :org")
    site = (await db.execute(site_q, {"site": data.site_id, "org": current_user.organization_id})).fetchone()
    if not site:
        raise HTTPException(status_code=404, detail="Site tidak ditemukan.")
        
    radius = site.radius_m or 50
    
    # Cek jarak
    dist_q = text("SELECT ST_Distance(ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography, :site_loc) as dist")
    dist = (await db.execute(dist_q, {
        "lng": data.location.lng, "lat": data.location.lat, "site_loc": site.location
    })).scalar()
    
    # 09.00 dianggap terlambat. Di production harus ambil shift dari employee/unit
    now_ts = datetime.now()
    work_dt = now_ts.date()
    is_late = now_ts.hour >= 9 
    
    # Tentukan status berdasarkan fallback (K-030 face mismatch UX)
    status_val = 'AUTO_VALID'
    if dist > radius:
        status_val = 'NEEDS_REVIEW'  # Di luar radius
    if data.location_origin != 'GPS':
        status_val = 'NEEDS_REVIEW'  # Simulasi/Fake GPS
    
    # Apabila pemindaian wajah tidak cocok, beri kesempatan finance/HR me-review, BUKAN menolak absennya.
    if data.face_result in ('NO_MATCH', 'LOW_QUALITY'):
        status_val = 'NEEDS_REVIEW'
        
    ins = text("""
        INSERT INTO vms.attendance (
            organization_id, employee_id, work_date, site_id, site_label,
            check_in_at, location, location_origin, distance_m, radius_m,
            is_late, selfie_file_id, status, face_result, face_similarity
        ) VALUES (
            :org, :emp, :wdate, :site, :slabel, now(),
            ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), :orig, :dist, :rad,
            :late, :file, :status, :f_res, :f_sim
        ) RETURNING id, check_in_at, check_out_at, is_early_leave, explanation, reviewed_at
    """)
    try:
        res = await db.execute(ins, {
            "org": current_user.organization_id, "emp": emp_id, "wdate": work_dt,
            "site": data.site_id, "slabel": site.name, 
            "lng": data.location.lng, "lat": data.location.lat,
            "orig": data.location_origin, "dist": dist, "rad": radius,
            "late": is_late, "file": data.selfie_file_id, "status": status_val,
            "f_res": data.face_result, "f_sim": data.face_similarity
        })
        row = res.fetchone()
        
        return AttendanceResponse(
            id=row.id, employee_id=emp_id, work_date=work_dt, site_id=data.site_id,
            site_label=site.name, check_in_at=row.check_in_at, check_out_at=row.check_out_at,
            distance_m=dist, is_late=is_late, is_early_leave=row.is_early_leave,
            status=status_val, explanation=row.explanation, reviewed_at=row.reviewed_at
        )
    except Exception as e:
        if "attendance_active_uidx" in str(e):
            raise HTTPException(status_code=400, detail="Anda sudah melakukan absensi hari ini.")
        raise HTTPException(status_code=400, detail={"code": "DB_ERROR", "message": str(e)})

@router.post("/check-out", response_model=AttendanceResponse)
async def check_out(
    data: CheckOutRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user)
):
    emp_q = text("SELECT employee_id FROM vms.app_user WHERE id = :uid")
    emp_id = (await db.execute(emp_q, {"uid": current_user.user_id})).scalar()
    
    # Cari absensi hari ini yang masih belum check out
    now_ts = datetime.now()
    work_dt = now_ts.date()
    
    find_q = text("""
        SELECT id, site_id, radius_m, status 
        FROM vms.attendance 
        WHERE employee_id = :emp AND work_date = :wdate AND check_out_at IS NULL
    """)
    att = (await db.execute(find_q, {"emp": emp_id, "wdate": work_dt})).fetchone()
    
    if not att:
        raise HTTPException(status_code=400, detail="Tidak ada absensi aktif untuk di-check-out.")
        
    is_early = now_ts.hour < 17  # Asumsi 17.00
    new_status = att.status
    if data.location_origin != 'GPS' or is_early:
        new_status = 'NEEDS_REVIEW'
        
    upd = text("""
        UPDATE vms.attendance 
        SET check_out_at = now(), is_early_leave = :early, status = :status
        WHERE id = :id
        RETURNING *
    """)
    res = await db.execute(upd, {"early": is_early, "status": new_status, "id": att.id})
    row = res.fetchone()
    
    return AttendanceResponse(
        id=row.id, employee_id=emp_id, work_date=row.work_date, site_id=row.site_id,
        site_label=row.site_label, check_in_at=row.check_in_at, check_out_at=row.check_out_at,
        distance_m=row.distance_m, is_late=row.is_late, is_early_leave=row.is_early_leave,
        status=row.status, explanation=row.explanation, reviewed_at=row.reviewed_at
    )

@router.post("/{att_id}/explain")
async def explain_attendance(
    att_id: UUID,
    data: ExplanationRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user)
):
    """P4-4: Karyawan memberi penjelasan untuk absensi bermasalah — hanya absensinya sendiri (V-09)."""
    upd = text("""
        UPDATE vms.attendance SET explanation = :exp
        WHERE id = :id AND employee_id = (SELECT employee_id FROM vms.app_user WHERE id = :uid)
        RETURNING id
    """)
    res = await db.execute(upd, {"exp": data.explanation, "id": att_id, "uid": current_user.user_id})
    if not res.scalar():
        raise HTTPException(status_code=404, detail="Absensi tidak ditemukan.")
    return {"message": "Penjelasan ditambahkan."}

@router.post("/{att_id}/review")
async def review_attendance(
    att_id: UUID,
    data: ReviewRequest,
    current_user: CurrentUser = Depends(require_permission(Permission.REVIEW_ATTENDANCE)),
    db: AsyncSession = Depends(get_db_with_user)
):
    """P4-4: Review oleh Finance/HR."""
    status_val = 'APPROVED' if data.is_approved else 'REJECTED'
    
    emp_q = text("SELECT employee_id FROM vms.app_user WHERE id = :uid")
    my_emp = (await db.execute(emp_q, {"uid": current_user.user_id})).scalar()
    
    upd = text("""
        UPDATE vms.attendance 
        SET status = :status, reviewed_by = :emp, reviewed_at = now()
        WHERE id = :id AND organization_id = :org
        RETURNING id
    """)
    res = await db.execute(upd, {
        "status": status_val, "emp": my_emp, 
        "id": att_id, "org": current_user.organization_id
    })
    
    if not res.scalar():
        raise HTTPException(status_code=404, detail="Gagal me-review absensi.")
    return {"message": f"Absensi di-{status_val.lower()}."}

import csv
import io

from fastapi.responses import PlainTextResponse


@router.get("/export", response_class=PlainTextResponse)
async def export_attendance(
    start_date: date,
    end_date: date,
    current_user: CurrentUser = Depends(require_permission(Permission.REVIEW_ATTENDANCE)),
    db: AsyncSession = Depends(get_db_with_user)
):
    """P4-5: Ekspor CSV untuk Finance."""
    query = text("""
        SELECT a.work_date, e.employee_no, e.full_name, a.site_label, 
               a.check_in_at, a.check_out_at, a.status, a.is_late, a.is_early_leave
        FROM vms.attendance a
        JOIN vms.employee e ON a.employee_id = e.id
        WHERE a.organization_id = :org 
          AND a.work_date BETWEEN :start AND :end
        ORDER BY a.work_date ASC, e.full_name ASC
    """)
    rows = (await db.execute(query, {
        "org": current_user.organization_id, "start": start_date, "end": end_date
    })).fetchall()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Tanggal", "NIK", "Nama", "Lokasi", "Check In", "Check Out", "Terlambat", "Pulang Cepat", "Status"])
    
    for r in rows:
        check_in = r.check_in_at.strftime("%H:%M:%S") if r.check_in_at else ""
        check_out = r.check_out_at.strftime("%H:%M:%S") if r.check_out_at else ""
        writer.writerow([
            r.work_date.isoformat(), r.employee_no, r.full_name, r.site_label,
            check_in, check_out, "Ya" if r.is_late else "Tidak", 
            "Ya" if r.is_early_leave else "Tidak", r.status
        ])
        
    return output.getvalue()
