"""
app/schemas/hse.py

Request and response schemas for HSE (Health, Safety, and Environment)
incident reporting and daily operational reports.
"""
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.modules.work_types.schemas.work_type_schema import EvidenceIn


class IncidentCreate(BaseModel):
    """
    Schema for creating a new HSE incident report.
    """
    work_plan_id: UUID
    # occurred_on tidak diterima dari klien: tanggal insiden selalu dianggap hari ini menurut server (V-10).
    # Nilai enumerasi DB (db/01 incident_category / incident_severity).
    # Jika ada nilai lain yang diberikan, sistem akan mengembalikan galat 422, bukan 500.
    category: Literal["K3_RINGAN", "K3_BERAT", "K3_LINGKUNGAN", "K3_HAMPIR", "ASET"]
    severity: Literal["RENDAH", "SEDANG", "TINGGI", "KRITIS"]
    description: str
    evidence_file_ids: list[UUID] = []


class IncidentResolve(BaseModel):
    """
    Schema for resolving a reported incident.
    """
    resolution_note: str


class IncidentResponse(BaseModel):
    """
    Schema for a detailed incident report response.
    """
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
    """
    Schema for submitting a daily HSE or operational report.
    """
    body: str
    obstacle: str
    evidence_file_ids: list[UUID] = []
    evidence: list[EvidenceIn] = []   # T9: foto berlabel slot template + sumber


class DailyReportResponse(BaseModel):
    """
    Schema for a daily report response.
    """
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
    """
    Schema for reviewing a submitted daily report.
    """
    decision: str
    note: str | None = None
