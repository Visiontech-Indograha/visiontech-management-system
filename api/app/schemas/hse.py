from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from uuid import UUID

class IncidentCreate(BaseModel):
    work_plan_id: UUID
    occurred_on: date
    category: str
    severity: str
    description: str
    evidence_file_ids: List[UUID] = []

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
    resolved_by: Optional[UUID]
    resolved_at: Optional[datetime]
    resolution_note: Optional[str]
    created_at: datetime
    
class DailyReportCreate(BaseModel):
    body: str
    obstacle: str
    evidence_file_ids: List[UUID] = []

class DailyReportResponse(BaseModel):
    id: UUID
    work_plan_day_id: UUID
    status: str
    body: str
    obstacle: str
    submitted_by: Optional[UUID]
    submitted_at: Optional[datetime]
    reviewed_at: Optional[datetime]
