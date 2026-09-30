"""
Tugas terjadwal pemantauan absensi (P4-9, dok 17 §5.3). Dipanggil penjadwal dengan token ADMIN.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db_with_user, require_permission
from app.core.permissions import Permission
from app.crud.crud_attendance_monitor import CRUDAttendanceMonitor
from app.schemas.attendance import MissingCheckInResponse, NeedsReviewResponse
from app.services.attendance_monitor_service import AttendanceMonitorService

router = APIRouter(prefix="/cron/attendance", tags=["Attendance Cron"])






@router.post("/alert-missing", response_model=MissingCheckInResponse)
async def alert_missing_checkin(
    current_user: CurrentUser = Depends(require_permission(Permission.RUN_SYSTEM_JOBS)),
    db: AsyncSession = Depends(get_db_with_user),
) -> MissingCheckInResponse:
    result = await AttendanceMonitorService(CRUDAttendanceMonitor(db)).check_missing_check_ins(
        current_user.organization_id
    )
    return MissingCheckInResponse(alerted=result.alerted, check_ins_today=result.check_ins_today)


@router.post("/alert-needs-review", response_model=NeedsReviewResponse)
async def alert_needs_review_spike(
    current_user: CurrentUser = Depends(require_permission(Permission.RUN_SYSTEM_JOBS)),
    db: AsyncSession = Depends(get_db_with_user),
) -> NeedsReviewResponse:
    result = await AttendanceMonitorService(CRUDAttendanceMonitor(db)).check_needs_review_spike(
        current_user.organization_id
    )
    return NeedsReviewResponse(
        alerted=result.alerted,
        needs_review_today=result.needs_review_today,
        daily_average=result.daily_average,
    )
