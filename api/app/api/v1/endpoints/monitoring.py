"""Pemantauan OPS (V-30, dok 05 §3.13): lini masa per pekerjaan & rekap absensi."""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_db_with_user, require_permission
from app.core.permissions import Permission
from app.schemas.monitoring import (
    AttendanceRecap,
    TimelineGroup,
)
from app.services.monitoring_service import MonitoringService

router = APIRouter(tags=["Monitoring"])












@router.get("/timeline", response_model=list[TimelineGroup])
async def timeline(
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    current_user: CurrentUser = Depends(require_permission(Permission.VIEW_TIMELINE)),
    db: AsyncSession = Depends(get_db_with_user),
) -> list[TimelineGroup]:
    """Dok 03 M11: dikelompokkan per pekerjaan, hanya SK yang terlihat (V-07)."""
    groups = await MonitoringService(db).timeline(current_user, date_from, date_to)
    return [TimelineGroup(**group) for group in groups]


@router.get("/recaps/attendance", response_model=AttendanceRecap)
async def attendance_recap(
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user),
) -> AttendanceRecap:
    """FINANCE/HR/OPS/ADMIN: seluruh organisasi; lainnya: hanya dirinya (aturan `GET /attendance`)."""
    return AttendanceRecap(**await MonitoringService(db).attendance_recap(current_user, month))
