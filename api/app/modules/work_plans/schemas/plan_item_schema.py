"""
app/modules/work_plans/schemas/plan_item_schema.py
Item pekerjaan per titik (Milestone 6, docs/35 §3–4): satu titik = satu item pada jadwal harian.

Fase: SURVEY → PREPARATION → INSTALLATION / REPLACEMENT / MAINTENANCE (hanya tiga terakhir boleh deliverable utama).
Status: TODO → IN_PROGRESS → DONE; belum selesai → PENDING_ROLLOVER (menunggu PM) → SHIFTED_DAY (digeser).
"""
from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

TaskPhase = Literal["SURVEY", "PREPARATION", "INSTALLATION", "REPLACEMENT", "MAINTENANCE"]
ItemStatus = Literal["TODO", "IN_PROGRESS", "DONE", "PENDING_ROLLOVER", "SHIFTED_DAY", "CANCELLED"]
RolloverStatus = Literal["NONE", "WAITING_PM", "APPROVED_BY_PM", "REJECTED_BY_PM"]
MAIN_PHASES = ("INSTALLATION", "REPLACEMENT", "MAINTENANCE")


def _check(phase: str | None, main: bool | None, start: time | None, end: time | None,
           lat: Decimal | None, lng: Decimal | None) -> None:
    if main and phase and phase not in MAIN_PHASES:
        raise ValueError("Deliverable utama hanya untuk fase instalasi, penggantian, atau pemeliharaan.")
    if start and end and end <= start:
        raise ValueError("Jam selesai item harus setelah jam mulai.")
    if (lat is None) != (lng is None):
        raise ValueError("Isi lintang dan bujur titik bersamaan.")


class PlanItemCreate(BaseModel):
    work_type_id: UUID
    title: str = Field(min_length=3, max_length=200)
    task_phase: TaskPhase = "INSTALLATION"
    is_main_deliverable: bool = False
    completion_id: UUID | None = None  # order klien
    depends_on_item_id: UUID | None = None  # prasyarat (mis. survei titik ini)
    target_qty: Decimal = Field(Decimal("1"), gt=0, le=Decimal("99999999"))
    start_time: time | None = None
    end_time: time | None = None
    location_name: str | None = Field(default=None, max_length=150)
    site_lat: Decimal | None = Field(default=None, ge=-90, le=90)
    site_lng: Decimal | None = Field(default=None, ge=-180, le=180)
    assigned_employee_ids: list[UUID] = Field(default_factory=list, max_length=50)
    notes: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def _rules(self) -> PlanItemCreate:
        _check(self.task_phase, self.is_main_deliverable, self.start_time, self.end_time, self.site_lat,
               self.site_lng)
        return self


class PlanItemUpdate(BaseModel):
    work_type_id: UUID | None = None
    title: str | None = Field(default=None, min_length=3, max_length=200)
    task_phase: TaskPhase | None = None
    is_main_deliverable: bool | None = None
    completion_id: UUID | None = None
    depends_on_item_id: UUID | None = None
    target_qty: Decimal | None = Field(default=None, gt=0, le=Decimal("99999999"))
    start_time: time | None = None
    end_time: time | None = None
    location_name: str | None = Field(default=None, max_length=150)
    site_lat: Decimal | None = Field(default=None, ge=-90, le=90)
    site_lng: Decimal | None = Field(default=None, ge=-180, le=180)
    assigned_employee_ids: list[UUID] | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def _rules(self) -> PlanItemUpdate:
        _check(self.task_phase, self.is_main_deliverable, self.start_time, self.end_time, self.site_lat,
               self.site_lng)
        return self


class ItemPhoto(BaseModel):
    """Foto realisasi: berkas /files + slot syarat foto (image_requirement) yang dipenuhinya."""

    file_id: UUID
    requirement_id: UUID | None = None


class ProgressIn(BaseModel):
    completed_qty: Decimal = Field(ge=0)
    photos: list[ItemPhoto] | None = Field(default=None, max_length=40)
    notes: str | None = Field(default=None, max_length=4000)


class RolloverRequest(BaseModel):
    """Ketua: pekerjaan belum selesai (hujan, izin, material) → minta digeser."""

    delay_reason: str = Field(min_length=3, max_length=1000)
    completed_qty: Decimal = Field(ge=0)


class RolloverDecision(BaseModel):
    """PM: setujui ke jadwal yang ada (`target_daily_plan_id`) atau tanggal baru (`target_date`), atau tolak."""

    approve: bool
    target_daily_plan_id: UUID | None = None
    target_date: date | None = None
    target_team_id: UUID | None = None
    note: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def _target(self) -> RolloverDecision:
        if self.approve and (self.target_daily_plan_id is None) == (self.target_date is None):
            raise ValueError("Pilih salah satu: jadwal tujuan yang sudah ada atau tanggal baru.")
        return self


class PlanItemOut(BaseModel):
    item_id: UUID
    daily_plan_id: UUID
    work_date: date
    work_type_id: UUID
    work_type_name: str
    title: str
    task_phase: TaskPhase
    is_main_deliverable: bool
    completion_id: UUID | None = None
    order_title: str | None = None
    depends_on_item_id: UUID | None = None
    depends_on_title: str | None = None
    depends_on_team_name: str | None = None  # tim pemilik prasyarat (bisa tim divisi lain)
    depends_on_done: bool = False  # pekerjaan yang ditunggu sudah selesai
    target_qty: Decimal
    completed_qty: Decimal
    progress_percent: Decimal
    status: ItemStatus
    rollover_approval_status: RolloverStatus
    approved_by_pm_id: UUID | None = None
    origin_item_id: UUID | None = None
    shifted_to_daily_id: UUID | None = None
    delay_reason: str | None = None
    notes: str | None = None
    start_time: time | None = None
    end_time: time | None = None
    location_name: str | None = None
    site_lat: Decimal | None = None
    site_lng: Decimal | None = None
    assigned_employee_ids: list[UUID] = []
    realization_photos_json: list[dict[str, Any]] = []
    update_at: datetime


class PrerequisiteOption(BaseModel):
    """Item yang boleh dijadikan prasyarat item baru di jadwal ini."""

    item_id: UUID
    title: str
    task_phase: str
    status: str
    work_date: date
    team_name: str | None = None
    other_team: bool = False  # milik tim/divisi lain di lokasi yang sama


class ChainStep(BaseModel):
    item_id: UUID
    daily_plan_id: UUID
    work_date: date
    status: ItemStatus
    target_qty: Decimal
    completed_qty: Decimal
    delay_reason: str | None = None
