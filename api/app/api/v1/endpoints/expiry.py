
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db_with_user, require_permission
from app.core.permissions import Permission
from app.crud.crud_document import CRUDDocument
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
    db: AsyncSession = Depends(get_db_with_user)
) -> ExpiringDocumentList:
    """
    Mengambil daftar dokumen yang akan kedaluwarsa atau sudah kedaluwarsa.
    Memerlukan izin VERIFY_DOCUMENTS (biasanya HR).
    """
    where_clauses = ["organization_id = :org"]
    params = {"org": current_user.organization_id}
    
    if urgency:
        where_clauses.append("urgency = :urgency")
        params["urgency"] = urgency
        
    where_str = " AND ".join(where_clauses)
    
    query = text(f"""
        SELECT id, employee_id, full_name, doc_type, expiry_date, days_left, urgency
        FROM vms.v_document_expiry
        WHERE {where_str}
        ORDER BY days_left ASC
    """)
    
    rows = (await db.execute(query, params)).fetchall()
    
    items = []
    for row in rows:
        items.append(ExpiringDocumentResponse(**row._mapping))
        
    return ExpiringDocumentList(items=items)





@router.get("/pending", response_model=PendingDocumentList)
async def get_pending_documents(
    current_user: CurrentUser = Depends(require_permission(Permission.VERIFY_DOCUMENTS)),
    db: AsyncSession = Depends(get_db_with_user),
) -> PendingDocumentList:
    """Antrean verifikasi HR (P2-5): dokumen pribadi berstatus PENDING di organisasi ini, terlama dulu."""
    rows = await DocumentService(CRUDDocument(db)).pending_queue(current_user.organization_id,
                                                                current_user.user_id)
    return PendingDocumentList(items=[PendingDocument(**r._mapping) for r in rows])


@router.post("/cron/expire-documents")
async def cron_expire_documents(
    current_user: CurrentUser = Depends(require_permission(Permission.RUN_SYSTEM_JOBS)),
    db: AsyncSession = Depends(get_db_with_user),
) -> dict[str, object]:
    """
    Dipanggil berkala oleh penjadwal: dokumen 'CURRENT' yang lewat masa berlaku → 'EXPIRED'.
    Hanya ADMIN (`run:system_jobs`, sama dengan cron absensi) dan hanya untuk organisasinya (V-09);
    "hari ini" menurut zona waktu organisasi, bukan jam server DB.
    """
    query = text("""
        UPDATE vms.employee_document d
        SET lifecycle = 'EXPIRED'
        FROM vms.employee e
        JOIN vms.organization o ON o.id = e.organization_id
        WHERE d.employee_id = e.id AND e.organization_id = CAST(:org AS uuid)
          AND d.lifecycle = 'CURRENT' AND d.expiry_date < (now() AT TIME ZONE o.timezone)::date
        RETURNING d.id
    """)
    res = await db.execute(query, {"org": current_user.organization_id})
    updated = res.fetchall()
    return {"expired_count": len(updated)}
