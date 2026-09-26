"""
app/repositories/document_repo.py
Dokumen pribadi karyawan — kueri untuk servis baru (R-19). Rute lama di api/documents.py belum dipindah.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base_repo import BaseRepo


class DocumentRepo(BaseRepo):

    async def pending_for_org(self, org_id: UUID | str, user_id: UUID | str) -> list[Any]:
        """Antrean verifikasi HR: dokumen PENDING milik karyawan organisasi ini, terlama dulu."""
        return list(await self.fetchall(
            """
            SELECT d.id, d.employee_id, e.full_name, d.doc_type, d.number_masked, d.expiry_date, d.file_id,
                   d.created_at AS uploaded_at, (d.uploaded_by = CAST(:uid AS uuid)) AS uploaded_by_me
            FROM vms.employee_document d JOIN vms.employee e ON e.id = d.employee_id
            WHERE e.organization_id = :org AND e.deleted_at IS NULL AND d.status = 'PENDING'
            ORDER BY d.created_at
            """,
            {"org": org_id, "uid": user_id}))
