import hashlib
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db_with_user, require_permission
from app.core.permissions import Permission
from app.schemas.document import (
    DocumentListResponse,
    EmployeeDocumentCreate,
    EmployeeDocumentResponse,
    EmployeeDocumentVerify,
)

router = APIRouter(prefix="/employees/{emp_id}/documents", tags=["Employee Documents"])

def mask_number(number: str) -> str:
    """Mengubah nomor dokumen menjadi tersamar (Misal: 1234567890 -> ******7890)"""
    if len(number) <= 4:
        return "*" * len(number)
    return "*" * (len(number) - 4) + number[-4:]

@router.get("", response_model=DocumentListResponse)
async def get_employee_documents(
    emp_id: UUID,
    current_user: CurrentUser = Depends(require_permission(Permission.VIEW_DOCUMENTS)),
    db: AsyncSession = Depends(get_db_with_user)
):
    # Dapatkan employee_id dari user yang sedang login
    user_emp = text("SELECT employee_id FROM vms.app_user WHERE id = :uid")
    my_emp_id = (await db.execute(user_emp, {"uid": current_user.user_id})).scalar()
    
    if Permission.MANAGE_EMPLOYEE_DOCUMENTS.value not in current_user.permissions and my_emp_id != emp_id:
        # DoD: "pengguna lain tidak bisa melihat dokumen pribadi orang lain (404, bukan 403)"
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan.")
        
    query = text("""
        SELECT id, employee_id, doc_type, number_masked, expiry_date, 
               status, lifecycle, file_id, uploaded_by, verified_by, 
               verified_at, review_note, created_at
        FROM vms.employee_document
        WHERE employee_id = :emp_id
        ORDER BY created_at DESC
    """)
    rows = (await db.execute(query, {"emp_id": emp_id})).fetchall()
    
    items = []
    for row in rows:
        items.append(EmployeeDocumentResponse(**row._mapping))
        
    return DocumentListResponse(items=items, total=len(items))

@router.post("", response_model=EmployeeDocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    emp_id: UUID,
    data: EmployeeDocumentCreate,
    current_user: CurrentUser = Depends(require_permission(Permission.UPLOAD_DOCUMENTS)),
    db: AsyncSession = Depends(get_db_with_user)
):
    # Dapatkan employee_id dari user yang login
    user_emp = text("SELECT employee_id FROM vms.app_user WHERE id = :uid")
    my_emp_id = (await db.execute(user_emp, {"uid": current_user.user_id})).scalar()
    
    if Permission.MANAGE_EMPLOYEE_DOCUMENTS.value not in current_user.permissions and my_emp_id != emp_id:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan.")
        
    # Masking dan hashing
    number_masked = mask_number(data.number)
    number_sha256 = hashlib.sha256(data.number.encode('utf-8')).digest()
    
    insert_query = text("""
        INSERT INTO vms.employee_document (
            employee_id, doc_type, number_masked, number_sha256, 
            expiry_date, file_id, uploaded_by, supersedes_id
        ) VALUES (
            :emp_id, :type, :masked, :hash, :expiry, :fid, :uid, :super_id
        ) RETURNING *
    """)
    try:
        res = await db.execute(insert_query, {
            "emp_id": emp_id, "type": data.doc_type,
            "masked": number_masked, "hash": number_sha256,
            "expiry": data.expiry_date, "fid": data.file_id,
            "uid": current_user.user_id, "super_id": data.supersedes_id
        })
        row = res.fetchone()
        return EmployeeDocumentResponse(**row._mapping)
    except Exception as e:
        raise HTTPException(status_code=400, detail={"code": "DB_ERROR", "message": str(e)})

@router.post("/{doc_id}/verify", response_model=EmployeeDocumentResponse)
async def verify_document(
    emp_id: UUID,
    doc_id: UUID,
    data: EmployeeDocumentVerify,
    current_user: CurrentUser = Depends(require_permission(Permission.VERIFY_DOCUMENTS)),
    db: AsyncSession = Depends(get_db_with_user)
):
    status_val = "VERIFIED" if data.is_approved else "REJECTED"
    lifecycle_val = "CURRENT" if data.is_approved else "PENDING"
    
    verify_query = text("""
        UPDATE vms.employee_document 
        SET status = :status, lifecycle = :lifecycle, 
            verified_by = :uid, verified_at = now(), review_note = :note
        WHERE id = :doc_id AND employee_id = :emp_id
        RETURNING *
    """)
    res = await db.execute(verify_query, {
        "status": status_val, "lifecycle": lifecycle_val,
        "uid": current_user.user_id, "note": data.review_note,
        "doc_id": doc_id, "emp_id": emp_id
    })
    row = res.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan.")
        
    return EmployeeDocumentResponse(**row._mapping)
