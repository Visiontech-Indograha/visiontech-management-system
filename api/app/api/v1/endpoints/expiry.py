
from fastapi import APIRouter, Depends

from app.api.deps import get_document_service, require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.schemas.document import (
    ExpiringDocumentList,
    ExpiringDocumentResponse,
    PendingDocument,
    PendingDocumentList,
)
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["Document Expiry"])



@router.get("/expiring", response_model=ExpiringDocumentList)
async def get_expiring_documents(
    urgency: str | None = None,
    current_user: CurrentUser = Depends(require_permission(Permission.VERIFY_DOCUMENTS)),
    document_service: DocumentService = Depends(get_document_service),
) -> ExpiringDocumentList:
    """
    Mengambil daftar dokumen yang akan kedaluwarsa atau sudah kedaluwarsa.
    Memerlukan izin VERIFY_DOCUMENTS (biasanya HR).

    Query params:
    - urgency: Opsi pemfilteran berdasarkan tingkat urgensi

    Return: Daftar dokumen yang memasuki masa kedaluwarsa (ExpiringDocumentList)
    """
    rows = await document_service.expiring(current_user.organization_id, urgency)
    return ExpiringDocumentList(items=[ExpiringDocumentResponse(**r._mapping) for r in rows])





@router.get("/pending", response_model=PendingDocumentList)
async def get_pending_documents(
    current_user: CurrentUser = Depends(require_permission(Permission.VERIFY_DOCUMENTS)),
    document_service: DocumentService = Depends(get_document_service),
) -> PendingDocumentList:
    """
    Antrean verifikasi HR (P2-5): dokumen pribadi berstatus PENDING di organisasi ini, terlama dulu.

    Return: Daftar dokumen yang perlu diverifikasi (PendingDocumentList)
    """
    # Memerlukan DocumentService lewat injeksi dependensi
    # Melakukan pemanggilan service queue pending
    rows = await document_service.pending_queue(current_user.organization_id,
                                                                current_user.user_id)
    return PendingDocumentList(items=[PendingDocument(**r._mapping) for r in rows])


@router.post("/cron/expire-documents")
async def cron_expire_documents(
    current_user: CurrentUser = Depends(require_permission(Permission.RUN_SYSTEM_JOBS)),
    document_service: DocumentService = Depends(get_document_service),
) -> dict[str, object]:
    """
    Dipanggil berkala oleh penjadwal: dokumen 'CURRENT' yang lewat masa berlaku → 'EXPIRED'.
    Hanya ADMIN (`run:system_jobs`, sama dengan cron absensi) dan hanya untuk organisasinya (V-09);
    "hari ini" menurut zona waktu organisasi, bukan jam server DB.

    Return: Jumlah dokumen yang diubah (dict)
    """
    return {"expired_count": await document_service.expire_overdue(current_user.organization_id)}
