"""
app/modules/hse/routes/daily_report_route.py

Rute endpoint HTTP untuk laporan harian pekerjaan (/work-plans/{plan_id}/days).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import plan_day_access
from app.modules.hse.controllers.hse_controller import HseController
from app.modules.hse.schemas.hse_schema import (
    DailyReportCreate,
    DailyReportResponse,
    ReportReviewRequest,
)
from app.shared.access.access_service import PlanAccess, PlanNeed

days_router = APIRouter(prefix="/work-plans/{plan_id}/days", tags=["Daily Reports"])
_DAY_LEADER_ACCESS = Depends(plan_day_access(PlanNeed.LEADER))
_DAY_PM_UNIT_ACCESS = Depends(plan_day_access(PlanNeed.PM_UNIT))


@days_router.put("/{day_id}", response_model=DailyReportResponse)
async def upsert_daily_report(
    day_id: UUID,
    data: DailyReportCreate,
    access: PlanAccess = _DAY_LEADER_ACCESS,
    controller: HseController = Depends(),
) -> DailyReportResponse:
    """Membuat atau memperbarui DRAFT laporan harian pekerjaan."""
    return await controller.handle_upsert_daily_report(access, day_id, data)


@days_router.post("/{day_id}/submit", response_model=DailyReportResponse)
async def submit_daily_report(
    day_id: UUID,
    access: PlanAccess = _DAY_LEADER_ACCESS,
    controller: HseController = Depends(),
) -> DailyReportResponse:
    """Menyerahkan (submit) laporan harian untuk ditinjau."""
    return await controller.handle_submit_daily_report(access, day_id)


@days_router.post("/{day_id}/review", response_model=DailyReportResponse)
async def review_daily_report(
    day_id: UUID,
    data: ReportReviewRequest,
    access: PlanAccess = _DAY_PM_UNIT_ACCESS,
    controller: HseController = Depends(),
) -> DailyReportResponse:
    """PM unit/OPS menyetujui atau mengembalikan laporan harian."""
    return await controller.handle_review_daily_report(access, day_id, data)


@days_router.post("/{day_id}/tasks/{task_id}/toggle")
async def toggle_task(
    day_id: UUID,
    task_id: UUID,
    access: PlanAccess = _DAY_LEADER_ACCESS,
    controller: HseController = Depends(),
) -> dict[str, object]:
    """Ketua mencentang atau menghapus centang tugas hari tersebut."""
    return await controller.handle_toggle_task(access, day_id, task_id)
