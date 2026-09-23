from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class EmployeeDocumentCreate(BaseModel):
    doc_type: str
    number: str  # Akan di-mask dan di-hash oleh backend
    expiry_date: date | None = None
    file_id: UUID
    supersedes_id: UUID | None = None

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
