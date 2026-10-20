"""
app/modules/reports/routes/weekly_report_route.py

Rute endpoint HTTP untuk laporan mingguan SK (/work-plans/{plan_id}/weekly).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from fastapi import APIRouter, Depends

from app.api.deps import plan_access
from app.modules.reports.controllers.weekly_report_controller import (
    WeeklyReportController,
)
from app.modules.reports.schemas.weekly_report_schema import (
    WeeklyReportRequest,
    WeeklyReportResponse,
    WeeklyReviewRequest,
)
from app.shared.access.access_service import PlanAccess, PlanNeed

router = APIRouter(prefix="/work-plans/{plan_id}/weekly", tags=["Weekly Reports"])
_VIEW_ACCESS = Depends(plan_access(PlanNeed.VIEW))
_LEADER_ACCESS = Depends(plan_access(PlanNeed.LEADER))
_PM_UNIT_ACCESS = Depends(plan_access(PlanNeed.PM_UNIT))


@router.get("", response_model=list[WeeklyReportResponse])
async def list_weeks(
    access: PlanAccess = _VIEW_ACCESS,
    controller: WeeklyReportController = Depends(),
) -> list[WeeklyReportResponse]:
    """Mengambil daftar laporan mingguan untuk sebuah SK."""
    return await controller.handle_list_weeks(access)


@router.put("/{week}", response_model=WeeklyReportResponse)
async def save_weekly(
    week: int,
    data: WeeklyReportRequest,
    access: PlanAccess = _LEADER_ACCESS,
    controller: WeeklyReportController = Depends(),
) -> WeeklyReportResponse:
    """Menyimpan draf laporan mingguan."""
    return await controller.handle_save_weekly(access, week, data)


@router.post("/{week}/submit", response_model=WeeklyReportResponse)
async def submit_weekly(
    week: int,
    access: PlanAccess = _LEADER_ACCESS,
    controller: WeeklyReportController = Depends(),
) -> WeeklyReportResponse:
    """Mengajukan laporan mingguan agar bisa ditinjau."""
    return await controller.handle_submit_weekly(access, week)


@router.post("/{week}/review", response_model=WeeklyReportResponse)
async def review_weekly(
    week: int,
    data: WeeklyReviewRequest,
    access: PlanAccess = _PM_UNIT_ACCESS,
    controller: WeeklyReportController = Depends(),
) -> WeeklyReportResponse:
    """Meninjau laporan mingguan (PM Unit) untuk disetujui atau ditolak."""
    return await controller.handle_review_weekly(access, week, data)
