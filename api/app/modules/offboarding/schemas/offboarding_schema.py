"""
app/modules/offboarding/schemas/offboarding_schema.py
Offboarding PKWT & clearance aset (Milestone 9, docs/35 §7).
Status: CLEARANCE_PENDING (masih ada aset) → SUBMITTED (aset lengkap, menunggu persetujuan) → APPROVED (PM & HR
setuju, menunggu tanggal efektif) → COMPLETED (karyawan `offboarded`, akun dinonaktifkan).
"""
from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class OffboardingReason(StrEnum):
    PKWT_EXPIRED = "PKWT_EXPIRED"
    RESIGN = "RESIGN"
    TERMINATED = "TERMINATED"
    RETIRED = "RETIRED"


class OffboardingStatus(StrEnum):
    SUBMITTED = "SUBMITTED"
    CLEARANCE_PENDING = "CLEARANCE_PENDING"
    APPROVED = "APPROVED"
    COMPLETED = "COMPLETED"


ReturnCondition = Literal["GOOD", "DAMAGED", "LOST"]


class ClearanceItemOut(BaseModel):
    clearance_item_id: UUID
    offboarding_id: UUID
    assignment_id: UUID
    asset_type: str | None = None
    asset_name: str | None = None
    asset_code: str | None = None
    loaned_at: datetime | None = None
    return_condition: str
    handover_photo_path: str | None = None
    verified_by_id: UUID | None = None
    verified_by_name: str | None = None
    verified_at: datetime | None = None


class ClearanceItemVerify(BaseModel):
    return_condition: ReturnCondition
    # Foto serah terima (file_object) wajib bila barang kembali; LOST boleh tanpa foto.
    handover_file_id: UUID | None = None

    @model_validator(mode="after")
    def _photo(self) -> ClearanceItemVerify:
        if self.return_condition != "LOST" and self.handover_file_id is None:
            raise ValueError("Foto serah terima wajib untuk barang yang dikembalikan.")
        return self


class OffboardingCreate(BaseModel):
    employee_id: UUID
    reason_type: OffboardingReason
    # Kosong + PKWT_EXPIRED → tanggal akhir PKWT karyawan.
    effective_date: date | None = None
    notes: str | None = Field(None, max_length=2000)


class OffboardingApprove(BaseModel):
    approval_type: Literal["PM", "HR"]


class OffboardingCancel(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500)


class OffboardingListItem(BaseModel):
    offboarding_id: UUID
    employee_id: UUID
    employee_name: str | None = None
    employee_photo_file_id: UUID | None = None
    employee_no: str | None = None
    division_name: str | None = None
    reason_type: str
    submission_date: datetime
    effective_date: date
    is_all_assets_returned: bool
    status: str
    approved_by_pm_id: UUID | None = None
    approved_by_pm_name: str | None = None
    approved_by_hr_id: UUID | None = None
    approved_by_hr_name: str | None = None
    pending_items: int = 0
    notes: str | None = None
    create_at: datetime


class OffboardingDetail(OffboardingListItem):
    clearance_items: list[ClearanceItemOut] = []


class PkwtExpiringRow(BaseModel):
    """Karyawan PKWT yang kontraknya berakhir dalam rentang & belum diproses offboarding."""
    employee_id: UUID
    employee_no: str
    full_name: str
    division_name: str | None = None
    pkwt_end_date: date
    open_loans: int


class CompleteDueResult(BaseModel):
    completed: int
