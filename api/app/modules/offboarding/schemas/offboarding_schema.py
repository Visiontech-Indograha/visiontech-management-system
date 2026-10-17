"""
app/modules/offboarding/schemas/offboarding_schema.py
Skema data Pydantic untuk Offboarding Karyawan dan Clearance Aset.
"""
from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class OffboardingReason(StrEnum):
    PKWT_EXPIRED = "PKWT_EXPIRED"
    RESIGN = "RESIGN"
    TERMINATED = "TERMINATED"
    RETIRED = "RETIRED"


class OffboardingStatus(StrEnum):
    ACTIVE = "active"
    IN_PROCESS = "in_process"
    OFFBOARDED = "offboarded"


class ClearanceItemOut(BaseModel):
    clearance_item_id: UUID
    offboarding_id: UUID
    assignment_id: UUID
    asset_type: str | None = None
    asset_name: str | None = None
    return_condition: str
    handover_photo_path: str | None = None
    verified_by_id: UUID | None = None
    verified_by_name: str | None = None
    verified_at: datetime | None = None
    create_at: datetime


class ClearanceItemVerify(BaseModel):
    return_condition: str = Field(..., min_length=2, max_length=100)
    handover_photo_path: str | None = None


class OffboardingCreate(BaseModel):
    employee_id: UUID
    reason_type: OffboardingReason
    effective_date: date
    notes: str | None = None


class OffboardingApprove(BaseModel):
    approval_type: str = Field("HR", description="'PM' atau 'HR'")
    notes: str | None = None


class OffboardingListItem(BaseModel):
    offboarding_id: UUID
    employee_id: UUID
    employee_name: str | None = None
    employee_no: str | None = None
    division_name: str | None = None
    reason_type: str
    submission_date: datetime
    effective_date: date
    is_all_assets_returned: bool
    status: str
    approved_by_pm_id: UUID | None = None
    approved_by_hr_id: UUID | None = None
    notes: str | None = None
    create_at: datetime


class OffboardingDetail(OffboardingListItem):
    clearance_items: list[ClearanceItemOut] = []
