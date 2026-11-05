"""
app/modules/documents/routes/document_expiry_route.py

Rute endpoint HTTP pemantauan kedaluwarsa dokumen karyawan (/documents).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from fastapi import APIRouter, Depends

from app.api.deps import require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.documents.controllers.document_controller import DocumentController
from app.modules.documents.schemas.document_schema import ExpiringDocumentList, Urgency

router = APIRouter(prefix="/documents", tags=["Document Expiry"])


@router.get("/expiring", response_model=ExpiringDocumentList)
async def get_expiring_documents(
    urgency: Urgency | None = None,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_EMPLOYEE_DOCUMENTS)),
    controller: DocumentController = Depends(),
) -> ExpiringDocumentList:
    """Dokumen berlaku yang sudah lewat (EXPIRED), ≤7 hari (CRITICAL), atau ≤30 hari (WARNING)."""
    return await controller.handle_get_expiring(current_user, urgency)


@router.post("/cron/expire-documents")
async def cron_expire_documents(
    current_user: CurrentUser = Depends(require_permission(Permission.RUN_SYSTEM_JOBS)),
    controller: DocumentController = Depends(),
) -> dict[str, object]:
    """Pekerjaan berkala: dokumen yang lewat tanggal kedaluwarsa → not_active."""
    return await controller.handle_cron_expire()
