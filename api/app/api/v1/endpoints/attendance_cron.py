"""
Tugas terjadwal pemantauan absensi (P4-9, dok 17 §5.3). Dipanggil penjadwal dengan token ADMIN.
"""
from fastapi import APIRouter, Depends

from app.api.deps import get_attendance_monitor_service, get_attendance_session_service, require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.schemas.attendance import MissingCheckInResponse, NeedsReviewResponse
from app.services.attendance_monitor_service import AttendanceMonitorService
from app.services.attendance_session_service import AttendanceSessionService

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


@router.post("/reverify-faces")
async def reverify_pending_faces(
    limit: int = 50,
    current_user: CurrentUser = Depends(require_permission(Permission.RUN_SYSTEM_JOBS)),
    attendance_session_service: AttendanceSessionService = Depends(get_attendance_session_service),
) -> dict[str, int]:
    """
    Penjadwal: hitung dan cocokkan ulang wajah yang tertunda saat face-service sempat mati.
    """
    done, left = await attendance_session_service.reverify_faces(limit=limit)
    return {"done": done, "remaining": left}


@router.post("/purge-face-probes")
async def purge_expired_face_probes(
    current_user: CurrentUser = Depends(require_permission(Permission.RUN_SYSTEM_JOBS)),
    attendance_session_service: AttendanceSessionService = Depends(get_attendance_session_service),
) -> dict[str, int]:
    """
    Penjadwal: hapus berkas gambar wajah (probe) yang telah melewati masa retensi (P8-6).
    """
    purged = await attendance_session_service.purge_faces()
    return {"purged": purged}
