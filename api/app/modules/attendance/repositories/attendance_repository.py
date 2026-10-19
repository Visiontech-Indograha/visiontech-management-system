"""
app/modules/attendance/repositories/attendance_repository.py
"""
from .attendance_monitor_repository import AttendanceMonitorRepository, CRUDAttendanceMonitor
from .attendance_offline_repository import AttendanceOfflineRepository, CRUDAttendanceOffline
from .attendance_session_repository import AttendanceSessionRepository, CRUDAttendanceSession

__all__ = [
    "AttendanceMonitorRepository",
    "AttendanceOfflineRepository",
    "AttendanceSessionRepository",
    "CRUDAttendanceMonitor",
    "CRUDAttendanceOffline",
    "CRUDAttendanceSession",
]
