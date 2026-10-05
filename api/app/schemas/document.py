"""
app/schemas/document.py

Schemas for employee documents, validations, and expirations.
"""
import re
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, field_validator

# Reguler ekspresi untuk mencocokkan berbagai format SIM
_SIM = re.compile(r"^SIM\s*(A|C|D|B\s*(?:I{1,2}|1|2)(?:\s*UMUM)?)(\s+UMUM)?$", re.IGNORECASE)
_UPPER = {"KTP", "KK", "NPWP", "MCU", "BPJS"}


def normalise_doc_type(value: str) -> str:
    """
    Normalize document types, specifically for driver's licenses (SIM) and identity cards.
    
    Rapikan jenis dokumen: atasi spasi ganda, ubah menjadi huruf kapital untuk 
    SIM/KTP/MCU, dan standarisasi penamaan seperti "SIM B1" menjadi "SIM B I".
    
    Aturan SIM pengemudi dalam trigger `tg_vehicle_driver_licence` akan 
    mencocokkan teks secara persis ('SIM A' / 'SIM C'), oleh karena itu teks 
    bebas yang diketik harus diseragamkan di fungsi ini.
    """
    # Menggabungkan spasi ganda menjadi tunggal
    text = " ".join(value.split())
    m = _SIM.match(text)
    if m:
        # Standarisasi tipe SIM dan penghapusan kata UMUM ekstra
        klass = m.group(1).upper().replace(" ", "")
        klass = {"B1": "B I", "BI": "B I", "B2": "B II", "BII": "B II"}.get(
            klass.removesuffix("UMUM"), klass.removesuffix("UMUM")
        )
        umum = "UMUM" in m.group(0).upper()
        # Mengembalikan string SIM yang sudah distandarisasi
        return f"SIM {klass}{' UMUM' if umum else ''}"
    if text.upper() in _UPPER:
        return text.upper()
    return text


class EmployeeDocumentCreate(BaseModel):
    """
    Schema for creating or uploading a new employee document.
    """
    doc_type: str
    # Nomor ini akan dimasker dan di-hash oleh backend
    number: str
    expiry_date: date | None = None
    file_id: UUID
    supersedes_id: UUID | None = None

    @field_validator("doc_type")
    @classmethod
    def _doc_type(cls, value: str) -> str:
        # Normalisasi tipe dokumen sebelum disimpan
        text = normalise_doc_type(value)
        if not text:
            raise ValueError("Jenis dokumen wajib diisi.")
        return text


class EmployeeDocumentVerify(BaseModel):
    """
    Schema for verifying an uploaded employee document.
    """
    is_approved: bool
    review_note: str | None = None


class EmployeeDocumentResponse(BaseModel):
    """
    Schema detailing an employee document's properties.
    """
    id: UUID
    employee_id: UUID
    doc_type: str
    number_masked: str
    expiry_date: date | None
    status: str
    lifecycle: str
    file_id: UUID
    uploaded_by: UUID
    verified_by: UUID | None = None
    verified_at: datetime | None = None
    review_note: str | None = None
    created_at: datetime
    

class DocumentListResponse(BaseModel):
    """
    Schema for a list of employee documents.
    """
    items: list[EmployeeDocumentResponse]
    total: int


# ── Dipindah dari api/v1/endpoints/expiry.py (R-28 M2b) ──
class ExpiringDocumentResponse(BaseModel):
    """
    Schema for a document that is approaching its expiry date.
    """
    id: UUID
    employee_id: UUID
    full_name: str
    doc_type: str
    expiry_date: date
    days_left: int
    urgency: str


class ExpiringDocumentList(BaseModel):
    """
    Schema for a list of expiring documents.
    """
    items: list[ExpiringDocumentResponse]


class PendingDocument(BaseModel):
    """
    Schema for a document pending review.
    """
    id: UUID
    employee_id: UUID
    full_name: str
    doc_type: str
    number_masked: str | None
    expiry_date: date | None
    file_id: UUID | None
    uploaded_at: datetime
    uploaded_by_me: bool


class PendingDocumentList(BaseModel):
    """
    Schema for a list of pending documents.
    """
    items: list[PendingDocument]
