"""
app/modules/documents/schemas/document_schema.py

Skema validasi permintaan dan respons dokumen karyawan.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.4.
"""
from app.schemas.document import (
    DocumentListResponse,
    EmployeeDocumentCreate,
    EmployeeDocumentResponse,
    EmployeeDocumentVerify,
    ExpiringDocumentList,
    ExpiringDocumentResponse,
    PendingDocument,
    PendingDocumentList,
    normalise_doc_type,
)

__all__ = [
    "DocumentListResponse",
    "EmployeeDocumentCreate",
    "EmployeeDocumentResponse",
    "EmployeeDocumentVerify",
    "ExpiringDocumentList",
    "ExpiringDocumentResponse",
    "PendingDocument",
    "PendingDocumentList",
    "normalise_doc_type",
]
