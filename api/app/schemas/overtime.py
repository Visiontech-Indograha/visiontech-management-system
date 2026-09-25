"""
app/schemas/overtime.py
Skema permintaan & respons lembur (V-28) — domain.js REPORT_OVERTIME, REVIEW_OVERTIME.
"""
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class OvertimeCreate(BaseModel):
    """domain.js REPORT_OVERTIME. Aturan (jam 0–12, alasan wajib) diperiksa di OvertimeService
    agar urutan & pesannya sama dengan prototipe."""
    work_plan_id: UUID
    hours: float
    reason: str


class OvertimeReview(BaseModel):
    """domain.js REVIEW_OVERTIME: decision APPROVED | REJECTED (diperiksa di service)."""
    decision: str
    note: str | None = None


class OvertimeResponse(BaseModel):
    id: UUID
    work_plan_id: UUID
    plan_document_id: UUID | None
    employee_id: UUID
    work_date: date
    hours: float
    reason: str
    status: str
    reviewed_by: UUID | None
    reviewed_at: datetime | None
    review_note: str | None
    created_at: datetime


class OvertimeRecapRow(BaseModel):
    """Satu baris rekap dari v_overtime_recap (per karyawan per bulan)."""
    employee_id: UUID
    employee_name: str
    period_month: date
    approved_entries: int
    pending_entries: int
    approved_hours: float
