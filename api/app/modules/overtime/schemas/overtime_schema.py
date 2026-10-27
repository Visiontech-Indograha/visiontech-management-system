"""
app/schemas/overtime.py

Request and response schemas for overtime reporting and reviewing (V-28).
Corresponding to domain transactions: REPORT_OVERTIME and REVIEW_OVERTIME.
"""
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class OvertimeCreate(BaseModel):
    """
    Schema for reporting overtime (domain.js REPORT_OVERTIME).

    Aturan validasi seperti jam 0–12 dan alasan yang wajib diisi akan
    diperiksa secara terpusat di OvertimeService. Hal ini dilakukan
    agar urutan dan pesan kesalahan yang muncul sama persis dengan prototipe.
    """
    daily_plan_id: UUID
    hours: float
    reason: str = Field(max_length=1000)


class OvertimeReview(BaseModel):
    """
    Schema for reviewing an overtime request (domain.js REVIEW_OVERTIME).

    Status keputusan (decision) berupa APPROVED atau REJECTED, dan akan
    diperiksa serta diproses di dalam service.
    """
    decision: str = Field(max_length=20)
    note: str | None = Field(default=None, max_length=1000)


class OvertimeResponse(BaseModel):
    """
    Schema for a detailed overtime record response.
    """
    id: UUID
    daily_plan_id: UUID | None
    employee_id: UUID
    employee_name: str
    work_date: date
    hours: float
    reason: str = Field(max_length=1000)
    status: str
    reviewed_by: UUID | None
    reviewed_at: datetime | None
    review_note: str | None
    created_at: datetime


class OvertimeRecapRow(BaseModel):
    """
    Schema for a summarized overtime record from the recap view.
    Satu baris rekap yang diambil dari `v_overtime_recap`
    (direkapitulasi per karyawan per bulan).
    """
    employee_id: UUID
    employee_name: str
    period_month: date
    approved_entries: int
    pending_entries: int
    approved_hours: float
