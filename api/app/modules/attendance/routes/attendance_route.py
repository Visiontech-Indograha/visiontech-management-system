"""
app/modules/attendance/routes/attendance_route.py

Rute endpoint HTTP untuk absensi lapangan dan luring (/attendance).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse

from app.api.deps import (
    get_current_user,
    require_permission,
)
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.attendance.controllers.attendance_controller import AttendanceController
from app.modules.attendance.schemas.attendance_schema import (
    AttendanceListResponse,
    AttendanceResponse,
    CheckInRequest,
    CheckOutRequest,
    DeviceKeyRequest,
    ExplanationRequest,
    OfflineAttendanceEvent,
    OfflineAttendanceResult,
    ReviewRequest,
)

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.get("", response_model=AttendanceListResponse)
async def list_attendance(
    employee_id: UUID | None = None,
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    status: str | None = None,
    scope: str = Query("all", pattern="^(all|mine|team)$"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = Depends(get_current_user),
    controller: AttendanceController = Depends(),
) -> AttendanceListResponse:
    """
    Dok 05 §3.5 · R-33: Finance & OPS seluruh organisasi; PM miliknya + bawahan lapangan di unitnya;
    lainnya hanya milik sendiri. Filter `plan_id` di dok 05 belum didukung (dok 10 Bagian C).
    """
    return await controller.handle_list_attendance(
        current_user,
        employee_id=employee_id,
        date_from=date_from,
        date_to=date_to,
        status=status,
        scope=scope,
        page=page,
        size=size,
    )


@router.post("/device-key")
async def register_device_key(
    data: DeviceKeyRequest,
    current_user: CurrentUser = Depends(get_current_user),
    controller: AttendanceController = Depends(),
) -> dict[str, str]:
    """
    R-34: daftarkan kunci publik Android Keystore perangkat ini untuk memverifikasi absen luring.
    """
    return await controller.handle_register_device_key(current_user, data)


@router.post("/offline", response_model=OfflineAttendanceResult)
async def submit_offline_attendance(
    data: OfflineAttendanceEvent,
    current_user: CurrentUser = Depends(get_current_user),
    controller: AttendanceController = Depends(),
) -> OfflineAttendanceResult:
    """
    R-34: terima satu absen luring yang ditandatangani perangkat (idempoten per client_op_id).
    """
    return await controller.handle_submit_offline(current_user, data)


@router.post("/check-in", response_model=AttendanceResponse)
async def check_in(
    data: CheckInRequest,
    current_user: CurrentUser = Depends(get_current_user),
    controller: AttendanceController = Depends(),
) -> AttendanceResponse:
    """
    P4-2 · domain.js CHECK_IN. Waktu, tanggal, jarak, dan status dari server (aturan inti #3).
    Pekerja lapangan lewat HP (`channel` MOBILE), pekerja kantor lewat web (`channel` WEB).
    """
    return await controller.handle_check_in(current_user, data)


@router.post("/check-out", response_model=AttendanceResponse)
async def check_out(
    data: CheckOutRequest,
    current_user: CurrentUser = Depends(get_current_user),
    controller: AttendanceController = Depends(),
) -> AttendanceResponse:
    """
    domain.js CHECK_OUT — menutup sesi terbuka milik sendiri, dari kanal sesuai jenis pekerja.
    """
    return await controller.handle_check_out(current_user, data)


@router.post("/{att_id}/explain")
async def explain_attendance(
    att_id: UUID,
    data: ExplanationRequest,
    current_user: CurrentUser = Depends(get_current_user),
    controller: AttendanceController = Depends(),
) -> dict[str, str]:
    """
    P4-4 · domain.js EXPLAIN_ATTENDANCE — hanya absensi sendiri yang menunggu pemeriksaan.
    """
    return await controller.handle_explain(current_user, att_id, data)


@router.post("/{att_id}/review")
async def review_attendance(
    att_id: UUID,
    data: ReviewRequest,
    current_user: CurrentUser = Depends(require_permission(Permission.REVIEW_ATTENDANCE)),
    controller: AttendanceController = Depends(),
) -> dict[str, str]:
    """
    P4-4 · domain.js REVIEW_ATTENDANCE · R-33: PM → bawahan lapangan, Finance → kantor non-Finance,
    OPS → Finance; tidak pernah absensi sendiri.
    """
    return await controller.handle_review(current_user, att_id, data)


@router.get("/export", response_class=PlainTextResponse)
async def export_attendance(
    start_date: date,
    end_date: date,
    current_user: CurrentUser = Depends(require_permission(Permission.EXPORT_ATTENDANCE)),
    controller: AttendanceController = Depends(),
) -> str:
    """
    P4-5: Ekspor CSV untuk Finance. Jam dalam zona waktu organisasi (sebelumnya tercetak UTC).
    """
    return await controller.handle_export(current_user, start_date, end_date)


__all__ = ["router"]
