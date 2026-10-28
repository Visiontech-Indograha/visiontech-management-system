"""
app/modules/work_plans/schemas/daily_correction_schema.py
Skema koreksi laporan harian: ketua tim mengajukan, PM menyetujui / mengembalikan sampai diterima.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

CorrectionStatus = Literal["REQUESTED", "REVISING", "IN_REVIEW", "ACCEPTED", "REJECTED"]
CorrectionDecision = Literal["APPROVE", "REJECT", "ACCEPT", "RETURN"]


class CorrectionCreate(BaseModel):
    reason: str = Field(min_length=5, max_length=1000)


class CorrectionDecide(BaseModel):
    """APPROVE/REJECT untuk permintaan awal; ACCEPT/RETURN untuk hasil revisi. Menolak/mengembalikan wajib catatan."""

    decision: CorrectionDecision
    note: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def _note_required(self) -> CorrectionDecide:
        if self.decision in ("REJECT", "RETURN") and not (self.note and self.note.strip()):
            raise ValueError("Catatan wajib diisi saat menolak atau mengembalikan untuk revisi.")
        return self


class CorrectionOut(BaseModel):
    correction_id: UUID
    daily_plan_id: UUID
    work_date: date
    site_name: str
    team_name: str
    requested_by_id: UUID
    requested_by_name: str
    reason: str
    status: CorrectionStatus
    review_note: str | None = None
    reviewed_at: datetime | None = None
    revision_count: int
    create_at: datetime
