"""
app/modules/attendance/repositories/attendance_repository.py

Repositori data absensi sesi kerja, event luring, dan pemantauan.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.5.
"""
from app.crud.crud_attendance_monitor import CRUDAttendanceMonitor
from app.crud.crud_attendance_offline import CRUDAttendanceOffline
from app.crud.crud_attendance_session import CRUDAttendanceSession


class AttendanceSessionRepository(CRUDAttendanceSession):
    """Repositori sesi absensi lapangan dan kantor."""


class AttendanceOfflineRepository(CRUDAttendanceOffline):
    """Repositori antrean event absensi luring."""


class AttendanceMonitorRepository(CRUDAttendanceMonitor):
    """Repositori pemantauan dan audit anomali absensi."""


__all__ = [
    "AttendanceMonitorRepository",
    "AttendanceOfflineRepository",
    "AttendanceSessionRepository",
]

