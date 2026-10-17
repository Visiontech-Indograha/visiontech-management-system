"""
app/crud/crud_document.py
Dokumen dan sertifikat karyawan dari tabel employee_file (Master Schema V2).
Tipe dokumen: 'KTP', 'SIM_A', 'SIM_B', 'SERTIFIKAT_K3', 'PKWT', dsb.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDDocument(CRUDBase):
    """
    Operasi CRUD berkas dokumen dan sertifikat karyawan (tabel employee_file).
    """

    async def employee_of_user(self, user_id: UUID | str) -> UUID | None:
        """Mendapatkan employee_id dari user_id."""
        val = await self.scalar(
            "SELECT employee_id FROM users WHERE user_id = CAST(:uid AS uuid) AND delete_at IS NULL",
            {"uid": user_id},
        )
        return UUID(str(val)) if val else None

    async def employee_in_org(self, emp_id: UUID | str, org_id: UUID | str) -> bool:
        """Cek apakah karyawan ada di sistem."""
        return bool(await self.scalar(
            "SELECT EXISTS (SELECT 1 FROM employee WHERE employee_id = CAST(:emp AS uuid) AND delete_at IS NULL)",
            {"emp": emp_id},
        ))

    async def pending_for_org(self, org_id: UUID | str, user_id: UUID | str) -> list[Any]:
        """Dokumen yang menunggu verifikasi HR (status not_active)."""
        return list(
            await self.fetchall(
                """
                SELECT 
                    ef.employee_file_id AS id,
                    ef.employee_id,
                    e.full_name,
                    ef.type AS doc_type,
                    ef.type AS number_masked,
                    ef.expired_at::date AS expiry_date,
                    ef.employee_file_id AS file_id,
                    ef.create_at AS uploaded_at,
                    FALSE AS uploaded_by_me
                FROM employee_file ef
                JOIN employee e ON e.employee_id = ef.employee_id
                WHERE ef.status = 'not_active' AND ef.delete_at IS NULL
                ORDER BY ef.create_at ASC
                """,
                {},
            )
        )

    async def list_for_employee(self, emp_id: UUID | str) -> list[Any]:
        """Daftar berkas dokumen milik seorang karyawan."""
        return list(
            await self.fetchall(
                """
                SELECT 
                    ef.employee_file_id AS id,
                    ef.employee_id,
                    ef.type AS doc_type,
                    ef.type AS number_masked,
                    ef.expired_at::date AS expiry_date,
                    ef.status::text AS status,
                    'CURRENT' AS lifecycle,
                    ef.employee_file_id AS file_id,
                    ef.path_file,
                    ef.employee_id AS uploaded_by,
                    NULL::uuid AS verified_by,
                    NULL::timestamptz AS verified_at,
                    NULL::text AS review_note,
                    ef.create_at AS created_at
                FROM employee_file ef
                WHERE ef.employee_id = CAST(:emp AS uuid) AND ef.delete_at IS NULL
                ORDER BY ef.create_at DESC
                """,
                {"emp": emp_id},
            )
        )

    async def has_pending(self, emp_id: UUID | str, doc_type: str) -> bool:
        """Cek apakah ada dokumen bertipe sama yang masih not_active."""
        return bool(
            await self.scalar(
                """
                SELECT EXISTS (
                    SELECT 1 FROM employee_file 
                    WHERE employee_id = CAST(:emp AS uuid) 
                      AND type = :type 
                      AND status = 'not_active' 
                      AND delete_at IS NULL
                )
                """,
                {"emp": emp_id, "type": doc_type},
            )
        )

    async def get(self, doc_id: UUID | str) -> Any:
        """Mengambil detail satu dokumen."""
        return await self.fetchone(
            """
            SELECT 
                ef.employee_file_id AS id,
                ef.employee_id,
                ef.type AS doc_type,
                ef.type AS number_masked,
                ef.expired_at::date AS expiry_date,
                ef.status::text AS status,
                'CURRENT' AS lifecycle,
                ef.employee_file_id AS file_id,
                ef.path_file,
                NULL::uuid AS verified_by,
                NULL::timestamptz AS verified_at,
                ef.create_at AS created_at
            FROM employee_file ef
            WHERE ef.employee_file_id = CAST(:id AS uuid) AND ef.delete_at IS NULL
            """,
            {"id": doc_id},
        )

    async def insert(
        self,
        emp_id: UUID | str,
        doc_type: str,
        number: str,
        expiry: Any,
        file_id: UUID | str,
        uploaded_by: UUID | str,
    ) -> Any:
        """Menambahkan dokumen baru ke employee_file."""
        return await self.fetchone(
            """
            INSERT INTO employee_file (
                employee_id, type, path_file, status, active_at, expired_at
            )
            VALUES (
                CAST(:emp AS uuid),
                :type,
                :path,
                'active',
                now(),
                CAST(:exp AS timestamptz)
            )
            RETURNING 
                employee_file_id AS id, employee_id, type AS doc_type, 
                type AS number_masked, expired_at::date AS expiry_date, 
                status::text AS status, 'CURRENT' AS lifecycle, 
                employee_file_id AS file_id, create_at AS created_at
            """,
            {
                "emp": emp_id,
                "type": doc_type,
                "path": f"/files/emp/{file_id}_{doc_type.lower()}.pdf",
                "exp": expiry,
            },
        )

    async def verify(
        self,
        doc_id: UUID | str,
        decision: str,
        note: str | None,
        verified_by: UUID | str,
    ) -> None:
        """Memverifikasi dokumen karyawan."""
        status = "active" if decision == "APPROVED" else "not_active"
        await self.execute(
            """
            UPDATE employee_file
            SET status = CAST(:status AS doc_status_enum),
                update_at = now()
            WHERE employee_file_id = CAST(:id AS uuid)
            """,
            {"id": doc_id, "status": status},
        )
