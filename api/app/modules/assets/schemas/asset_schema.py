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
    team_id: UUID | None = None  # tim pemakai bawaan (opsional)
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
    team_id: UUID | None = None
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
    holder_external_borrower_id: UUID | None = None
    holder_name: str | None = None
    daily_plan_id: UUID | None = None


class ToolOut(AssetHolder):
    tool_id: UUID
    team_id: UUID | None = None  # tim pemakai bawaan
    team_name: str | None = None
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
    team_id: UUID | None = None  # tim pemakai bawaan (opsional)
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
    team_id: UUID | None = None
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
    team_id: UUID | None = None  # tim pemakai bawaan
    team_name: str | None = None
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
    employee_id: UUID | None = None
    external_borrower_id: UUID | None = None
    due_date: date | None = None
    bast_file_id: UUID | None = None
    daily_plan_id: UUID | None = None
    handover_file_id: UUID | None = None

    @model_validator(mode="after")
    def _one_borrower(self) -> LoanCreate:
        if (self.employee_id is None) == (self.external_borrower_id is None):
            raise ValueError("Pilih satu penerima saja: karyawan atau penerima eksternal.")
        if self.external_borrower_id is not None and self.daily_plan_id is not None:
            raise ValueError("Peminjaman ke penerima eksternal tidak dikaitkan ke jadwal harian.")
        return self

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
    employee_id: UUID | None = None
    employee_name: str
    employee_photo_file_id: UUID | None = None
    external_borrower_id: UUID | None = None
    borrower_name: str | None = None
    borrower_instansi: str | None = None
    due_date: date | None = None
    bast_file_id: UUID | None = None
    daily_plan_id: UUID | None = None
    work_date: date | None = None
    assignment_status: AssetStatus
    loaned_at: datetime
    returned_at: datetime | None = None
    handover_file_id: UUID | None = None
    return_requested_at: datetime | None = None
    return_condition: ReturnCondition | None = None
    return_note: str | None = None
    return_file_id: UUID | None = None


class LoanRequestCreate(BaseModel):
    """Karyawan mengajukan pinjam aset; employee_id selalu diambil dari akun yang login."""

    asset_type: AssetType
    tool_id: UUID | None = None
    vehicle_id: UUID | None = None
    purpose: str = Field(min_length=3, max_length=1000)
    needed_on: date | None = None

    @model_validator(mode="after")
    def _one_asset(self) -> LoanRequestCreate:
        tool = self.asset_type == "TOOL"
        wanted, other = (self.tool_id, self.vehicle_id) if tool else (self.vehicle_id, self.tool_id)
        if wanted is None or other is not None:
            field = "tool_id" if tool else "vehicle_id"
            raise ValueError(f"Isi {field} saja sesuai jenis aset {self.asset_type}.")
        return self


class LoanRequestReview(BaseModel):
    decision: Literal["APPROVED", "REJECTED"]
    note: str | None = Field(default=None, max_length=1000)


class LoanReturnRequest(BaseModel):
    """Pengajuan pengembalian oleh pemegang aset: kondisi, catatan, dan foto kondisi."""

    condition: ReturnCondition = "ready"
    note: str | None = Field(default=None, max_length=1000)
    photo_file_id: UUID


LoanRequestStatus = Literal["PENDING", "APPROVED", "REJECTED", "CANCELLED"]


class LoanRequestOut(BaseModel):
    request_id: UUID
    asset_type: AssetType
    asset_id: UUID
    asset_name: str
    asset_code: str
    employee_id: UUID
    employee_name: str
    employee_photo_file_id: UUID | None = None
    purpose: str
    needed_on: date | None = None
    status: LoanRequestStatus
    review_note: str | None = None
    reviewed_at: datetime | None = None
    assignment_id: UUID | None = None
    create_at: datetime


class AssetAvailabilityOut(BaseModel):
    """Ketersediaan satu alat/kendaraan pada satu tanggal jadwal."""
    asset_type: Literal["TOOL", "VEHICLE"]
    asset_id: UUID
    asset_name: str
    status: AssetStatus
    available: bool  # True bila tidak dipakai tim lain pada tanggal itu dan kondisinya siap
    used_by_team_id: UUID | None = None  # Tim pemakai pada tanggal itu (None = tidak dipakai)
    used_by_team_name: str | None = None
    used_by_requested_team: bool = False  # Dipakai oleh tim yang diminta (query team_id)


# ── Penerima eksternal (ADR 0003) ─────────────────────────────────────────────
class BorrowerCreate(BaseModel):
    """Penerima eksternal (klien sewa, subkontraktor). Data seminimal mungkin: tanpa NIK/alamat."""

    office_id: UUID
    nama: str = Field(min_length=1, max_length=150)
    instansi: str | None = Field(None, max_length=150)
    kontak: str | None = Field(None, max_length=100)

    @field_validator("nama", "instansi", "kontak")
    @classmethod
    def _trim(cls, value: str | None) -> str | None:
        text = " ".join(value.split()) if value else None
        return text or None

    @field_validator("nama")
    @classmethod
    def _nama_required(cls, value: str | None) -> str | None:
        if not value:
            raise ValueError("Nama penerima wajib diisi.")
        return value


class BorrowerUpdate(BaseModel):
    nama: str | None = Field(None, min_length=1, max_length=150)
    instansi: str | None = Field(None, max_length=150)
    kontak: str | None = Field(None, max_length=100)

    @field_validator("nama", "instansi", "kontak")
    @classmethod
    def _trim(cls, value: str | None) -> str | None:
        return " ".join(value.split()) if value else value


class BorrowerOut(BaseModel):
    borrower_id: UUID
    office_id: UUID
    office_name: str
    nama: str
    instansi: str | None = None
    kontak: str | None = None
    has_open_loan: bool = False
    create_at: datetime
