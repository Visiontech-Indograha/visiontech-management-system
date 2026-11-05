"""
app/modules/documents/controllers/document_controller.py

Controller orkestrasi use case dokumen karyawan.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends

from app.core.security import CurrentUser
from app.modules.documents.dependencies import get_document_service
from app.modules.documents.schemas.document_schema import (
    DocumentListResponse,
    EmployeeDocumentCreate,
    EmployeeDocumentResponse,
    ExpiringDocumentList,
    ExpiringDocumentResponse,
)
from app.modules.documents.services.document_service import DocumentService


class DocumentController:
    """Controller dokumen pribadi karyawan dan pemantauan kedaluwarsa."""

    def __init__(self, document_service: DocumentService = Depends(get_document_service)) -> None:
        self.document_service = document_service

    async def handle_get_employee_documents(self, current_user: CurrentUser, emp_id: UUID) -> DocumentListResponse:
        rows = await self.document_service.documents_of(current_user, emp_id)
        items = [EmployeeDocumentResponse(**r._mapping) for r in rows]
        return DocumentListResponse(items=items, total=len(items))

    async def handle_upload_document(
        self, current_user: CurrentUser, emp_id: UUID, data: EmployeeDocumentCreate
    ) -> EmployeeDocumentResponse:
        row = await self.document_service.upload(current_user, emp_id, data)
        return EmployeeDocumentResponse(**row._mapping)

    async def handle_deactivate_document(
        self, current_user: CurrentUser, emp_id: UUID, doc_id: UUID
    ) -> EmployeeDocumentResponse:
        row = await self.document_service.deactivate(current_user, emp_id, doc_id)
        return EmployeeDocumentResponse(**row._mapping)

    async def handle_delete_document(self, current_user: CurrentUser, emp_id: UUID, doc_id: UUID) -> dict[str, str]:
        await self.document_service.delete(current_user, emp_id, doc_id)
        return {"message": "Dokumen dihapus."}

    async def handle_get_expiring(self, user: CurrentUser, urgency: str | None) -> ExpiringDocumentList:
        rows = await self.document_service.expiring(user, urgency)
        return ExpiringDocumentList(items=[ExpiringDocumentResponse(**r._mapping) for r in rows])

    async def handle_cron_expire(self) -> dict[str, object]:
        return {"expired_count": await self.document_service.expire_overdue()}
