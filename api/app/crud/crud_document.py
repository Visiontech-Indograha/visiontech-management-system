"""
app/crud/crud_document.py
Shim re-export untuk kompatibilitas uji lama.
"""
from app.modules.documents.repositories.document_repository import CRUDDocument, DocumentRepository

__all__ = ["CRUDDocument", "DocumentRepository"]
