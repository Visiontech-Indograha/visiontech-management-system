"""
app/modules/attendance/routes/attendance_cron_route.py

Rute endpoint HTTP untuk cron absensi (/cron/attendance).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from fastapi import APIRouter, Depends

from app.api.deps import require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.attendance.controllers.attendance_cron_controller import (
    AttendanceCronController,
)
from app.modules.attendance.schemas.attendance_schema import (
    MissingCheckInResponse,
    NeedsReviewResponse,
)

router = APIRouter(prefix="/cron/attendance", tags=["Attendance Cron"])


@router.post("/alert-missing", response_model=MissingCheckInResponse)
async def alert_missing_checkin(
    current_user: CurrentUser = Depends(require_permission(Permission.RUN_SYSTEM_JOBS)),
    controller: AttendanceCronController = Depends(),
) -> MissingCheckInResponse:
    """
    Pemicu cron untuk memeriksa absensi check-in yang belum dilakukan pada hari berjalan,
    kemudian mengirim peringatan jika ditemukan.
    """
    return await controller.handle_alert_missing_checkin(current_user)


@router.post("/alert-needs-review", response_model=NeedsReviewResponse)
async def alert_needs_review_spike(
    current_user: CurrentUser = Depends(require_permission(Permission.RUN_SYSTEM_JOBS)),
    controller: AttendanceCronController = Depends(),
) -> NeedsReviewResponse:
    """
    Pemicu cron untuk mendeteksi lonjakan absensi yang memerlukan review (P4-9, dok 17 §5.3)
    dan memperingatkan manajer terkait.
    """
    return await controller.handle_alert_needs_review(current_user)


@router.post("/auto-checkout")
async def auto_checkout_daily(
    current_user: CurrentUser = Depends(require_permission(Permission.RUN_SYSTEM_JOBS)),
    controller: AttendanceCronController = Depends(),
) -> dict[str, int]:
    """
    Penjadwal / Cron: Menutup otomatis sesi absensi yang belum ditutup pada pukul 19:00.
    """
    return await controller.handle_auto_checkout(current_user)


__all__ = ["router"]
