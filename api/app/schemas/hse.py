from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class IncidentCreate(BaseModel):
    work_plan_id: UUID
    occurred_on: date
    category: str
    severity: str
    description: str
    evidence_file_ids: list[UUID] = []

class IncidentResolve(BaseModel):
    resolution_note: str

class IncidentResponse(BaseModel):
    id: UUID
    work_plan_id: UUID
    reported_by: UUID
    occurred_on: date
    category: str
    severity: str
    description: str
    status: str
    resolved_by: UUID | None
    resolved_at: datetime | None
    resolution_note: str | None
    created_at: datetime
    
class DailyReportCreate(BaseModel):
    body: str
    obstacle: str
    evidence_file_ids: list[UUID] = []

class DailyReportResponse(BaseModel):
    id: UUID
    work_plan_day_id: UUID
    status: str
    body: str
    obstacle: str
    submitted_by: UUID | None
    submitted_at: datetime | None
    reviewed_at: datetime | None
