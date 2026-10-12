"""
app/modules/documents/routes/employee_document_route.py

Rute endpoint HTTP untuk dokumen pribadi karyawan (/employees/{emp_id}/documents).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.documents.controllers.document_controller import DocumentController
from app.modules.documents.schemas.document_schema import (
    DocumentListResponse,
    EmployeeDocumentCreate,
    EmployeeDocumentResponse,
    EmployeeDocumentVerify,
)

router = APIRouter(prefix="/employees/{emp_id}/documents", tags=["Employee Documents"])


@router.get("", response_model=DocumentListResponse)
async def get_employee_documents(
    emp_id: UUID,
    current_user: CurrentUser = Depends(require_permission(Permission.VIEW_DOCUMENTS)),
    controller: DocumentController = Depends(),
) -> DocumentListResponse:
    """Mendapatkan daftar dokumen pribadi karyawan."""
    return await controller.handle_get_employee_documents(current_user, emp_id)


@router.post("", response_model=EmployeeDocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    emp_id: UUID,
    data: EmployeeDocumentCreate,
    current_user: CurrentUser = Depends(require_permission(Permission.UPLOAD_DOCUMENTS)),
    controller: DocumentController = Depends(),
) -> EmployeeDocumentResponse:
    """Mengunggah dokumen baru untuk karyawan."""
    return await controller.handle_upload_document(current_user, emp_id, data)


@router.post("/{doc_id}/verify", response_model=EmployeeDocumentResponse)
async def verify_document(
    emp_id: UUID,
    doc_id: UUID,
    data: EmployeeDocumentVerify,
    current_user: CurrentUser = Depends(require_permission(Permission.VERIFY_DOCUMENTS)),
    controller: DocumentController = Depends(),
) -> EmployeeDocumentResponse:
    """Memverifikasi (menyetujui atau menolak) dokumen karyawan."""
    return await controller.handle_verify_document(current_user, emp_id, doc_id, data)
