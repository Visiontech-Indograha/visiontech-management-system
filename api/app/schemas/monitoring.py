"""
app/schemas/monitoring.py

Request and response schemas for monitoring timelines and attendance recaps.
"""
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class TimelineLeader(BaseModel):
    """
    Schema for the leader information within a timeline.
    """
    employee_id: str
    full_name: str | None


class TimelineDay(BaseModel):
    """
    Schema for a specific day in a timeline.
    """
    id: str
    work_date: date
    title: str
    # Status dari hari tersebut: APPROVED | SUBMITTED | CHANGES_REQUESTED | LATE | TODAY | UPCOMING
    state: str


class TimelineGroup(BaseModel):
    """
    Schema for a grouped timeline representation (e.g., project timeline).
    """
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
    """
    Schema for a single employee's attendance summary in a recap report.
    """
    employee_id: str
    full_name: str
    days_present: int
    auto_valid: int
    needs_review: int
    approved: int
    rejected: int


class AttendanceRecapRecord(BaseModel):
    """
    Schema for a single attendance record within a recap history (R-33).
    Satu absensi dalam riwayat rekap — mencakup informasi jam masuk & keluar.
    """
    id: str
    employee_id: str
    full_name: str
    work_date: date
    site_label: str
    check_in_at: datetime
    check_out_at: datetime | None
    status: str
    is_late: bool
    is_early_leave: bool


class AttendanceRecap(BaseModel):
    """
    Schema for the overall monthly attendance recap report.
    """
    month: str
    employees: list[AttendanceRecapRow]
    records: list[AttendanceRecapRecord] = []
