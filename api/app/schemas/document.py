import re
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, field_validator

_SIM = re.compile(r"^SIM\s*(A|C|D|B\s*(?:I{1,2}|1|2)(?:\s*UMUM)?)(\s+UMUM)?$", re.IGNORECASE)
_UPPER = {"KTP", "KK", "NPWP", "MCU", "BPJS"}


def normalise_doc_type(value: str) -> str:
    """Rapikan jenis dokumen: spasi ganda, huruf kapital SIM/KTP/MCU, "SIM B1" → "SIM B I".

    Aturan SIM pengemudi di trigger `tg_vehicle_driver_licence` mencocokkan teks persis
    ('SIM A' / 'SIM C'), jadi ketikan bebas harus diseragamkan di sini.
    """
    text = " ".join(value.split())
    m = _SIM.match(text)
    if m:
        klass = m.group(1).upper().replace(" ", "")
        klass = {"B1": "B I", "BI": "B I", "B2": "B II", "BII": "B II"}.get(
            klass.removesuffix("UMUM"), klass.removesuffix("UMUM")
        )
        umum = "UMUM" in m.group(0).upper()
        return f"SIM {klass}{' UMUM' if umum else ''}"
    if text.upper() in _UPPER:
        return text.upper()
    return text


class EmployeeDocumentCreate(BaseModel):
    doc_type: str
    number: str  # Akan di-mask dan di-hash oleh backend
    expiry_date: date | None = None
    file_id: UUID
    supersedes_id: UUID | None = None

    @field_validator("doc_type")
    @classmethod
    def _doc_type(cls, value: str) -> str:
        text = normalise_doc_type(value)
        if not text:
            raise ValueError("Jenis dokumen wajib diisi.")
        return text

class EmployeeDocumentVerify(BaseModel):
    is_approved: bool
    review_note: str | None = None

class EmployeeDocumentResponse(BaseModel):
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
    items: list[EmployeeDocumentResponse]
    total: int
