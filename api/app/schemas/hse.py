from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class IncidentCreate(BaseModel):
    work_plan_id: UUID
    # occurred_on tidak diterima dari klien: tanggal insiden = hari ini menurut server (V-10).
    # Nilai enum DB (db/01 incident_category / incident_severity): nilai lain → 422, bukan 500.
    category: Literal["K3_RINGAN", "K3_BERAT", "K3_LINGKUNGAN", "K3_HAMPIR", "ASET"]
    severity: Literal["RENDAH", "SEDANG", "TINGGI", "KRITIS"]
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
    evidence_file_ids: list[UUID] = []
    
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


# ── Dipindah dari api/v1/endpoints/hse.py (R-28 M2b) ──
class ReportReviewRequest(BaseModel):
    decision: str
    note: str | None = None
