"""
app/modules/employees/schemas/employee_schema.py
Karyawan V2 (Milestone 10): tabel `employee` (kantor, divisi, jabatan, PKWT, foto, wajah, status offboarding) +
`address` (1─N) + akun `users` (1─1, dikelola modul accounts).
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

OffboardingStatus = Literal["active", "in_process", "offboarded"]


class AddressIn(BaseModel):
    address_line: str = Field(min_length=3, max_length=255)
    city: str = Field(min_length=2, max_length=100)
    postal_code: str = Field(min_length=3, max_length=10)


class AddressOut(AddressIn):
    address_id: UUID


class EmployeeOut(BaseModel):
    employee_id: UUID
    employee_no: str
    full_name: str
    office_id: UUID
    office_name: str
    division_id: UUID | None = None
    division_name: str | None = None
    position_id: UUID | None = None
    position_code: str | None = None
    position_name: str | None = None
    join_date: date
    pkwt_end_date: date | None = None
    photo_file_id: UUID | None = None
    face_enrolled: bool = False
    offboarding_status: OffboardingStatus
    archived: bool = False
    user_id: UUID | None = None
    email: str | None = None
    system_role: str | None = None
    account_active: bool | None = None
    city: str | None = None  # kota alamat pertama (daftar)
    create_at: datetime
    update_at: datetime


class EmployeeDetail(EmployeeOut):
    addresses: list[AddressOut] = []


class EmployeeListResponse(BaseModel):
    items: list[EmployeeOut]
    total: int
    page: int = 1
    size: int = 20


class EmployeeCreate(BaseModel):
    employee_no: str = Field(min_length=2, max_length=50)
    full_name: str = Field(min_length=2, max_length=150)
    office_id: UUID
    division_id: UUID | None = None
    position_id: UUID | None = None
    join_date: date
    pkwt_end_date: date | None = None  # kosong = karyawan tetap
    photo_file_id: UUID | None = None
    address: AddressIn | None = None

    @model_validator(mode="after")
    def _dates(self) -> EmployeeCreate:
        if self.pkwt_end_date and self.pkwt_end_date < self.join_date:
            raise ValueError("Akhir PKWT tidak boleh sebelum tanggal bergabung.")
        return self


class EmployeeUpdate(BaseModel):
    """Sebagian; kirim `null` untuk mengosongkan divisi/jabatan/akhir PKWT/foto."""

    employee_no: str | None = Field(None, min_length=2, max_length=50)
    full_name: str | None = Field(None, min_length=2, max_length=150)
    office_id: UUID | None = None
    division_id: UUID | None = None
    position_id: UUID | None = None
    join_date: date | None = None
    pkwt_end_date: date | None = None
    photo_file_id: UUID | None = None


__all__ = [
    "AddressIn",
    "AddressOut",
    "EmployeeCreate",
    "EmployeeDetail",
    "EmployeeListResponse",
    "EmployeeOut",
    "EmployeeUpdate",
    "OffboardingStatus",
]
