"""Skema dokumen kendaraan dan pengemudi. Batas input sama dengan yang dipakai web dan mobile."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

DocStatus = Literal["active", "replaced"]


class DocumentTypeOut(BaseModel):
    code: str
    nama: str
    berlaku_untuk: Literal["KENDARAAN", "KARYAWAN"]
    ambang_hari: list[int]
    harian_mulai_hari: int


class VehicleDocumentCreate(BaseModel):
    """Dokumen baru menggantikan dokumen berlaku sejenis pada kendaraan itu (yang lama menjadi `replaced`)."""

    doc_type_code: str = Field(min_length=2, max_length=30, pattern=r"^[A-Z0-9_]+$")
    doc_no: str | None = Field(None, max_length=100)
    issued_on: date | None = None
    expired_on: date
    file_id: UUID | None = None
    catatan: str | None = Field(None, max_length=500)

    @model_validator(mode="after")
    def _urutan_tanggal(self) -> VehicleDocumentCreate:
        if self.issued_on and self.issued_on > self.expired_on:
            raise ValueError("Tanggal terbit tidak boleh setelah tanggal jatuh tempo.")
        return self


class VehicleDocumentOut(BaseModel):
    vehicle_document_id: UUID
    vehicle_id: UUID
    vehicle_name: str
    number_plate: str
    office_id: UUID
    doc_type_code: str
    doc_type_name: str
    doc_no: str | None
    issued_on: date | None
    expired_on: date
    file_id: UUID | None
    status: DocStatus
    catatan: str | None
    days_left: int  # negatif = sudah lewat tempo
    created_at: datetime


class VehicleDriverCreate(BaseModel):
    employee_id: UUID


class VehicleDriverOut(BaseModel):
    vehicle_driver_id: UUID
    vehicle_id: UUID
    employee_id: UUID
    employee_name: str
    mulai_on: date
    selesai_on: date | None
