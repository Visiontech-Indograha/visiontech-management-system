"""
app/schemas/overtime.py
Skema permintaan & respons lembur (V-28) — domain.js REPORT_OVERTIME, REVIEW_OVERTIME.
"""
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, field_validator


class OvertimeCreate(BaseModel):
    """domain.js REPORT_OVERTIME: ketua mengajukan lembur pada SK yang sedang berjalan."""
    work_plan_id: UUID
    hours: float
    reason: str

    @field_validator("hours")
    @classmethod
    def hours_valid(cls, v: float) -> float:
        if not (0 < v <= 12):
            raise ValueError("Jam lembur tidak valid (harus 0 < jam ≤ 12).")
        return v

    @field_validator("reason")
    @classmethod
    def reason_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Alasan lembur wajib diisi.")
        return v.strip()


class OvertimeReview(BaseModel):
    """domain.js REVIEW_OVERTIME: PM unit/OPS menyetujui atau menolak lembur."""
    decision: str          # APPROVED | REJECTED
    note: str | None = None

    @field_validator("decision")
    @classmethod
    def decision_valid(cls, v: str) -> str:
        if v not in ("APPROVED", "REJECTED"):
            raise ValueError("Keputusan harus APPROVED atau REJECTED.")
        return v


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
