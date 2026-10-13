"""
app/modules/system/routes/monitoring_route.py

Rute endpoint HTTP untuk pemantauan lini masa dan rekap kehadiran (/timeline, /recaps/attendance).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""
from datetime import date

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user, require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.system.controllers.monitoring_controller import (
    MonitoringController,
)
from app.modules.system.schemas.system_schema import (
    AttendanceRecap,
    TimelineGroup,
)

router = APIRouter(tags=["Monitoring"])


@router.get("/timeline", response_model=list[TimelineGroup])
async def timeline(
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    current_user: CurrentUser = Depends(require_permission(Permission.VIEW_TIMELINE)),
    controller: MonitoringController = Depends(),
) -> list[TimelineGroup]:
    """Dok 03 M11: dikelompokkan per pekerjaan, hanya SK yang terlihat (V-07)."""
    return await controller.handle_timeline(current_user, date_from, date_to)


@router.get("/recaps/attendance", response_model=AttendanceRecap)
async def attendance_recap(
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    current_user: CurrentUser = Depends(get_current_user),
    controller: MonitoringController = Depends(),
) -> AttendanceRecap:
    """FINANCE/HR/OPS/ADMIN: seluruh organisasi; lainnya: hanya dirinya (aturan `GET /attendance`)."""
    return await controller.handle_attendance_recap(current_user, month)


__all__ = ["router"]

