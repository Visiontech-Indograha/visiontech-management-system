"""
app/modules/home/dependencies.py

Perakitan HomeService dari service modul lain (titik perakitan antarmodul).
"""

from fastapi import Depends

from app.modules.assets.dependencies import get_asset_service
from app.modules.assets.services.asset_service import AssetService
from app.modules.attendance.dependencies import get_attendance_session_service
from app.modules.attendance.services.attendance_session_service import AttendanceSessionService
from app.modules.home.services.home_service import HomeService
from app.modules.leaves.dependencies import get_leave_service
from app.modules.leaves.services.leave_service import LeaveService
from app.modules.mess.dependencies import get_mess_service
from app.modules.mess.services.mess_service import MessService
from app.modules.notifications.dependencies import get_notification_service
from app.modules.notifications.services.notification_service import NotificationService
from app.modules.offboarding.dependencies import get_offboarding_service
from app.modules.offboarding.services.offboarding_service import OffboardingService
from app.modules.overtime.dependencies import get_overtime_service
from app.modules.overtime.services.overtime_service import OvertimeService
from app.modules.work_plans.dependencies import get_daily_correction_service
from app.modules.work_plans.services.daily_correction_service import DailyCorrectionService


def get_home_service(
    leaves: LeaveService = Depends(get_leave_service),
    attendance: AttendanceSessionService = Depends(get_attendance_session_service),
    overtime: OvertimeService = Depends(get_overtime_service),
    mess: MessService = Depends(get_mess_service),
    assets: AssetService = Depends(get_asset_service),
    corrections: DailyCorrectionService = Depends(get_daily_correction_service),
    offboarding: OffboardingService = Depends(get_offboarding_service),
    notifications: NotificationService = Depends(get_notification_service),
) -> HomeService:
    return HomeService(leaves, attendance, overtime, mess, assets, corrections, offboarding, notifications)
