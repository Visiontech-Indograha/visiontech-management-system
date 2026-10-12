"""
app/modules/attendance/services/attendance_service.py

Layanan logika bisnis untuk modul absensi (sesi, luring, pemantauan).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.3.
"""
from app.services.attendance_monitor_service import (
    AttendanceMonitorService as BaseAttendanceMonitorService,
)
from app.services.attendance_offline_service import (
    AttendanceOfflineService as BaseAttendanceOfflineService,
)
from app.services.attendance_session_service import (
    AttendanceSessionService as BaseAttendanceSessionService,
)


class AttendanceSessionService(BaseAttendanceSessionService):
    """Layanan bisnis transaksi absensi sesi (check-in/out, review, export)."""


class AttendanceOfflineService(BaseAttendanceOfflineService):
    """Layanan bisnis sinkronisasi absensi luring."""


class AttendanceMonitorService(BaseAttendanceMonitorService):
    """Layanan bisnis audit dan deteksi anomali absensi."""


__all__ = [
    "AttendanceMonitorService",
    "AttendanceOfflineService",
    "AttendanceSessionService",
]

