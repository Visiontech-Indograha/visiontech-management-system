"""
app/services/document_service.py
Dokumen pribadi — daftar, pengajuan (UPLOAD_DOCUMENT), verifikasi (VERIFY_DOCUMENT) dan antrean HR.
Izin (view/upload/verify:documents) dijaga router; aturan & batas organisasi di sini (R-20).
"""
from __future__ import annotations

import hashlib
from typing import Any

from app.core.errors import AppError, NotFoundError
from app.core.permissions import Permission
from app.crud.crud_document import CRUDDocument
from app.schemas.document import EmployeeDocumentCreate, EmployeeDocumentVerify

NOT_FOUND = "Dokumen"


def mask_number(number: str) -> str:
    """Nomor dokumen tersamar (1234567890 → ******7890); nomor penuh tidak pernah disimpan."""
    if len(number) <= 4:
        return "*" * len(number)
    return "*" * (len(number) - 4) + number[-4:]


class DocumentService:
    def __init__(self, repo: CRUDDocument) -> None:
        self.repo = repo

    async def pending_queue(self, org_id: str, user_id: str) -> list[Any]:
        """Dokumen menunggu verifikasi. `uploaded_by_me` → harus diperiksa petugas lain (empat mata)."""
        return await self.repo.pending_for_org(org_id, user_id)

    async def _reachable(self, org_id: str, user_id: str, permissions: list[str], emp_id: Any) -> None:
        """Dokumen orang lain hanya untuk pengelola dokumen, dan hanya di organisasinya (V-08).
        Selain itu 404, bukan 403 — keberadaan data orang lain tidak dibocorkan."""
        if not await self.repo.employee_in_org(emp_id, org_id):
            raise NotFoundError(NOT_FOUND)
        if Permission.MANAGE_EMPLOYEE_DOCUMENTS.value in permissions:
            return
        if str(await self.repo.employee_of_user(user_id)) != str(emp_id):
            raise NotFoundError(NOT_FOUND)

    async def documents_of(self, org_id: str, user_id: str, permissions: list[str], emp_id: Any) -> list[Any]:
        await self._reachable(org_id, user_id, permissions, emp_id)
        return await self.repo.list_for_employee(emp_id)

    async def upload(self, org_id: str, user_id: str, permissions: list[str], emp_id: Any,
                     data: EmployeeDocumentCreate) -> Any:
        """domain.js UPLOAD_DOCUMENT: satu pengajuan tertunda per jenis; dokumen lama tetap berlaku
        sampai yang baru diverifikasi."""
        await self._reachable(org_id, user_id, permissions, emp_id)
        if data.supersedes_id is not None and not await self.repo.belongs_to(data.supersedes_id, emp_id):
            raise NotFoundError(NOT_FOUND)
        if await self.repo.has_pending(emp_id, data.doc_type):
            raise AppError("DOCUMENT_PENDING", "Masih ada dokumen jenis ini menunggu pemeriksaan.", status=409)
        return await self.repo.insert(
            emp_id=emp_id, doc_type=data.doc_type, masked=mask_number(data.number),
            number_hash=hashlib.sha256(data.number.encode("utf-8")).digest(), expiry=data.expiry_date,
            file_id=data.file_id, user_id=user_id, supersedes_id=data.supersedes_id)

    async def verify(self, org_id: str, user_id: str, emp_id: Any, doc_id: Any, data: EmployeeDocumentVerify) -> Any:
        """domain.js VERIFY_DOCUMENT: hanya yang PENDING; pemilik maupun pengunggah tidak memverifikasi
        dokumennya sendiri; disetujui → versi berlaku sebelumnya menjadi SUPERSEDED (R8)."""
        doc = await self.repo.for_decision(doc_id, emp_id, org_id)
        if doc is None:
            raise NotFoundError(NOT_FOUND)
        if doc.status != "PENDING":
            raise AppError("NOT_PENDING", "Dokumen tidak menunggu verifikasi.", status=409)
        if str(doc.uploaded_by) == str(user_id) or str(await self.repo.employee_of_user(user_id)) == str(emp_id):
            raise AppError("FOUR_EYES", "Pemilik atau pengunggah tidak dapat memverifikasi dokumen sendiri.",
                           status=409)
        if data.is_approved:
            await self.repo.supersede_current(emp_id, doc_id, doc.doc_type)
        return await self.repo.decide(
            doc_id, status="VERIFIED" if data.is_approved else "REJECTED",
            lifecycle="CURRENT" if data.is_approved else "PENDING", user_id=user_id,
            note=(data.review_note or "").strip() or None)
