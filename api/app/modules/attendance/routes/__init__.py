"""
Paket routing untuk modul attendance.
"""

from app.modules.attendance.routes.attendance_cron_route import router as attendance_cron_router
from app.modules.attendance.routes.attendance_route import router as attendance_router

__all__ = ["attendance_cron_router", "attendance_router"]
