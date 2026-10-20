"""
app/modules/work_plans/schemas/daily_plan_schema.py
Skema jadwal harian daily-first (Milestone 5, docs/35 §3). Minggu = rentang tanggal `work_date`.

Status: DRAFT → SUBMITTED → APPROVED → ONGOING → COMPLETED; ditolak PM → DRAFT + `rejection_reason`.
"""
from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

DailyStatus = Literal["DRAFT", "SUBMITTED", "APPROVED", "ONGOING", "COMPLETED"]


def _check_hours(clock_in: time | None, clock_out: time | None) -> None:
    if clock_in and clock_out and clock_out <= clock_in:
        raise ValueError("Jam pulang harus setelah jam masuk.")


class DailyPlanCreate(BaseModel):
    division_id: UUID
    team_id: UUID
    work_date: date
    site_name: str = Field(min_length=2, max_length=150)
    site_lat: Decimal = Field(ge=-90, le=90)
    site_lng: Decimal = Field(ge=-180, le=180)
    attendance_radius_m: int = Field(150, ge=10, le=5000)
    clock_in_time: time = time(7, 0)
    clock_out_time: time = time(16, 0)

    @model_validator(mode="after")
    def _hours(self) -> DailyPlanCreate:
        _check_hours(self.clock_in_time, self.clock_out_time)
        return self


class DailyPlanUpdate(BaseModel):
    team_id: UUID | None = None
    work_date: date | None = None
    site_name: str | None = Field(default=None, min_length=2, max_length=150)
    site_lat: Decimal | None = Field(default=None, ge=-90, le=90)
    site_lng: Decimal | None = Field(default=None, ge=-180, le=180)
    attendance_radius_m: int | None = Field(default=None, ge=10, le=5000)
    clock_in_time: time | None = None
    clock_out_time: time | None = None

    @model_validator(mode="after")
    def _hours(self) -> DailyPlanUpdate:
        _check_hours(self.clock_in_time, self.clock_out_time)
        return self


class DailyPlanCopy(BaseModel):
    """Salin jadwal (lokasi, jam, tim) ke tanggal lain — mis. menyusun satu minggu."""

    work_dates: list[date] = Field(min_length=1, max_length=31)


class RejectIn(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


class BulkApproveIn(BaseModel):
    daily_plan_ids: list[UUID] = Field(min_length=1, max_length=200)


class BulkApproveOut(BaseModel):
    approved: list[UUID]
    skipped: list[UUID]


class AttachmentsIn(BaseModel):
    file_ids: list[UUID] = Field(max_length=20)


class DailyItemBrief(BaseModel):
    """Ringkasan item di detail jadwal (pengelolaan item: Milestone 6)."""

    item_id: UUID
    title: str
    task_phase: str
    work_type_id: UUID
    work_type_name: str | None = None
    completion_id: UUID | None = None
    location_name: str | None = None
    target_qty: Decimal
    completed_qty: Decimal
    status: str
    rollover_approval_status: str


class DailyPlanOut(BaseModel):
    daily_plan_id: UUID
    division_id: UUID
    division_name: str
    team_id: UUID
    team_name: str
    leader_employee_id: UUID
    leader_name: str
    work_date: date
    site_name: str
    site_lat: Decimal
    site_lng: Decimal
    attendance_radius_m: int
    clock_in_time: time
    clock_out_time: time
    status: DailyStatus
    created_by_id: UUID
    approved_by_pm_id: UUID | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None
    item_count: int = 0
    done_count: int = 0


class DailyPlanDetail(DailyPlanOut):
    items: list[DailyItemBrief] = []
    attachment_file_ids: list[UUID] = []


class TeamOption(BaseModel):
    team_id: UUID
    name: str
    division_id: UUID
    leader_employee_id: UUID
    leader_name: str


class DivisionOption(BaseModel):
    division_id: UUID
    name: str


class OrderOption(BaseModel):
    completion_id: UUID
    client_name: str
    project_title: str
    order_number: str | None = None
    division_id: UUID | None = None


class DailyFormOptions(BaseModel):
    divisions: list[DivisionOption]
    teams: list[TeamOption]
    orders: list[OrderOption]


class GeoResult(BaseModel):
    name: str
    lat: float
    lng: float
    type: str = ""
