"""
Absensi lapangan. Tipis (dok 12 §2): aturan di services/attendance_session_service.py (V-12),
SQL di crud/crud_attendance_session.py; jarak/status/terlambat/pulang cepat diputuskan trigger.
"""
import csv
import io
from datetime import date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, ensure_same_org, get_current_user, get_db_with_user, require_permission
from app.core.permissions import Permission
from app.crud.crud_attendance_session import CRUDAttendanceSession
from app.crud.crud_org_clock import CRUDOrgClock
from app.schemas.attendance import (
    AttendanceListResponse,
    AttendanceResponse,
    CheckInRequest,
    CheckOutRequest,
    ExplanationRequest,
    ReviewRequest,
)
from app.services.attendance_session_service import AttendanceSessionService

router = APIRouter(prefix="/attendance", tags=["Attendance"])


def _service(db: AsyncSession) -> AttendanceSessionService:
    return AttendanceSessionService(CRUDAttendanceSession(db), CRUDOrgClock(db))


def _response(row: Any) -> AttendanceResponse:
    return AttendanceResponse(**row._mapping)


@router.get("", response_model=AttendanceListResponse)
async def list_attendance(
    employee_id: UUID | None = None,
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    status: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user)
) -> AttendanceListResponse:
    """Dok 05 §3.5. FINANCE/HR/OPS/ADMIN: seluruh organisasi; lainnya: hanya milik sendiri.
    Filter `plan_id` di dok 05 belum didukung — absensi belum tertaut ke SK (dok 10 Bagian C)."""
    service = _service(db)
    rows, total = await service.list_attendance(
        current_user.organization_id, current_user.user_id, current_user.roles,
        employee_id=employee_id, date_from=date_from, date_to=date_to, status=status, page=page, size=size)
    return AttendanceListResponse(items=[_response(r) for r in rows], total=total, page=page, size=size,
                                  today=await service.today(current_user.organization_id))


@router.post("/check-in", response_model=AttendanceResponse)
async def check_in(
    data: CheckInRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user)
) -> AttendanceResponse:
    """P4-2 · domain.js CHECK_IN. Waktu, tanggal, jarak, dan status dari server (aturan inti #3)."""
    await ensure_same_org(db, current_user.organization_id, sites=[data.site_id], files=[data.selfie_file_id])
    row = await _service(db).check_in(
        current_user.organization_id, current_user.user_id, site_id=data.site_id,
        lng=data.location.lng, lat=data.location.lat, origin=data.location_origin,
        accuracy_m=data.accuracy_m, selfie_file_id=data.selfie_file_id, face_result=data.face_result, face_similarity=data.face_similarity,
    )
    return _response(row)


@router.post("/check-out", response_model=AttendanceResponse)
async def check_out(
    data: CheckOutRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user)
) -> AttendanceResponse:
    """domain.js CHECK_OUT — menutup sesi terbuka milik sendiri."""
    return _response(await _service(db).check_out(current_user.user_id))


@router.post("/{att_id}/explain")
async def explain_attendance(
    att_id: UUID,
    data: ExplanationRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user)
) -> dict[str, str]:
    """P4-4 · domain.js EXPLAIN_ATTENDANCE — hanya absensi sendiri yang menunggu pemeriksaan."""
    await _service(db).explain_attendance(current_user.organization_id, current_user.user_id, att_id, data.explanation)
    return {"message": "Penjelasan ditambahkan."}


@router.post("/{att_id}/review")
async def review_attendance(
    att_id: UUID,
    data: ReviewRequest,
    current_user: CurrentUser = Depends(require_permission(Permission.REVIEW_UNIT_ATTENDANCE)),
    db: AsyncSession = Depends(get_db_with_user)
) -> dict[str, str]:
    """P4-4 · domain.js REVIEW_ATTENDANCE: Finance seluruh organisasi; PM unitnya, OPS lintas unit (R-10)."""
    status = await _service(db).review_attendance(
        current_user.organization_id, current_user.user_id, att_id, data.is_approved, data.note,
        review_all=Permission.REVIEW_ATTENDANCE in current_user.permissions)
    return {"message": f"Absensi di-{status.lower()}."}


@router.get("/export", response_class=PlainTextResponse)
async def export_attendance(
    start_date: date,
    end_date: date,
    current_user: CurrentUser = Depends(require_permission(Permission.REVIEW_ATTENDANCE)),
    db: AsyncSession = Depends(get_db_with_user)
) -> str:
    """P4-5: Ekspor CSV untuk Finance. Jam dalam zona waktu organisasi (sebelumnya tercetak UTC)."""
    query = text("""
        SELECT a.work_date, e.employee_no, e.full_name, a.site_label,
               to_char(a.check_in_at AT TIME ZONE o.timezone, 'HH24:MI:SS') AS check_in,
               to_char(a.check_out_at AT TIME ZONE o.timezone, 'HH24:MI:SS') AS check_out,
               a.status, a.is_late, a.is_early_leave
        FROM vms.attendance a
        JOIN vms.employee e ON a.employee_id = e.id
        JOIN vms.organization o ON o.id = a.organization_id
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
        writer.writerow([
            r.work_date.isoformat(), r.employee_no, r.full_name, r.site_label,
            r.check_in or "", r.check_out or "", "Ya" if r.is_late else "Tidak",
            "Ya" if r.is_early_leave else "Tidak", r.status
        ])

    return output.getvalue()
