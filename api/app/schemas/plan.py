from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from uuid import UUID

class WorkPlanBase(BaseModel):
    title: str
    unit_id: UUID
    site_id: Optional[UUID] = None
    location_text: str
    description: Optional[str] = None
    period_start: date
    period_end: date
    pm_employee_id: UUID
    leader_employee_id: Optional[UUID] = None

class WorkPlanCreate(WorkPlanBase):
    pass

class WorkPlanUpdate(BaseModel):
    title: Optional[str] = None
    site_id: Optional[UUID] = None
    location_text: Optional[str] = None
    description: Optional[str] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    leader_employee_id: Optional[UUID] = None
    row_version: int

class WorkPlanResponse(WorkPlanBase):
    id: UUID
    number: Optional[str] = None
    status: str
    revision: int
    row_version: int
    cancellation_reason: Optional[str] = None

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
