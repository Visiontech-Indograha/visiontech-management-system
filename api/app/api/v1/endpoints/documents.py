"""
Dokumen pribadi karyawan. Tipis (dok 12 §2): izin di sini, aturan & batas organisasi di
services/document_service.py (R-20 — dulu SQL langsung di router tanpa cek organisasi).
"""
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user, get_document_service, require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.schemas.document import (
    DocumentListResponse,
    EmployeeDocumentCreate,
    EmployeeDocumentResponse,
    EmployeeDocumentVerify,
)
from app.services.access_service import ensure_same_org
from app.services.document_service import DocumentService

router = APIRouter(prefix="/employees/{emp_id}/documents", tags=["Employee Documents"])

_viewer = Depends(require_permission(Permission.VIEW_DOCUMENTS))
_uploader = Depends(require_permission(Permission.UPLOAD_DOCUMENTS))
_verifier = Depends(require_permission(Permission.VERIFY_DOCUMENTS))
_db = Depends(get_db_with_user)


@router.get("", response_model=DocumentListResponse)
async def get_employee_documents(
    emp_id: UUID, current_user: CurrentUser = _viewer, document_service: DocumentService = Depends(get_document_service),
) -> DocumentListResponse:
    """
    Mendapatkan daftar dokumen pribadi karyawan.
    Dokumen milik sendiri, atau milik siapa pun di organisasi bagi pengelola dokumen (HR). Lainnya 404.
    
    Path params:
    - emp_id: UUID dari karyawan
    
    Return: Daftar dokumen karyawan (DocumentListResponse)
    """
    # Injeksi dependensi DocumentService dan current_user (_viewer) 
    # Meneruskan query ke service layer untuk mengambil daftar dokumen
    rows = await document_service.documents_of(current_user.organization_id, current_user.user_id,
                                           current_user.permissions, emp_id)
    items = [EmployeeDocumentResponse(**r._mapping) for r in rows]
    return DocumentListResponse(items=items, total=len(items))


@router.post("", response_model=EmployeeDocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    emp_id: UUID, data: EmployeeDocumentCreate, current_user: CurrentUser = _uploader, db: AsyncSession = _db,
                                                                                       document_service: DocumentService = Depends(get_document_service),
) -> EmployeeDocumentResponse:
    """
    Mengunggah (menambahkan) dokumen baru untuk karyawan.
    
    Path params:
    - emp_id: UUID dari karyawan
    
    Body params:
    - data: Data dokumen yang akan dibuat, termasuk referensi file (EmployeeDocumentCreate)
    
    Return: Detail dokumen yang baru saja ditambahkan (EmployeeDocumentResponse)
    """
    # Menggunakan injeksi dependensi sesi DB (_db) dan DocumentService
    # Berkas lampiran harus milik organisasi ini (V-08) — sebelum menulis apa pun.
    await ensure_same_org(db, current_user.organization_id, files=[data.file_id])
    # Memanggil metode upload pada service layer untuk memproses dokumen
    row = await document_service.upload(current_user.organization_id, current_user.user_id,
                                    current_user.permissions, emp_id, data)
    return EmployeeDocumentResponse(**row._mapping)


@router.post("/{doc_id}/verify", response_model=EmployeeDocumentResponse)
async def verify_document(
    emp_id: UUID, doc_id: UUID, data: EmployeeDocumentVerify,
    current_user: CurrentUser = _verifier, document_service: DocumentService = Depends(get_document_service),
) -> EmployeeDocumentResponse:
    """
    Memverifikasi (menyetujui atau menolak) dokumen karyawan.
    
    Path params:
    - emp_id: UUID dari karyawan
    - doc_id: UUID dari dokumen
    
    Body params:
    - data: Hasil verifikasi dokumen (EmployeeDocumentVerify)
    
    Return: Detail dokumen yang telah diverifikasi (EmployeeDocumentResponse)
    """
    # Mengambil instance DocumentService via Depends dan pengguna saat ini (_verifier)
    # Memanggil metode verifikasi pada service layer
    row = await document_service.verify(current_user.organization_id, current_user.user_id, emp_id, doc_id, data)
    return EmployeeDocumentResponse(**row._mapping)
