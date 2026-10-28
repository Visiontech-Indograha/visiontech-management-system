"""
app/modules/leaves/schemas/leave_schema.py

Schema Pydantic untuk pengajuan dan persetujuan cuti / sakit (leave_request & leave_balance).
"""
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

LeaveType = Literal["ANNUAL", "SICK", "MATERNITY", "UNPAID", "OTHER"]
LeaveStatus = Literal[
    "PENDING",
    "APPROVED_BY_PM",
    "APPROVED_BY_HR",
    "APPROVED_BY_FINANCE",
    "REJECTED",
    "CANCELLED",
]


class LeaveCreate(BaseModel):
    employee_id: UUID | None = None  # None = karyawan yang sedang login
    leave_type: LeaveType
    start_date: date
    end_date: date
    reason: str = Field(min_length=3, max_length=1000)
    attachment_file_id: UUID | None = None  # Surat dokter / dokumen pendukung

    @model_validator(mode="after")
    def _dates(self) -> "LeaveCreate":
        if self.end_date < self.start_date:
            raise ValueError("Tanggal selesai tidak boleh sebelum tanggal mulai.")
        return self


class LeaveReview(BaseModel):
    decision: Literal["APPROVED", "REJECTED"]
    note: str | None = Field(default=None, max_length=1000)


class LeaveResponse(BaseModel):
    leave_id: UUID
    employee_id: UUID
    employee_name: str
    employee_no: str | None = None
    division_name: str | None = None
    leave_type: LeaveType
    start_date: date
    end_date: date
    total_days: int
    reason: str
    status: LeaveStatus
    attachment_path: str | None = None
    reviewed_by_name: str | None = None
    reviewed_at: datetime | None = None
    rejection_note: str | None = None
    create_at: datetime


class LeaveBalanceResponse(BaseModel):
    balance_id: UUID
    employee_id: UUID
    employee_name: str
    period_year: int
    total_quota: int
    used_quota: int
    remaining_quota: int


class LeaveTypeOption(BaseModel):
    code: LeaveType
    label: str
    uses_quota: bool
