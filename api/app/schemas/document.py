from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from uuid import UUID

class EmployeeDocumentCreate(BaseModel):
    doc_type: str
    number: str  # Akan di-mask dan di-hash oleh backend
    expiry_date: Optional[date] = None
    file_id: UUID
    supersedes_id: Optional[UUID] = None

class EmployeeDocumentVerify(BaseModel):
    is_approved: bool
    review_note: Optional[str] = None

class EmployeeDocumentResponse(BaseModel):
    id: UUID
    employee_id: UUID
    doc_type: str
    number_masked: str
    expiry_date: Optional[date]
    status: str
    lifecycle: str
    file_id: UUID
    uploaded_by: UUID
    verified_by: Optional[UUID] = None
    verified_at: Optional[datetime] = None
    review_note: Optional[str] = None
    created_at: datetime
    
class DocumentListResponse(BaseModel):
    items: List[EmployeeDocumentResponse]
    total: int
