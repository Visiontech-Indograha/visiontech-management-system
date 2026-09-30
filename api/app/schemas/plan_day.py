"""Skema permintaan & respons: plan day (dipindah dari api/v1/endpoints/work_plan_days.py, R-28 M2b)."""
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class DayTaskOut(BaseModel):
    id: UUID
    title: str
    sort_order: int
    is_done: bool
    done_at: datetime | None


class DayReportOut(BaseModel):
    status: str
    body: str
    obstacle: str
    review_note: str | None
    submitted_at: datetime | None
    reviewed_at: datetime | None
    evidence_file_ids: list[UUID]


class PlanDayOut(BaseModel):
    id: UUID
    work_date: date
    title: str
    sort_order: int
    tasks: list[DayTaskOut]
    report: DayReportOut | None
