"""Skema permintaan & respons: weekly report (dipindah dari api/v1/endpoints/weekly_reports.py, R-28 M2b)."""
from datetime import date

from pydantic import BaseModel


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
    resubmitted: bool = False   # "Dikirim ulang" (alur SK v2)
