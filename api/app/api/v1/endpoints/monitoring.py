"""Pemantauan OPS (V-30, dok 05 §3.13): lini masa per pekerjaan & rekap absensi."""
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_db_with_user, require_permission
from app.core.permissions import Permission
from app.services.monitoring_service import MonitoringService

router = APIRouter(tags=["Monitoring"])


class TimelineLeader(BaseModel):
    employee_id: str
    full_name: str | None


class TimelineDay(BaseModel):
    id: str
    work_date: date
    title: str
    state: str          # APPROVED | SUBMITTED | CHANGES_REQUESTED | LATE | TODAY | UPCOMING


class TimelineGroup(BaseModel):
    id: str
    number: str | None
    title: str
    status: str
    unit_id: UUID | None
    location_text: str | None
    period_start: date
    period_end: date
    leader: TimelineLeader | None
    total_days: int
    approved_days: int
    late_days: int
    days: list[TimelineDay]


class AttendanceRecapRow(BaseModel):
    employee_id: str
    full_name: str
    days_present: int
    auto_valid: int
    needs_review: int
    approved: int
    rejected: int


class AttendanceRecap(BaseModel):
    month: str
    employees: list[AttendanceRecapRow]


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
