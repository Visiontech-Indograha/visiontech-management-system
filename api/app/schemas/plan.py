from datetime import date
from uuid import UUID

from pydantic import BaseModel


class WorkPlanBase(BaseModel):
    title: str
    unit_id: UUID
    site_id: UUID | None = None
    location_text: str
    description: str | None = None
    period_start: date
    period_end: date
    pm_employee_id: UUID
    leader_employee_id: UUID | None = None

class WorkPlanCreate(WorkPlanBase):
    pass

class WorkPlanUpdate(BaseModel):
    title: str | None = None
    site_id: UUID | None = None
    location_text: str | None = None
    description: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    leader_employee_id: UUID | None = None
    row_version: int

class WorkPlanResponse(WorkPlanBase):
    id: UUID
    number: str | None = None
    status: str
    revision: int
    row_version: int
    cancellation_reason: str | None = None
    appeal_reason: str | None = None
    category: str | None = None   # alur SK v2


class AssignmentEmployeeOption(BaseModel):
    id: UUID
    full_name: str
    position: str
    unit_id: UUID | None = None


class PlanAssignmentOptions(BaseModel):
    can_choose_pm: bool
    fixed_pm_employee_id: UUID | None = None
    fixed_unit_id: UUID | None = None
    pm_options: list[AssignmentEmployeeOption]
    personnel_options: list[AssignmentEmployeeOption]

class PlanMemberListResponse(BaseModel):
    id: UUID
    employee_id: UUID
    role_in_plan: str
    valid_from: date
    valid_to: date
    
class PlanDayCreate(BaseModel):
    work_date: date
    title: str
    sort_order: int = 0

class PlanTaskCreate(BaseModel):
    title: str
    sort_order: int = 0

class PlanDayResponse(PlanDayCreate):
    id: UUID
    work_plan_id: UUID

class PlanTaskResponse(PlanTaskCreate):
    id: UUID
    work_plan_day_id: UUID
    is_done: bool


# ── Dipindah dari api/v1/endpoints/work_plans.py (R-28 M2b) ──
class DayTaskInput(BaseModel):
    title: str


class DayPlanRequest(BaseModel):
    title: str
    tasks: list[DayTaskInput]
