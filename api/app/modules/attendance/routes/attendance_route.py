"""
app/modules/attendance/routes/attendance_route.py

Rute endpoint HTTP untuk absensi lapangan dan offline (/attendance).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse

from app.api.deps import get_current_user, require_permission
from app.core.list_params import check_date_range
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.attendance.controllers.attendance_controller import AttendanceController
from app.modules.attendance.schemas.attendance_schema import (
    AttendanceAdminPatch,
    AttendanceListResponse,
    AttendanceResponse,
    CheckInRequest,
    CheckOutRequest,
    DeviceKeyRequest,
    EvidenceRequest,
    ExplanationRequest,
    MealAllowanceRow,
    MyRecapResponse,
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
    status: str | None = Query(None, max_length=30),
    scope: str = Query("all", pattern="^(all|mine|team)$"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    q: str | None = Query(None, max_length=100, description="Nama atau NIP karyawan diawali kata kunci"),
    current_user: CurrentUser = Depends(get_current_user),
    controller: AttendanceController = Depends(),
) -> AttendanceListResponse:
    """
    Dok 05 §3.5 · R-33: Finance & OPS seluruh organisasi; PM miliknya + bawahan lapangan di unitnya;
    lainnya hanya milik sendiri. Filter `plan_id` di dok 05 belum didukung (dok 10 Bagian C).
    """
    check_date_range(date_from, date_to, start_name="from", end_name="to")
    return await controller.handle_list_attendance(
        current_user,
        employee_id=employee_id,
        date_from=date_from,
        date_to=date_to,
        status=status,
        scope=scope,
        page=page,
        size=size,
        q=q,
    )


@router.post("/device-key")
async def register_device_key(
    data: DeviceKeyRequest,
    current_user: CurrentUser = Depends(get_current_user),
    controller: AttendanceController = Depends(),
) -> dict[str, str]:
    """
    R-34: daftarkan kunci publik Android Keystore perangkat ini untuk memverifikasi absen offline.
    """
    return await controller.handle_register_device_key(current_user, data)


@router.post("/offline", response_model=OfflineAttendanceResult)
async def submit_offline_attendance(
    data: OfflineAttendanceEvent,
    current_user: CurrentUser = Depends(get_current_user),
    controller: AttendanceController = Depends(),
) -> OfflineAttendanceResult:
    """
    R-34: terima satu absen offline yang ditandatangani perangkat (idempoten per client_op_id).
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


@router.post("/{att_id}/evidence")
async def attach_evidence(
    att_id: UUID,
    data: EvidenceRequest,
    current_user: CurrentUser = Depends(get_current_user),
    controller: AttendanceController = Depends(),
) -> dict[str, str]:
    """Foto bukti biasa (terlambat / di luar radius) untuk absensi sendiri, tanpa pencocokan wajah."""
    return await controller.handle_evidence(current_user, att_id, data)


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


@router.patch("/{att_id}")
async def admin_patch_attendance(
    att_id: UUID,
    data: AttendanceAdminPatch,
    current_user: CurrentUser = Depends(require_permission(Permission.DELETE_ANY)),
    controller: AttendanceController = Depends(),
) -> dict[str, str]:
    """Koreksi jam/status absensi — hanya SUPER_ADMIN; alasan wajib dan dicatat di audit."""
    return await controller.handle_admin_patch(current_user, att_id, data)


@router.delete("/{att_id}")
async def admin_delete_attendance(
    att_id: UUID,
    current_user: CurrentUser = Depends(require_permission(Permission.DELETE_ANY)),
    controller: AttendanceController = Depends(),
) -> dict[str, str]:
    """Hapus permanen satu absensi — hanya SUPER_ADMIN."""
    return await controller.handle_admin_delete(current_user, att_id)


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
    check_date_range(start_date, end_date, start_name="start_date", end_name="end_date")
    return await controller.handle_export(current_user, start_date, end_date)


@router.get("/meal-allowance", response_model=list[MealAllowanceRow])
async def meal_allowance_recap(
    start_date: date,
    end_date: date,
    division_id: UUID | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    controller: AttendanceController = Depends(),
) -> list[MealAllowanceRow]:
    """Rekap uang makan per karyawan dari absensi sah: pengelola absensi semua divisi, PM divisinya."""
    return await controller.handle_meal_allowance(current_user, start_date, end_date, division_id)


@router.get("/me/recap", response_model=MyRecapResponse)
async def my_recap(
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$", description="Bulan YYYY-MM (default: bulan ini WIB)"),
    current_user: CurrentUser = Depends(get_current_user),
    controller: AttendanceController = Depends(),
) -> MyRecapResponse:
    """Rekap absensi bulanan milik sendiri: hadir, terlambat, pulang awal, uang makan."""
    return await controller.handle_my_recap(current_user, month)


__all__ = ["router"]
