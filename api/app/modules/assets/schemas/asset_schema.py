"""
app/modules/assets/schemas/asset_schema.py
Skema inventaris aset V2 (Milestone 4): alat (tool), kendaraan (vehicle) beserta berkas & inspeksinya,
dan peminjaman (asset_assignment). Berkas/foto dirujuk lewat `file_id` (file_object); kolom `*_path`
menyimpan `file_object.storage_key`.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

Ownership = Literal["PERSONAL_LOAN", "SHARED_TOOL"]
ToolCategory = Literal["BAJU", "LAPTOP", "SEPATU", "BOR", "TANGGA", "LAINNYA"]
VehicleType = Literal["Motorcycle", "Car", "Truck"]
AssetStatus = Literal["ready", "allocated", "loaned", "damaged", "lost", "pension"]
# Status yang boleh diubah manual; allocated/loaned hanya lewat peminjaman.
ManualStatus = Literal["ready", "damaged", "lost", "pension"]
ReturnCondition = Literal["ready", "damaged", "lost"]
VehicleFileType = Literal["STNK", "BPKB", "KIR"]
InspectionType = Literal["day", "month", "year", "repair", "profile"]
AssetType = Literal["TOOL", "VEHICLE"]


def normalise_plate(value: str) -> str:
    """'bk1452zn' / 'BK  1452 ZN' → 'BK 1452 ZN'."""
    text = re.sub(r"[^A-Z0-9]", "", value.upper())
    m = re.fullmatch(r"([A-Z]{1,2})(\d{1,4})([A-Z]{0,3})", text)
    return " ".join(p for p in m.groups() if p) if m else " ".join(value.upper().split())


# ── Alat ───────────────────────────────────────────────────────────────────────
class ToolCreate(BaseModel):
    office_id: UUID
    division_id: UUID | None = None
    ownership_type: Ownership
    category: ToolCategory
    name: str = Field(min_length=2, max_length=100)
    tool_code: str = Field(min_length=2, max_length=50)
    photo_file_id: UUID | None = None

    @field_validator("tool_code")
    @classmethod
    def _code(cls, value: str) -> str:
        return value.strip().upper()


class ToolUpdate(BaseModel):
    office_id: UUID | None = None
    division_id: UUID | None = None
    ownership_type: Ownership | None = None
    category: ToolCategory | None = None
    name: str | None = Field(default=None, min_length=2, max_length=100)
    tool_code: str | None = Field(default=None, min_length=2, max_length=50)
    photo_file_id: UUID | None = None

    @field_validator("tool_code")
    @classmethod
    def _code(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else value


class AssetHolder(BaseModel):
    """Peminjaman yang sedang berjalan atas aset ini (returned_at IS NULL)."""

    assignment_id: UUID | None = None
    holder_employee_id: UUID | None = None
    holder_name: str | None = None
    daily_plan_id: UUID | None = None


class ToolOut(AssetHolder):
    tool_id: UUID
    office_id: UUID
    office_name: str
    division_id: UUID | None = None
    division_name: str | None = None
    ownership_type: Ownership
    category: ToolCategory
    name: str
    tool_code: str
    status: AssetStatus
    photo_file_id: UUID | None = None


# ── Kendaraan ──────────────────────────────────────────────────────────────────
class VehicleCreate(BaseModel):
    office_id: UUID
    division_id: UUID
    vehicle_type: VehicleType
    name: str = Field(min_length=2, max_length=150)
    number_plate: str = Field(min_length=3, max_length=20)
    photo_file_id: UUID | None = None

    @field_validator("number_plate")
    @classmethod
    def _plate(cls, value: str) -> str:
        return normalise_plate(value)


class VehicleUpdate(BaseModel):
    office_id: UUID | None = None
    division_id: UUID | None = None
    vehicle_type: VehicleType | None = None
    name: str | None = Field(default=None, min_length=2, max_length=150)
    number_plate: str | None = Field(default=None, min_length=3, max_length=20)
    photo_file_id: UUID | None = None

    @field_validator("number_plate")
    @classmethod
    def _plate(cls, value: str | None) -> str | None:
        return normalise_plate(value) if value else value


class VehicleOut(AssetHolder):
    vehicle_id: UUID
    office_id: UUID
    office_name: str
    division_id: UUID
    division_name: str
    vehicle_type: VehicleType
    name: str
    number_plate: str
    status: AssetStatus
    photo_file_id: UUID | None = None
    stnk_expired_at: date | None = None
    kir_expired_at: date | None = None


class AssetStatusUpdate(BaseModel):
    status: ManualStatus


# ── Berkas & inspeksi kendaraan ───────────────────────────────────────────────
class VehicleFileCreate(BaseModel):
    type: VehicleFileType
    file_id: UUID
    active_at: date | None = None  # default: hari ini (WIB)
    expired_at: date

    @model_validator(mode="after")
    def _period(self) -> VehicleFileCreate:
        if self.active_at and self.expired_at < self.active_at:
            raise ValueError("Tanggal kedaluwarsa tidak boleh sebelum tanggal berlaku.")
        return self


class VehicleFileOut(BaseModel):
    vehicle_file_id: UUID
    vehicle_id: UUID
    type: VehicleFileType
    status: Literal["active", "not_active", "extended"]
    active_at: date
    expired_at: date
    file_id: UUID | None = None
    created_at: datetime


class InspectionCreate(BaseModel):
    type: InspectionType
    file_id: UUID


class InspectionOut(BaseModel):
    vehicle_inspection_id: UUID
    vehicle_id: UUID
    type: InspectionType
    inspector_employee_id: UUID | None = None
    inspector_name: str | None = None
    file_id: UUID | None = None
    created_at: datetime


# ── Peminjaman ────────────────────────────────────────────────────────────────
class LoanCreate(BaseModel):
    """Serah terima aset ke karyawan; `daily_plan_id` mengaitkannya ke jadwal harian tim (opsional)."""

    asset_type: AssetType
    tool_id: UUID | None = None
    vehicle_id: UUID | None = None
    employee_id: UUID
    daily_plan_id: UUID | None = None
    handover_file_id: UUID | None = None

    @model_validator(mode="after")
    def _one_asset(self) -> LoanCreate:
        tool = self.asset_type == "TOOL"
        wanted, other = (self.tool_id, self.vehicle_id) if tool else (self.vehicle_id, self.tool_id)
        if wanted is None or other is not None:
            field = "tool_id" if self.asset_type == "TOOL" else "vehicle_id"
            raise ValueError(f"Isi {field} saja sesuai jenis aset {self.asset_type}.")
        return self


class LoanReturn(BaseModel):
    condition: ReturnCondition = "ready"


class LoanOut(BaseModel):
    assignment_id: UUID
    asset_type: AssetType
    asset_id: UUID
    asset_name: str
    asset_code: str
    employee_id: UUID
    employee_name: str
    daily_plan_id: UUID | None = None
    work_date: date | None = None
    assignment_status: AssetStatus
    loaned_at: datetime
    returned_at: datetime | None = None
    handover_file_id: UUID | None = None
