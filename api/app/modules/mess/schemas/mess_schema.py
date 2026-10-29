"""
app/modules/mess/schemas/mess_schema.py
Skema data Pydantic untuk Mess Karyawan (company_mess, company_mess_stay).
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class MessPlaceIn(BaseModel):
    mess_name: str = Field(..., min_length=2, max_length=150)
    city: str = Field(..., min_length=2, max_length=100)
    address: str = Field(min_length=5, max_length=500)
    latitude: Decimal | None = Field(None, ge=-90, le=90)
    longitude: Decimal | None = Field(None, ge=-180, le=180)
    capacity: int | None = Field(None, ge=1, le=1000, description="Jumlah penghuni maksimum; kosong = tak dibatasi")


class MessPlaceUpdate(BaseModel):
    mess_name: str | None = Field(None, min_length=2, max_length=150)
    city: str | None = Field(None, min_length=2, max_length=100)
    address: str | None = Field(None, min_length=5, max_length=500)
    latitude: Decimal | None = Field(None, ge=-90, le=90)
    longitude: Decimal | None = Field(None, ge=-180, le=180)
    capacity: int | None = Field(None, ge=1, le=1000)


class MessPlaceOut(BaseModel):
    mess_id: UUID
    mess_name: str
    city: str
    address: str
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    capacity: int | None = None
    occupied: int = 0


class MessStayCreate(BaseModel):
    """Pencatatan langsung oleh HR/GA: karyawan + mess dari master, langsung disetujui."""

    employee_id: UUID
    mess_id: UUID
    stay_start_date: date
    stay_end_date: date
    team_id: UUID | None = None  # tim yang menginap (dinas luar kota), opsional


class MessStayRequest(BaseModel):
    """Pengajuan hunian oleh karyawan sendiri; diputus PM/OM/HR."""

    mess_id: UUID
    stay_start_date: date
    stay_end_date: date
    note: str | None = Field(None, max_length=500)
    team_id: UUID | None = None  # tim yang menginap, opsional


class MessDecision(BaseModel):
    approve: bool
    note: str | None = Field(None, max_length=500)


class MessStayUpdate(BaseModel):
    stay_start_date: date | None = None
    stay_end_date: date | None = None


class MessStayOut(BaseModel):
    mess_stay_id: UUID
    mess_id: UUID | None = None
    mess_name: str
    city: str
    address: str
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    employee_id: UUID
    employee_name: str | None = None
    employee_photo_file_id: UUID | None = None
    employee_no: str | None = None
    stay_start_date: date
    stay_end_date: date
    status: str = "APPROVED"
    request_note: str | None = None
    decision_note: str | None = None
    decided_at: datetime | None = None
    create_at: datetime
