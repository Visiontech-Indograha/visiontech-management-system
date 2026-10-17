"""
app/modules/attendance/controllers/attendance_cron_controller.py

Controller orkestrasi use case tugas terjadwal pemantauan absensi (cron).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""

from __future__ import annotations

from fastapi import Depends

from app.api.deps import (
    get_attendance_monitor_service,
    get_attendance_session_service,
)
from app.core.security import CurrentUser
from app.modules.attendance.schemas.attendance_schema import (
    MissingCheckInResponse,
    NeedsReviewResponse,
)
from app.modules.attendance.services.attendance_service import (
    AttendanceMonitorService,
    AttendanceSessionService,
)


class AttendanceCronController:
    """
    Controller tugas berkala absensi (deteksi keterlambatan, lonjakan review,
    pencocokan ulang wajah, pembersihan probe).
    """

    def __init__(
        self,
        attendance_monitor_service: AttendanceMonitorService = Depends(get_attendance_monitor_service),
        attendance_session_service: AttendanceSessionService = Depends(get_attendance_session_service),
    ) -> None:
        self.monitor_service = attendance_monitor_service
        self.session_service = attendance_session_service

    async def handle_alert_missing_checkin(
        self,
        current_user: CurrentUser,
    ) -> MissingCheckInResponse:
        """Memeriksa absensi check-in yang belum dilakukan pada hari berjalan dan mengirim peringatan."""
        result = await self.monitor_service.check_missing_check_ins(current_user.organization_id)
        return MissingCheckInResponse(alerted=result.alerted, check_ins_today=result.check_ins_today)

    async def handle_alert_needs_review(
        self,
        current_user: CurrentUser,
    ) -> NeedsReviewResponse:
        """Mendeteksi lonjakan absensi yang memerlukan peninjauan dan mengirim peringatan."""
        result = await self.monitor_service.check_needs_review_spike(current_user.organization_id)
        return NeedsReviewResponse(
            alerted=result.alerted,
            needs_review_today=result.needs_review_today,
            daily_average=result.daily_average,
        )

    async def handle_reverify_faces(
        self,
        limit: int = 50,
    ) -> dict[str, int]:
        """Mencocokkan ulang probe wajah yang tertunda saat face service sempat tidak aktif."""
        done, left = await self.session_service.reverify_faces(limit=limit)
        return {"done": done, "remaining": left}

    async def handle_purge_face_probes(
        self,
    ) -> dict[str, int]:
        """Menghapus berkas gambar wajah (probe) yang melewati masa retensi privasi."""
        purged = await self.session_service.purge_faces()
        return {"purged": purged}

    async def handle_auto_checkout(
        self,
        current_user: CurrentUser,
    ) -> dict[str, int]:
        """Menutup otomatis sesi absensi yang belum ditutup pada pukul 19:00."""
        closed = await self.monitor_service.auto_checkout_unclosed_sessions(current_user.organization_id)
        return {"closed_count": closed}


__all__ = ["AttendanceCronController"]
