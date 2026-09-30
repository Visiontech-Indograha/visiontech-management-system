"""Skema permintaan & respons: monitoring (dipindah dari api/v1/endpoints/monitoring.py, R-28 M2b)."""
from datetime import date
from uuid import UUID

from pydantic import BaseModel


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
