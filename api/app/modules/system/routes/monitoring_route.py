"""
app/modules/system/routes/monitoring_route.py

Rute endpoint HTTP untuk rekap kehadiran (/recaps/attendance).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.core.security import CurrentUser
from app.modules.system.controllers.monitoring_controller import (
    MonitoringController,
)
from app.modules.system.schemas.system_schema import (
    AttendanceRecap,
)

router = APIRouter(tags=["Monitoring"])


@router.get("/recaps/attendance", response_model=AttendanceRecap)
async def attendance_recap(
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    current_user: CurrentUser = Depends(get_current_user),
    controller: MonitoringController = Depends(),
) -> AttendanceRecap:
    """FINANCE/HR/OPS/ADMIN: seluruh organisasi; lainnya: hanya dirinya (aturan `GET /attendance`)."""
    return await controller.handle_attendance_recap(current_user, month)


__all__ = ["router"]
