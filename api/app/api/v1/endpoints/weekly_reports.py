"""Laporan mingguan SK (V-25, dok 05 §3.6) — `domain.js` SAVE_WEEKLY, SUBMIT_WEEKLY, REVIEW_WEEKLY."""
from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_weekly_report_service, plan_access
from app.schemas.weekly_report import WeeklyReportRequest, WeeklyReportResponse, WeeklyReviewRequest
from app.services.access_service import PlanAccess, PlanNeed
from app.services.weekly_report_service import WeeklyReportService

router = APIRouter(prefix="/work-plans/{plan_id}/weekly", tags=["Weekly Reports"])
_VIEW_ACCESS = Depends(plan_access(PlanNeed.VIEW))
_LEADER_ACCESS = Depends(plan_access(PlanNeed.LEADER))      # domain.js SAVE/SUBMIT_WEEKLY
_PM_UNIT_ACCESS = Depends(plan_access(PlanNeed.PM_UNIT))    # domain.js REVIEW_WEEKLY








def _out(row: Any) -> WeeklyReportResponse:
    return WeeklyReportResponse(**row._mapping)


@router.get("", response_model=list[WeeklyReportResponse])
async def list_weeks(access: PlanAccess = _VIEW_ACCESS, weekly_report_service: WeeklyReportService = Depends(get_weekly_report_service)) -> list[WeeklyReportResponse]:
    return [_out(row) for row in await weekly_report_service.list_weeks(access)]


@router.put("/{week}", response_model=WeeklyReportResponse)
async def save_weekly(week: int, data: WeeklyReportRequest, access: PlanAccess = _LEADER_ACCESS,
                      weekly_report_service: WeeklyReportService = Depends(get_weekly_report_service)) -> WeeklyReportResponse:
    return _out(await weekly_report_service.save_weekly(access, week, data.body, data.obstacle))


@router.post("/{week}/submit", response_model=WeeklyReportResponse)
async def submit_weekly(week: int, access: PlanAccess = _LEADER_ACCESS,
                        weekly_report_service: WeeklyReportService = Depends(get_weekly_report_service)) -> WeeklyReportResponse:
    return _out(await weekly_report_service.submit_weekly(access, week))


@router.post("/{week}/review", response_model=WeeklyReportResponse)
async def review_weekly(week: int, data: WeeklyReviewRequest, access: PlanAccess = _PM_UNIT_ACCESS,
                        weekly_report_service: WeeklyReportService = Depends(get_weekly_report_service)) -> WeeklyReportResponse:
    return _out(await weekly_report_service.review_weekly(access, week, data.decision, data.note))
