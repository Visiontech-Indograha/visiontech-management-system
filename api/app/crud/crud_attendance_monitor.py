"""
app/crud/crud_attendance_monitor.py
Shim re-export untuk kompatibilitas uji lama.
"""
from app.modules.attendance.repositories.attendance_monitor_repository import (
    AttendanceMonitorRepository,
    CRUDAttendanceMonitor,
)

__all__ = ["AttendanceMonitorRepository", "CRUDAttendanceMonitor"]
