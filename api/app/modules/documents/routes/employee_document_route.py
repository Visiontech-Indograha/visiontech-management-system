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
)

router = APIRouter(prefix="/employees/{emp_id}/documents", tags=["Employee Documents"])
_MANAGE = Depends(require_permission(Permission.MANAGE_EMPLOYEE_DOCUMENTS))


@router.get("", response_model=DocumentListResponse)
async def get_employee_documents(
    emp_id: UUID,
    current_user: CurrentUser = Depends(require_permission(Permission.VIEW_DOCUMENTS)),
    controller: DocumentController = Depends(),
) -> DocumentListResponse:
    """Daftar dokumen karyawan (milik sendiri, atau semua bagi pengelola dokumen)."""
    return await controller.handle_get_employee_documents(current_user, emp_id)


@router.post("", response_model=EmployeeDocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    emp_id: UUID,
    data: EmployeeDocumentCreate,
    current_user: CurrentUser = _MANAGE,
    controller: DocumentController = Depends(),
) -> EmployeeDocumentResponse:
    """Mencatat dokumen baru dari berkas yang sudah diunggah; dokumen sejenis yang lama menjadi `extended`."""
    return await controller.handle_upload_document(current_user, emp_id, data)


@router.post("/{doc_id}/deactivate", response_model=EmployeeDocumentResponse)
async def deactivate_document(
    emp_id: UUID,
    doc_id: UUID,
    current_user: CurrentUser = _MANAGE,
    controller: DocumentController = Depends(),
) -> EmployeeDocumentResponse:
    """Menonaktifkan dokumen (mis. dicabut atau tidak lagi berlaku)."""
    return await controller.handle_deactivate_document(current_user, emp_id, doc_id)


@router.delete("/{doc_id}")
async def delete_document(
    emp_id: UUID,
    doc_id: UUID,
    current_user: CurrentUser = _MANAGE,
    controller: DocumentController = Depends(),
) -> dict[str, str]:
    """Menghapus (soft delete) dokumen yang salah unggah."""
    return await controller.handle_delete_document(current_user, emp_id, doc_id)
