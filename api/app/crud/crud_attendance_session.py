"""
app/crud/crud_attendance_session.py
Shim re-export untuk kompatibilitas uji lama.
"""
from app.modules.attendance.repositories.attendance_session_repository import (
    AttendanceSessionRepository,
    CRUDAttendanceSession,
)

__all__ = ["AttendanceSessionRepository", "CRUDAttendanceSession"]
