"""Laporan mingguan SK (V-25, dok 05 §3.6) — `domain.js` SAVE_WEEKLY, SUBMIT_WEEKLY, REVIEW_WEEKLY."""
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import PlanAccess, PlanNeed, get_db_with_user, plan_access
from app.services.weekly_report_service import WeeklyReportService

router = APIRouter(prefix="/work-plans/{plan_id}/weekly", tags=["Weekly Reports"])
_VIEW_ACCESS = Depends(plan_access(PlanNeed.VIEW))
_LEADER_ACCESS = Depends(plan_access(PlanNeed.LEADER))      # domain.js SAVE/SUBMIT_WEEKLY
_PM_UNIT_ACCESS = Depends(plan_access(PlanNeed.PM_UNIT))    # domain.js REVIEW_WEEKLY


class WeeklyReportRequest(BaseModel):
    body: str
    obstacle: str


class WeeklyReviewRequest(BaseModel):
    decision: str
    note: str | None = None


class WeeklyReportResponse(BaseModel):
    week: int
    name: str
    starts_on: date
    ends_on: date
    status: str
    body: str
    obstacle: str
    review_note: str | None
    days_approved: bool


def _out(row: Any) -> WeeklyReportResponse:
    return WeeklyReportResponse(**row._mapping)


@router.get("", response_model=list[WeeklyReportResponse])
async def list_weeks(access: PlanAccess = _VIEW_ACCESS, db: AsyncSession = Depends(get_db_with_user)) -> list[WeeklyReportResponse]:
    return [_out(row) for row in await WeeklyReportService(db).list_weeks(access)]


@router.put("/{week}", response_model=WeeklyReportResponse)
async def save_weekly(week: int, data: WeeklyReportRequest, access: PlanAccess = _LEADER_ACCESS,
                      db: AsyncSession = Depends(get_db_with_user)) -> WeeklyReportResponse:
    return _out(await WeeklyReportService(db).save_weekly(access, week, data.body, data.obstacle))


@router.post("/{week}/submit", response_model=WeeklyReportResponse)
async def submit_weekly(week: int, access: PlanAccess = _LEADER_ACCESS,
                        db: AsyncSession = Depends(get_db_with_user)) -> WeeklyReportResponse:
    return _out(await WeeklyReportService(db).submit_weekly(access, week))


@router.post("/{week}/review", response_model=WeeklyReportResponse)
async def review_weekly(week: int, data: WeeklyReviewRequest, access: PlanAccess = _PM_UNIT_ACCESS,
                        db: AsyncSession = Depends(get_db_with_user)) -> WeeklyReportResponse:
    return _out(await WeeklyReportService(db).review_weekly(access, week, data.decision, data.note))
