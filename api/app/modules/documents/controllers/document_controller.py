"""
app/modules/documents/controllers/document_controller.py

Controller orkestrasi use case dokumen karyawan.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.core.security import CurrentUser
from app.modules.documents.dependencies import get_document_service
from app.modules.documents.schemas.document_schema import (
    DocumentListResponse,
    EmployeeDocumentCreate,
    EmployeeDocumentResponse,
    EmployeeDocumentVerify,
    ExpiringDocumentList,
    ExpiringDocumentResponse,
    PendingDocument,
    PendingDocumentList,
)
from app.modules.documents.services.document_service import DocumentService
from app.shared.access.access_service import ensure_same_org


class DocumentController:
    """
    Controller use case dokumen pribadi karyawan dan antrean verifikasi.
    """

    def __init__(
        self,
        document_service: DocumentService = Depends(get_document_service),
        db: AsyncSession = Depends(get_db_with_user),
    ) -> None:
        self.document_service = document_service
        self.db = db

    async def handle_get_employee_documents(self, current_user: CurrentUser, emp_id: UUID) -> DocumentListResponse:
        """Mengambil daftar dokumen pribadi karyawan sesuai aturan visibilitas."""
        rows = await self.document_service.documents_of(
            current_user.organization_id,
            current_user.user_id,
            current_user.permissions,
            emp_id,
        )
        items = [EmployeeDocumentResponse(**r._mapping) for r in rows]
        return DocumentListResponse(items=items, total=len(items))

    async def handle_upload_document(
        self, current_user: CurrentUser, emp_id: UUID, data: EmployeeDocumentCreate
    ) -> EmployeeDocumentResponse:
        """Mengunggah dokumen baru untuk karyawan setelah validasi kepemilikan file di organisasi."""
        await ensure_same_org(self.db, current_user.organization_id, files=[data.file_id])
        row = await self.document_service.upload(
            current_user.organization_id,
            current_user.user_id,
            current_user.permissions,
            emp_id,
            data,
        )
        return EmployeeDocumentResponse(**row._mapping)

    async def handle_verify_document(
        self,
        current_user: CurrentUser,
        emp_id: UUID,
        doc_id: UUID,
        data: EmployeeDocumentVerify,
    ) -> EmployeeDocumentResponse:
        """Memverifikasi status persetujuan dokumen karyawan."""
        row = await self.document_service.verify(
            current_user.organization_id, current_user.user_id, emp_id, doc_id, data
        )
        return EmployeeDocumentResponse(**row._mapping)

    async def handle_get_expiring(self, current_user: CurrentUser, urgency: str | None) -> ExpiringDocumentList:
        """Mengambil daftar dokumen karyawan yang akan atau sudah kedaluwarsa."""
        rows = await self.document_service.expiring(current_user.organization_id, urgency)
        return ExpiringDocumentList(items=[ExpiringDocumentResponse(**r._mapping) for r in rows])

    async def handle_get_pending(self, current_user: CurrentUser) -> PendingDocumentList:
        """Mengambil antrean verifikasi dokumen yang masih berstatus PENDING."""
        rows = await self.document_service.pending_queue(current_user.organization_id, current_user.user_id)
        return PendingDocumentList(items=[PendingDocument(**r._mapping) for r in rows])

    async def handle_cron_expire(self, current_user: CurrentUser) -> dict[str, object]:
        """Tugas terjadwal untuk memperbarui status dokumen yang lewat masa berlaku menjadi EXPIRED."""
        return {"expired_count": await self.document_service.expire_overdue(current_user.organization_id)}
