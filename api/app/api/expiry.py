from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db_with_user, require_permission
from app.core.permissions import Permission

router = APIRouter(prefix="/documents", tags=["Document Expiry"])

class ExpiringDocumentResponse(BaseModel):
    id: UUID
    employee_id: UUID
    full_name: str
    doc_type: str
    expiry_date: date
    days_left: int
    urgency: str

class ExpiringDocumentList(BaseModel):
    items: list[ExpiringDocumentResponse]

@router.get("/expiring", response_model=ExpiringDocumentList)
async def get_expiring_documents(
    urgency: str | None = None,
    current_user: CurrentUser = Depends(require_permission(Permission.VERIFY_DOCUMENTS)),
    db: AsyncSession = Depends(get_db_with_user)
):
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

@router.post("/cron/expire-documents")
async def cron_expire_documents(db: AsyncSession = Depends(get_db_with_user)):
    """
    Dipanggil secara berkala oleh scheduler untuk memperbarui status 'CURRENT' menjadi 'EXPIRED'.
    Dalam praktiknya, endpoint ini harus diproteksi dengan secret key internal.
    """
    query = text("""
        UPDATE vms.employee_document 
        SET lifecycle = 'EXPIRED'
        WHERE lifecycle = 'CURRENT' AND expiry_date < CURRENT_DATE
        RETURNING id
    """)
    res = await db.execute(query)
    updated = res.fetchall()
    return {"expired_count": len(updated)}
