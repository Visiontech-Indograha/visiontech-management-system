"""
app/modules/documents/dependencies.py

Perakitan service modul documents untuk FastAPI `Depends` (dipindah dari api/deps.py).
Getter memakai dependency sesi yang SAMA dengan handler sehingga satu permintaan = satu transaksi.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.documents.repositories.document_repository import DocumentRepository
from app.modules.documents.services.document_service import DocumentService


def get_document_service(db: AsyncSession = Depends(get_db_with_user)) -> DocumentService:
    return DocumentService(DocumentRepository(db))
