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

from app.modules.work_plans.schemas.plan_item_schema import PlanItemCreate

DailyStatus = Literal["DRAFT", "SUBMITTED", "APPROVED", "ONGOING", "COMPLETED"]
# WORK = jadwal kerja; STANDBY = tim siaga menunggu perintah PM (tanpa item wajib).
DailyKind = Literal["WORK", "STANDBY"]


def _check_hours(clock_in: time | None, clock_out: time | None) -> None:
    if clock_in and clock_out and clock_out <= clock_in:
        raise ValueError("Jam pulang harus setelah jam masuk.")


class DailyPlanCreate(BaseModel):
    division_id: UUID
    team_id: UUID
    project_id: UUID | None = None  # proyek/SPK divisi yang sama (Milestone 10)
    work_date: date
    kind: DailyKind = "WORK"
    site_name: str | None = Field(default=None, min_length=2, max_length=150)
    site_lat: Decimal | None = Field(default=None, ge=-90, le=90)
    site_lng: Decimal | None = Field(default=None, ge=-180, le=180)
    attendance_radius_m: int | None = Field(default=150, ge=10, le=5000)
    clock_in_time: time = time(7, 0)
    clock_out_time: time = time(16, 0)
    # F10: tanggal lampau (maks. 7 hari) hanya untuk PM/OM dan wajib beralasan; tercatat di audit.
    backdate_reason: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def _hours(self) -> DailyPlanCreate:
        _check_hours(self.clock_in_time, self.clock_out_time)
        if (self.site_lat is None) != (self.site_lng is None):
            raise ValueError("Latitude dan longitude harus diisi bersama atau dibiarkan kosong.")
        return self


class RecentSiteOut(BaseModel):
    """Lokasi site yang pernah dipakai tim (untuk dipilih ulang di form Jadwal harian)."""

    site_name: str
    site_lat: Decimal
    site_lng: Decimal
    attendance_radius_m: int | None = None
    last_used: date


class DailyPlanUpdate(BaseModel):
    team_id: UUID | None = None
    project_id: UUID | None = None
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


class DailyBulkIn(BaseModel):
    """Alokasi massal (matriks mingguan): banyak tim × banyak tanggal dalam satu permintaan."""

    division_id: UUID
    team_ids: list[UUID] = Field(min_length=1, max_length=30)
    work_dates: list[date] = Field(min_length=1, max_length=31)
    kind: DailyKind = "WORK"
    # DRAFT = belum diajukan. APPROVED hanya untuk siaga (jadwal kerja butuh item dulu).
    target: Literal["DRAFT", "APPROVED"] = "DRAFT"
    site_name: str | None = Field(default=None, min_length=2, max_length=150)
    site_lat: Decimal | None = Field(default=None, ge=-90, le=90)
    site_lng: Decimal | None = Field(default=None, ge=-180, le=180)
    attendance_radius_m: int | None = Field(default=150, ge=10, le=5000)

    @model_validator(mode="after")
    def _rules(self) -> DailyBulkIn:
        if (self.site_lat is None) != (self.site_lng is None):
            raise ValueError("Latitude dan longitude harus diisi bersama atau dibiarkan kosong.")
        if self.target == "APPROVED" and self.kind != "STANDBY":
            raise ValueError("Jadwal kerja disetujui setelah berisi pekerjaan; gunakan target DRAFT.")
        return self


class DailyBulkStandbyIn(BaseModel):
    """Siaga untuk hari kosong: tim × tanggal; sel yang sudah punya jadwal dilewati."""

    division_id: UUID
    team_ids: list[UUID] = Field(min_length=1, max_length=30)
    work_dates: list[date] = Field(min_length=1, max_length=31)


class DailyBulkCellOut(BaseModel):
    team_id: UUID
    work_date: date
    status: Literal["CREATED", "SKIPPED"]
    daily_plan_id: UUID | None = None
    reason: str | None = None  # kode galat tetap, mis. TEAM_DAY_TAKEN
    message: str | None = None


class DailyBulkOut(BaseModel):
    created: int
    skipped: int
    cells: list[DailyBulkCellOut]


class DailyActivateIn(BaseModel):
    """Ubah jadwal siaga jadi pekerjaan klien: minimal satu item (pekerjaan, order, lokasi)."""

    items: list[PlanItemCreate] = Field(min_length=1, max_length=50)


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
    depends_on_item_id: UUID | None = None  # titik survei → tugas survei induknya
    location_name: str | None = None
    target_qty: Decimal
    completed_qty: Decimal
    status: str
    rollover_approval_status: str
    delay_reason: str | None = None


class DailyPlanOut(BaseModel):
    daily_plan_id: UUID
    division_id: UUID
    project_id: UUID | None = None
    project_title: str | None = None
    division_name: str
    team_id: UUID
    team_name: str
    leader_employee_id: UUID
    leader_name: str
    leader_phone: str | None = None
    pm_name: str | None = None  # PM divisi — kontak ketua tim
    pm_phone: str | None = None
    work_date: date
    site_name: str | None = None
    site_lat: Decimal | None = None
    site_lng: Decimal | None = None
    attendance_radius_m: int | None = None
    clock_in_time: time
    clock_out_time: time
    status: DailyStatus
    kind: DailyKind = "WORK"
    created_by_id: UUID
    approved_by_pm_id: UUID | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None
    item_count: int = 0
    done_count: int = 0
    progress_pct: int = 0  # rata-rata jumlah dikerjakan/target, 0–100
    phases: list[str] = []  # SURVEY/PREPARATION/INSTALLATION/REPLACEMENT/MAINTENANCE


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
