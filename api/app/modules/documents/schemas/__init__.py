"""
Paket skema untuk modul documents.
"""
from app.modules.documents.schemas.document_schema import (
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
