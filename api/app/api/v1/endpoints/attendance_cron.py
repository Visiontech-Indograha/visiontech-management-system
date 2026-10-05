"""
Tugas terjadwal pemantauan absensi (P4-9, dok 17 §5.3). Dipanggil penjadwal dengan token ADMIN.
"""
from fastapi import APIRouter, Depends

from app.api.deps import get_attendance_monitor_service, require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.schemas.attendance import MissingCheckInResponse, NeedsReviewResponse
from app.services.attendance_monitor_service import AttendanceMonitorService

router = APIRouter(prefix="/cron/attendance", tags=["Attendance Cron"])






@router.post("/alert-missing", response_model=MissingCheckInResponse)
async def alert_missing_checkin(
    current_user: CurrentUser = Depends(require_permission(Permission.RUN_SYSTEM_JOBS)),
    attendance_monitor_service: AttendanceMonitorService = Depends(get_attendance_monitor_service),
) -> MissingCheckInResponse:
    """
    Pemicu cron untuk memeriksa absensi check-in yang belum dilakukan pada hari berjalan, 
    kemudian mengirim peringatan jika ditemukan.
    
    Return: Detail peringatan (MissingCheckInResponse)
    """
    # Mengambil dependensi penjadwal dengan hak akses (RUN_SYSTEM_JOBS)
    # Memanggil attendance_monitor_service untuk melakukan evaluasi dan alert ke user
    result = await attendance_monitor_service.check_missing_check_ins(
        current_user.organization_id
    )
    return MissingCheckInResponse(alerted=result.alerted, check_ins_today=result.check_ins_today)


@router.post("/alert-needs-review", response_model=NeedsReviewResponse)
async def alert_needs_review_spike(
    current_user: CurrentUser = Depends(require_permission(Permission.RUN_SYSTEM_JOBS)),
    attendance_monitor_service: AttendanceMonitorService = Depends(get_attendance_monitor_service),
) -> NeedsReviewResponse:
    """
    Pemicu cron untuk mendeteksi lonjakan absensi yang memerlukan review (P4-9, dok 17 §5.3)
    dan memperingatkan manajer terkait.
    
    Return: Ringkasan hasil pemeriksaan dan jumlah review (NeedsReviewResponse)
    """
    # Injeksi dependensi untuk mendapatkan AttendanceMonitorService
    # Meneruskan operasi pengecekan lonjakan review ke service layer
    result = await attendance_monitor_service.check_needs_review_spike(
        current_user.organization_id
    )
    return NeedsReviewResponse(
        alerted=result.alerted,
        needs_review_today=result.needs_review_today,
        daily_average=result.daily_average,
    )
