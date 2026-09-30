"""
app/crud/crud_document.py
Dokumen pribadi karyawan — seluruh kueri modul (antrean HR R-19; daftar/ajukan/verifikasi R-20).
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDDocument(CRUDBase):

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

    async def employee_of_user(self, user_id: UUID | str) -> Any:
        return await self.scalar("SELECT employee_id FROM vms.app_user WHERE id = CAST(:uid AS uuid)", {"uid": user_id})

    async def employee_in_org(self, emp_id: UUID | str, org_id: UUID | str) -> bool:
        return bool(await self.scalar(
            "SELECT EXISTS (SELECT 1 FROM vms.employee WHERE id = CAST(:emp AS uuid) AND organization_id = :org)",
            {"emp": emp_id, "org": org_id}))

    async def list_for_employee(self, emp_id: UUID | str) -> list[Any]:
        return list(await self.fetchall(
            """
            SELECT id, employee_id, doc_type, number_masked, expiry_date, status, lifecycle, file_id,
                   uploaded_by, verified_by, verified_at, review_note, created_at
            FROM vms.employee_document WHERE employee_id = CAST(:emp AS uuid)
            ORDER BY created_at DESC
            """,
            {"emp": emp_id}))

    async def has_pending(self, emp_id: UUID | str, doc_type: str) -> bool:
        return bool(await self.scalar(
            """SELECT EXISTS (SELECT 1 FROM vms.employee_document
                              WHERE employee_id = CAST(:emp AS uuid) AND doc_type = :type AND status = 'PENDING')""",
            {"emp": emp_id, "type": doc_type}))

    async def belongs_to(self, doc_id: UUID | str, emp_id: UUID | str) -> bool:
        return bool(await self.scalar(
            "SELECT EXISTS (SELECT 1 FROM vms.employee_document WHERE id = CAST(:id AS uuid) AND employee_id = CAST(:emp AS uuid))",
            {"id": doc_id, "emp": emp_id}))

    async def insert(self, *, emp_id: UUID | str, doc_type: str, masked: str, number_hash: bytes,
                     expiry: Any, file_id: UUID | str, user_id: UUID | str, supersedes_id: UUID | str | None) -> Any:
        return await self.fetchone(
            """
            INSERT INTO vms.employee_document (employee_id, doc_type, number_masked, number_sha256,
                                               expiry_date, file_id, uploaded_by, supersedes_id)
            VALUES (CAST(:emp AS uuid), :type, :masked, :hash, :expiry, CAST(:fid AS uuid), CAST(:uid AS uuid),
                    CAST(:super_id AS uuid))
            RETURNING id, employee_id, doc_type, number_masked, expiry_date, status, lifecycle, file_id,
                      uploaded_by, verified_by, verified_at, review_note, created_at
            """,
            {"emp": emp_id, "type": doc_type, "masked": masked, "hash": number_hash, "expiry": expiry,
             "fid": file_id, "uid": user_id, "super_id": supersedes_id})

    async def for_decision(self, doc_id: UUID | str, emp_id: UUID | str, org_id: UUID | str) -> Any:
        """Dokumen milik karyawan organisasi ini, dikunci untuk diputus (tidak ada dua pemeriksa bersamaan)."""
        return await self.fetchone(
            """
            SELECT d.id, d.doc_type, d.status::text AS status, d.uploaded_by
            FROM vms.employee_document d JOIN vms.employee e ON e.id = d.employee_id
            WHERE d.id = CAST(:id AS uuid) AND d.employee_id = CAST(:emp AS uuid) AND e.organization_id = :org
            FOR UPDATE OF d
            """,
            {"id": doc_id, "emp": emp_id, "org": org_id})

    async def supersede_current(self, emp_id: UUID | str, doc_id: UUID | str, doc_type: str) -> None:
        await self.execute(
            """
            UPDATE vms.employee_document SET lifecycle = 'SUPERSEDED'
            WHERE employee_id = CAST(:emp AS uuid) AND lifecycle = 'CURRENT' AND id <> CAST(:id AS uuid)
              AND doc_type = :type
            """,
            {"emp": emp_id, "id": doc_id, "type": doc_type})

    async def decide(self, doc_id: UUID | str, *, status: str, lifecycle: str, user_id: UUID | str,
                     note: str | None) -> Any:
        return await self.fetchone(
            """
            UPDATE vms.employee_document
            SET status = CAST(:status AS vms.personal_document_status),
                lifecycle = CAST(:lifecycle AS vms.personal_document_lifecycle),
                verified_by = CAST(:uid AS uuid), verified_at = now(), review_note = :note
            WHERE id = CAST(:id AS uuid)
            RETURNING id, employee_id, doc_type, number_masked, expiry_date, status, lifecycle, file_id,
                      uploaded_by, verified_by, verified_at, review_note, created_at
            """,
            {"id": doc_id, "status": status, "lifecycle": lifecycle, "uid": user_id, "note": note})
