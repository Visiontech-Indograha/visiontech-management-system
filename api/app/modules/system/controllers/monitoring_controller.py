"""
app/modules/system/controllers/monitoring_controller.py

Controller orkestrasi use case pemantauan lini masa pekerjaan dan rekap absensi.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""

from __future__ import annotations

from fastapi import Depends

from app.core.security import CurrentUser
from app.modules.system.dependencies import get_monitoring_service
from app.modules.system.schemas.system_schema import (
    AttendanceRecap,
)
from app.modules.system.services.system_service import MonitoringService


class MonitoringController:
    """Controller pemantauan lini masa pekerjaan lapangan dan rekap bulanan absensi."""

    def __init__(
        self,
        monitoring_service: MonitoringService = Depends(get_monitoring_service),
    ) -> None:
        self.service = monitoring_service

    async def handle_attendance_recap(
        self,
        current_user: CurrentUser,
        month: str | None = None,
    ) -> AttendanceRecap:
        """Mengambil ringkasan rekapitulasi kehadiran bulanan."""
        return AttendanceRecap(**await self.service.attendance_recap(current_user, month))


__all__ = ["MonitoringController"]
