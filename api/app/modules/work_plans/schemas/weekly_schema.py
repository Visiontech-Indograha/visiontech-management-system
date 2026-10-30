"""
app/modules/work_plans/schemas/weekly_schema.py
Matriks alokasi mingguan (GET /work-plans/weekly): tim (baris) × 7 hari Senin–Minggu (kolom) untuk divisi yang
dikelola PM/OM. Satu tim paling banyak satu jadwal per tanggal, sehingga satu sel = satu jadwal (atau kosong).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.work_plans.schemas.daily_plan_schema import DailyKind, DailyStatus


class WeeklyItemBrief(BaseModel):
    item_id: UUID
    title: str
    work_type_name: str | None = None
    completion_id: UUID | None = None
    target_qty: Decimal | None = None
    completed_qty: Decimal | None = None
    status: str


class WeeklyOrderRef(BaseModel):
    """Order klien yang dikerjakan pada sel. `remaining_qty` = total - selesai; `unscheduled_qty` = total - sudah
    dijadwalkan di semua jadwal (sisa yang belum dialokasikan)."""

    completion_id: UUID
    client_name: str | None = None
    project_title: str | None = None
    order_number: str | None = None
    total_target_unit: int
    remaining_qty: float
    unscheduled_qty: float


class WeeklyCell(BaseModel):
    work_date: date
    daily_plan_id: UUID | None = None
    status: DailyStatus | None = None
    kind: DailyKind | None = None
    item_count: int = 0
    items: list[WeeklyItemBrief] = Field(default_factory=list, max_length=20)
    orders: list[WeeklyOrderRef] = Field(default_factory=list)


class WeeklyRow(BaseModel):
    team_id: UUID
    team_name: str
    division_id: UUID
    division_name: str
    leader_name: str | None = None
    cells: list[WeeklyCell]


class WeeklyDivision(BaseModel):
    division_id: UUID
    name: str


class WeeklyMatrixOut(BaseModel):
    week_start: date
    week_end: date
    days: list[date]
    divisions: list[WeeklyDivision]
    rows: list[WeeklyRow]
