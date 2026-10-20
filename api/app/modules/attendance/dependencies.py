"""
app/modules/attendance/dependencies.py

Perakitan service modul attendance untuk FastAPI `Depends` (dipindah dari api/deps.py).
Getter memakai dependency sesi yang SAMA dengan handler sehingga satu permintaan = satu transaksi.
Verifikasi wajah dipakai lewat API publik modul face (`get_face_service`).
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.attendance.repositories.attendance_monitor_repository import CRUDAttendanceMonitor
from app.modules.attendance.repositories.attendance_offline_repository import CRUDAttendanceOffline
from app.modules.attendance.repositories.attendance_session_repository import CRUDAttendanceSession
from app.modules.attendance.services.attendance_monitor_service import AttendanceMonitorService
from app.modules.attendance.services.attendance_offline_service import AttendanceOfflineService
from app.modules.attendance.services.attendance_session_service import AttendanceSessionService
from app.modules.face.dependencies import get_face_service
from app.modules.face.services.face_service import FaceService
from app.shared.org_clock import CRUDOrgClock


def get_attendance_monitor_service(db: AsyncSession = Depends(get_db_with_user)) -> AttendanceMonitorService:
    return AttendanceMonitorService(CRUDAttendanceMonitor(db))


def get_attendance_session_service(
    db: AsyncSession = Depends(get_db_with_user),
    faces: FaceService = Depends(get_face_service),
) -> AttendanceSessionService:
    return AttendanceSessionService(CRUDAttendanceSession(db), CRUDOrgClock(db), faces)


def get_attendance_offline_service(
    db: AsyncSession = Depends(get_db_with_user),
    sessions: AttendanceSessionService = Depends(get_attendance_session_service),
) -> AttendanceOfflineService:
    return AttendanceOfflineService(CRUDAttendanceOffline(db), sessions)
