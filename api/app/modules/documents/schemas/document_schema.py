"""
app/modules/documents/schemas/document_schema.py
Skema dokumen & sertifikat karyawan (tabel employee_file, Master Schema V2).

`type` disimpan sebagai kode baku huruf besar bergaris bawah, sama dengan seed V2:
KTP, SIM_A, SIM_B1, SIM_C, SERTIFIKAT_K3, SERTIFIKAT_TEKNIS, KONTRAK_PKWT, …
"""
import re
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

_SIM = re.compile(r"^SIM_?(A|B_?(?:I{1,2}|1|2)|C|D)(_UMUM)?$")
_SIM_CLASS = {"BI": "B1", "BII": "B2", "B_I": "B1", "B_II": "B2", "B_1": "B1", "B_2": "B2"}
_CODE = re.compile(r"^[A-Z0-9_]{2,50}$")


def normalise_doc_type(value: str) -> str:
    """Ketikan bebas → kode baku: "sim a" → SIM_A, "SIM B II" → SIM_B2, "Sertifikat K3" → SERTIFIKAT_K3."""
    code = re.sub(r"[\s\-]+", "_", value.strip().upper())
    m = _SIM.match(code)
    if m:
        klass = _SIM_CLASS.get(m.group(1), m.group(1))
        return f"SIM_{klass}{m.group(2) or ''}"
    return code


DocStatus = Literal["active", "not_active", "extended"]
Urgency = Literal["EXPIRED", "CRITICAL", "WARNING"]


class EmployeeDocumentCreate(BaseModel):
    """Unggah dokumen: berkas diunggah dulu ke /files, lalu dirujuk lewat `file_id`."""

    doc_type: str = Field(max_length=50)
    file_id: UUID
    active_at: date | None = None  # default: hari ini (WIB)
    expired_at: date | None = None

    @field_validator("doc_type")
    @classmethod
    def _doc_type(cls, value: str) -> str:
        code = normalise_doc_type(value)
        if not _CODE.match(code):
            raise ValueError("Jenis dokumen wajib diisi (huruf/angka, 2–50 karakter).")
        return code

    @model_validator(mode="after")
    def _period(self) -> "EmployeeDocumentCreate":
        if self.active_at and self.expired_at and self.expired_at < self.active_at:
            raise ValueError("Tanggal kedaluwarsa tidak boleh sebelum tanggal berlaku.")
        return self


class EmployeeDocumentResponse(BaseModel):
    id: UUID
    employee_id: UUID
    doc_type: str
    status: DocStatus
    active_at: date
    expired_at: date | None = None
    file_id: UUID | None = None  # file_object yang menyimpan berkasnya (path_file = storage_key)
    created_at: datetime


class DocumentListResponse(BaseModel):
    items: list[EmployeeDocumentResponse]
    total: int


class ExpiringDocumentResponse(BaseModel):
    id: UUID
    employee_id: UUID
    full_name: str
    doc_type: str
    expiry_date: date
    days_left: int
    urgency: Urgency


class ExpiringDocumentList(BaseModel):
    items: list[ExpiringDocumentResponse]
