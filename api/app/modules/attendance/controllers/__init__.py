"""
Paket controller untuk modul attendance.
"""

from app.modules.attendance.controllers.attendance_controller import AttendanceController
from app.modules.attendance.controllers.attendance_cron_controller import (
    AttendanceCronController,
)

__all__ = ["AttendanceController", "AttendanceCronController"]
