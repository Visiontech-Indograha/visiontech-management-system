"""
app/modules/documents/services/document_service.py
Dokumen & sertifikat karyawan (Milestone 3, docs/36): KTP, SIM, sertifikat K3/teknis, kontrak PKWT.

- Karyawan melihat dokumennya sendiri; pengelola dokumen (`manage:employee_documents`, HR/GA &
  SUPER_ADMIN) melihat dan mengelola dokumen semua karyawan. Dokumen orang lain → 404, bukan 403,
  agar keberadaan data tidak dibocorkan.
- Unggah dokumen sejenis yang baru otomatis menggantikan yang berlaku (lama → `extended`).
- Dokumen yang tanggal kedaluwarsanya lewat dinonaktifkan oleh pekerjaan berkala.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.errors import NotFoundError, ValidationError
from app.core.permissions import Permission, SystemRole
from app.core.security import CurrentUser
from app.modules.documents.repositories.document_repository import DocumentRepository
from app.modules.documents.schemas.document_schema import EmployeeDocumentCreate

NOT_FOUND = "Dokumen"
FILE_NOT_OWNED = "Berkas tidak ditemukan atau bukan milik Anda. Unggah ulang berkasnya."


class DocumentService:
    """Use case dokumen pribadi karyawan."""

    def __init__(self, repo: DocumentRepository) -> None:
        self.repo = repo

    async def _reachable(self, user: CurrentUser, emp_id: UUID) -> None:
        if not await self.repo.employee_exists(emp_id):
            raise NotFoundError("Karyawan")
        if Permission.MANAGE_EMPLOYEE_DOCUMENTS.value in user.permissions:
            return
        if await self.repo.employee_of_user(user.user_id) != str(emp_id):
            raise NotFoundError("Karyawan")

    async def documents_of(self, user: CurrentUser, emp_id: UUID) -> list[Any]:
        await self._reachable(user, emp_id)
        return await self.repo.list_for_employee(emp_id)

    async def upload(self, user: CurrentUser, emp_id: UUID, data: EmployeeDocumentCreate) -> Any:
        await self._reachable(user, emp_id)
        path_file = await self.repo.file_key(data.file_id)
        if path_file is None:
            raise ValidationError("Berkas belum diunggah atau sudah dihapus. Unggah ulang berkasnya.")
        await self._owns_file(user, emp_id, data.file_id)
        doc_id = await self.repo.insert(emp_id, data.doc_type, path_file, data.active_at, data.expired_at)
        return await self.repo.get(doc_id, emp_id)

    async def _owns_file(self, user: CurrentUser, emp_id: UUID, file_id: UUID) -> None:
        """Berkas yang dilampirkan harus milik pengunggah yang sah: pengunggah itu sendiri, akun karyawan
        yang bersangkutan, atau SUPER_ADMIN. Berkas milik orang lain ditolak seperti berkas tak dikenal."""
        uploader = await self.repo.file_uploader(file_id)
        if uploader is None:
            raise ValidationError(FILE_NOT_OWNED)
        if uploader == user.user_id or user.has_role(SystemRole.SUPER_ADMIN):
            return
        if uploader != await self.repo.user_of_employee(emp_id):
            raise ValidationError(FILE_NOT_OWNED)

    async def _doc(self, emp_id: UUID, doc_id: UUID) -> Any:
        doc = await self.repo.get(doc_id, emp_id)
        if doc is None:
            raise NotFoundError(NOT_FOUND)
        return doc

    async def deactivate(self, user: CurrentUser, emp_id: UUID, doc_id: UUID) -> Any:
        await self._reachable(user, emp_id)
        await self._doc(emp_id, doc_id)
        await self.repo.deactivate(doc_id)
        return await self.repo.get(doc_id, emp_id)

    async def delete(self, user: CurrentUser, emp_id: UUID, doc_id: UUID) -> None:
        await self._reachable(user, emp_id)
        await self._doc(emp_id, doc_id)
        await self.repo.archive(doc_id)

    async def expiring(self, urgency: str | None) -> list[Any]:
        return await self.repo.expiring(urgency)

    async def expire_overdue(self) -> int:
        return await self.repo.expire_overdue()
