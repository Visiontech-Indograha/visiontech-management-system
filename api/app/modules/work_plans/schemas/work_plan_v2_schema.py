"""
api/app/modules/work_plans/schemas/work_plan_v2_schema.py
Skema Pydantic v2 untuk modul Rencana Kerja V2:
- work_plan_weekly
- work_plan_daily
- work_plan_item
- Form Options V2
"""

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ── FORM OPTIONS V2 SCHEMAS ───────────────────────────────────

class TeamMemberOptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    employee_id: UUID
    full_name: str
    position: str


class TeamOptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    team_id: UUID
    name: str
    division_id: UUID
    leader_employee_id: UUID
    leader_name: str | None = None
    leader_position: str | None = None
    members: list[TeamMemberOptionOut] = []


class DivisionOptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    division_id: UUID
    name: str


class WorkTypeOptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    work_type_id: UUID
    name: str
    division_id: UUID
    description: str | None = None
    image_requirements_count: int = 0


class WorkCompletionOptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    completion_id: UUID
    client_name: str
    project_title: str
    order_number: str | None = None
    division_id: UUID | None = None
    order_status: str


class OfficeSiteOptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    office_id: UUID
    name: str
    address: str | None = None
    latitude: float
    longitude: float
    radius_m: int = 150


class ToolOptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tool_id: UUID
    name: str
    tool_code: str
    division_id: UUID | None = None
    category: str | None = None


class VehicleOptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    vehicle_id: UUID
    name: str
    number_plate: str
    vehicle_type: str
    division_id: UUID | None = None


class WorkPlanFormOptionsV2Out(BaseModel):
    divisions: list[DivisionOptionOut] = []
    teams: list[TeamOptionOut] = []
    work_types: list[WorkTypeOptionOut] = []
    work_completions: list[WorkCompletionOptionOut] = []
    offices: list[OfficeSiteOptionOut] = []
    tools: list[ToolOptionOut] = []
    vehicles: list[VehicleOptionOut] = []


# ── ITEM SCHEMAS (work_plan_item) ─────────────────────────────

class PlanItemCreateIn(BaseModel):
    daily_plan_id: UUID | None = None
    weekly_plan_id: UUID | None = None
    work_type_id: UUID
    title: str = Field(min_length=3, max_length=255)
    task_phase: str = "MAIN_INSTALLATION"
    is_main_deliverable: bool = True
    depends_on_item_id: UUID | None = None
    completion_id: UUID | None = None
    target_qty: Decimal = Field(gt=Decimal("0"))
    completed_qty: Decimal = Decimal("0.00")
    progress_percent: Decimal = Decimal("0.00")
    start_time: time | None = None
    end_time: time | None = None
    location_name: str | None = None
    site_lat: Decimal | None = None
    site_lng: Decimal | None = None
    assigned_employee_ids: list[UUID] = []
    status: str = "PENDING"
    rollover_approval_status: str = "NONE"
    delay_reason: str | None = None
    realization_photos_json: list[dict[str, Any]] = []


class PlanItemUpdateIn(BaseModel):
    title: str | None = None
    task_phase: str | None = None
    is_main_deliverable: bool | None = None
    depends_on_item_id: UUID | None = None
    work_type_id: UUID | None = None
    completion_id: UUID | None = None
    target_qty: Decimal | None = None
    completed_qty: Decimal | None = None
    progress_percent: Decimal | None = None
    start_time: time | None = None
    end_time: time | None = None
    location_name: str | None = None
    site_lat: Decimal | None = None
    site_lng: Decimal | None = None
    assigned_employee_ids: list[UUID] | None = None
    status: str | None = None
    rollover_approval_status: str | None = None
    delay_reason: str | None = None
    realization_photos_json: list[dict[str, Any]] | None = None


class PlanItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_id: UUID
    daily_plan_id: UUID
    weekly_plan_id: UUID | None = None
    work_type_id: UUID
    work_type_name: str | None = None
    title: str
    task_phase: str = "MAIN_INSTALLATION"
    is_main_deliverable: bool = True
    depends_on_item_id: UUID | None = None
    target_qty: Decimal
    completed_qty: Decimal
    progress_percent: Decimal
    status: str
    rollover_approval_status: str
    approved_by_pm_id: UUID | None = None
    origin_item_id: UUID | None = None
    shifted_to_daily_id: UUID | None = None
    allocated_to_weekly_id: UUID | None = None
    delay_reason: str | None = None
    realization_photos_json: list[dict[str, Any]] = []
    completion_id: UUID | None = None
    client_name: str | None = None
    project_title: str | None = None
    order_number: str | None = None
    start_time: time | None = None
    end_time: time | None = None
    location_name: str | None = None
    site_lat: Decimal | None = None
    site_lng: Decimal | None = None
    assigned_employee_ids: list[UUID] = []
    create_at: datetime | None = None
    update_at: datetime | None = None


# ── DAILY PLAN SCHEMAS (work_plan_daily) ──────────────────────

class DailyPlanCreateIn(BaseModel):
    division_id: UUID
    team_id: UUID
    weekly_plan_id: UUID | None = None
    work_date: date
    site_name: str = Field(min_length=2, max_length=255)
    site_lat: Decimal = Decimal("3.5952")
    site_lng: Decimal = Decimal("98.6722")
    attendance_radius_m: int = 150
    clock_in_time: time = time(8, 0)
    clock_out_time: time = time(17, 0)
    status: str = "SCHEDULED"
    is_holiday: bool = False
    items: list[PlanItemCreateIn] = []


class DailyPlanUpdateIn(BaseModel):
    division_id: UUID | None = None
    team_id: UUID | None = None
    work_date: date | None = None
    site_name: str | None = None
    site_lat: Decimal | None = None
    site_lng: Decimal | None = None
    attendance_radius_m: int | None = None
    clock_in_time: time | None = None
    clock_out_time: time | None = None
    status: str | None = None
    is_holiday: bool | None = None
    rejection_reason: str | None = None


class DailyPlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    daily_plan_id: UUID
    division_id: UUID
    division_name: str | None = None
    team_id: UUID
    team_name: str | None = None
    weekly_plan_id: UUID | None = None
    work_date: date
    site_name: str
    site_lat: Decimal
    site_lng: Decimal
    attendance_radius_m: int
    clock_in_time: time
    clock_out_time: time
    status: str
    is_holiday: bool = False
    created_by_id: UUID | None = None
    created_by_name: str | None = None
    approved_by_pm_id: UUID | None = None
    approved_by_pm_name: str | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None
    items: list[PlanItemOut] = []
    create_at: datetime | None = None
    update_at: datetime | None = None


# ── WEEKLY PLAN SCHEMAS (work_plan_weekly) ────────────────────

class WeeklyPlanCreateIn(BaseModel):
    division_id: UUID
    team_id: UUID
    week_number: int = Field(ge=1, le=53)
    year: int = Field(ge=2020, le=2100)
    start_date: date
    end_date: date
    status: str = "APPROVED"
    tool_ids: list[UUID] = []
    vehicle_id: UUID | None = None
    driver_employee_id: UUID | None = None
    days: list[DailyPlanCreateIn] = []


class WeeklyPlanUpdateIn(BaseModel):
    division_id: UUID | None = None
    team_id: UUID | None = None
    week_number: int | None = None
    year: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: str | None = None
    tool_ids: list[UUID] | None = None
    vehicle_id: UUID | None = None
    driver_employee_id: UUID | None = None
    days: list[DailyPlanCreateIn] | None = None


class WeeklyPlanDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    weekly_plan_id: UUID
    division_id: UUID
    division_name: str
    team_id: UUID
    team_name: str
    leader_name: str | None = None
    leader_employee_id: UUID | None = None
    week_number: int
    year: int
    start_date: date
    end_date: date
    created_by_id: UUID
    created_by_name: str | None = None
    approved_by_pm_id: UUID | None = None
    approved_by_pm_name: str | None = None
    status: str
    tool_ids: list[UUID] = []
    vehicle_id: UUID | None = None
    driver_employee_id: UUID | None = None
    days: list[DailyPlanOut] = []
    create_at: datetime | None = None
    update_at: datetime | None = None


class WeeklyPlanListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    weekly_plan_id: UUID
    division_id: UUID
    division_name: str
    team_id: UUID
    team_name: str
    week_number: int
    year: int
    start_date: date
    end_date: date
    status: str
    total_days: int = 0
    total_items: int = 0
    create_at: datetime | None = None


# ── WEEKLY CALENDAR MATRIX & PROJECT SCHEDULE SCHEMAS ─────────

class WeeklyMatrixDayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    day_name: str  # 'Senin', 'Selasa', dst
    daily_plan_id: UUID | None = None
    division_id: UUID | None = None
    team_id: UUID | None = None
    site_name: str | None = None
    site_lat: Decimal | None = None
    site_lng: Decimal | None = None
    status: str | None = None  # 'DRAFT', 'SUBMITTED', 'APPROVED', 'ONGOING', 'COMPLETED'
    approved_by_pm_id: UUID | None = None
    approved_by_pm_name: str | None = None
    approved_at: datetime | None = None
    is_holiday: bool = False
    items: list[PlanItemOut] = []
    total_target_qty: Decimal = Decimal("0.00")
    total_completed_qty: Decimal = Decimal("0.00")
    progress_percent: Decimal = Decimal("0.00")


class WeeklyCalendarMatrixOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    start_date: date
    end_date: date
    division_id: UUID | None = None
    division_name: str | None = None
    team_id: UUID | None = None
    team_name: str | None = None
    leader_name: str | None = None
    total_days: int = 7
    scheduled_days: int = 0
    total_items: int = 0
    all_approved: bool = False
    days: list[WeeklyMatrixDayOut] = []


class ProjectPhaseSummaryOut(BaseModel):
    task_phase: str
    phase_label: str
    total_target_qty: Decimal
    total_completed_qty: Decimal
    progress_percent: Decimal
    is_completed: bool
    items_count: int


class ProjectScheduleOut(BaseModel):
    completion_id: UUID
    client_name: str
    project_title: str
    order_number: str | None = None
    division_id: UUID | None = None
    division_name: str | None = None
    order_status: str
    start_work_date: date | None = None
    end_work_date: date | None = None
    total_target_deliverables: Decimal = Decimal("0.00")
    total_completed_deliverables: Decimal = Decimal("0.00")
    deliverables_progress_percent: Decimal = Decimal("0.00")
    is_ready_for_completion: bool = False
    phases: list[ProjectPhaseSummaryOut] = []
    timeline_items: list[PlanItemOut] = []


class BulkApproveDailyPlansIn(BaseModel):
    team_id: UUID
    start_date: date
    end_date: date


class BulkApproveDailyPlansOut(BaseModel):
    success: bool
    approved_count: int
    message: str
