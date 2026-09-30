"""
Dokumen pribadi karyawan. Tipis (dok 12 §2): izin di sini, aturan & batas organisasi di
services/document_service.py (R-20 — dulu SQL langsung di router tanpa cek organisasi).
"""
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, ensure_same_org, get_db_with_user, require_permission
from app.core.permissions import Permission
from app.repositories.document_repo import DocumentRepo
from app.schemas.document import (
    DocumentListResponse,
    EmployeeDocumentCreate,
    EmployeeDocumentResponse,
    EmployeeDocumentVerify,
)
from app.services.document_service import DocumentService

router = APIRouter(prefix="/employees/{emp_id}/documents", tags=["Employee Documents"])

_viewer = Depends(require_permission(Permission.VIEW_DOCUMENTS))
_uploader = Depends(require_permission(Permission.UPLOAD_DOCUMENTS))
_verifier = Depends(require_permission(Permission.VERIFY_DOCUMENTS))
_db = Depends(get_db_with_user)


def _service(db: AsyncSession) -> DocumentService:
    return DocumentService(DocumentRepo(db))


@router.get("", response_model=DocumentListResponse)
async def get_employee_documents(
    emp_id: UUID, current_user: CurrentUser = _viewer, db: AsyncSession = _db,
) -> DocumentListResponse:
    """Dokumen milik sendiri, atau milik siapa pun di organisasi bagi pengelola dokumen (HR). Lainnya 404."""
    rows = await _service(db).documents_of(current_user.organization_id, current_user.user_id,
                                           current_user.permissions, emp_id)
    items = [EmployeeDocumentResponse(**r._mapping) for r in rows]
    return DocumentListResponse(items=items, total=len(items))


@router.post("", response_model=EmployeeDocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    emp_id: UUID, data: EmployeeDocumentCreate, current_user: CurrentUser = _uploader, db: AsyncSession = _db,
) -> EmployeeDocumentResponse:
    # Berkas lampiran harus milik organisasi ini (V-08) — sebelum menulis apa pun.
    await ensure_same_org(db, current_user.organization_id, files=[data.file_id])
    row = await _service(db).upload(current_user.organization_id, current_user.user_id,
                                    current_user.permissions, emp_id, data)
    return EmployeeDocumentResponse(**row._mapping)


@router.post("/{doc_id}/verify", response_model=EmployeeDocumentResponse)
async def verify_document(
    emp_id: UUID, doc_id: UUID, data: EmployeeDocumentVerify,
    current_user: CurrentUser = _verifier, db: AsyncSession = _db,
) -> EmployeeDocumentResponse:
    row = await _service(db).verify(current_user.organization_id, current_user.user_id, emp_id, doc_id, data)
    return EmployeeDocumentResponse(**row._mapping)
