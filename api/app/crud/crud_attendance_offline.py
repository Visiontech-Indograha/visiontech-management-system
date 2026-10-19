"""
app/crud/crud_attendance_offline.py
Shim re-export untuk kompatibilitas uji lama.
"""
from app.modules.attendance.repositories.attendance_offline_repository import (
    AttendanceOfflineRepository,
    CRUDAttendanceOffline,
)

__all__ = ["AttendanceOfflineRepository", "CRUDAttendanceOffline"]
