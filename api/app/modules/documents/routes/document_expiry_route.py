"""
app/modules/documents/routes/document_expiry_route.py

Rute endpoint HTTP untuk kedaluwarsa dan verifikasi antrean dokumen (/documents).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from fastapi import APIRouter, Depends

from app.api.deps import require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.documents.controllers.document_controller import DocumentController
from app.modules.documents.schemas.document_schema import (
    ExpiringDocumentList,
    PendingDocumentList,
)

router = APIRouter(prefix="/documents", tags=["Document Expiry"])


@router.get("/expiring", response_model=ExpiringDocumentList)
async def get_expiring_documents(
    urgency: str | None = None,
    current_user: CurrentUser = Depends(require_permission(Permission.VERIFY_DOCUMENTS)),
    controller: DocumentController = Depends(),
) -> ExpiringDocumentList:
    """Mengambil daftar dokumen yang akan kedaluwarsa atau sudah kedaluwarsa."""
    return await controller.handle_get_expiring(current_user, urgency)


@router.get("/pending", response_model=PendingDocumentList)
async def get_pending_documents(
    current_user: CurrentUser = Depends(require_permission(Permission.VERIFY_DOCUMENTS)),
    controller: DocumentController = Depends(),
) -> PendingDocumentList:
    """Antrean verifikasi HR untuk dokumen pribadi berstatus PENDING."""
    return await controller.handle_get_pending(current_user)


@router.post("/cron/expire-documents")
async def cron_expire_documents(
    current_user: CurrentUser = Depends(require_permission(Permission.RUN_SYSTEM_JOBS)),
    controller: DocumentController = Depends(),
) -> dict[str, object]:
    """Tugas penjadwal untuk menandai dokumen kedaluwarsa menjadi EXPIRED."""
    return await controller.handle_cron_expire(current_user)
