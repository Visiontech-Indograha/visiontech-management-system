"""
app/modules/documents/repositories/document_repository.py
Dokumen & sertifikat karyawan (tabel employee_file, Master Schema V2).

Relasi: employee 1─N employee_file. Berkas fisik ada di file_object; `path_file` menyimpan
`file_object.storage_key` sehingga berkas dapat dilacak balik tanpa kolom tambahan.
Siklus status (doc_status_enum): active → extended (diganti dokumen baru sejenis) atau
not_active (lewat `expired_at`, atau dinonaktifkan HR).
"""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository

# Tanggal dibaca dalam WIB agar "hari ini" sama dengan jam kerja lapangan.
_COLUMNS = """
    ef.employee_file_id AS id, ef.employee_id, ef.type AS doc_type, ef.status::text AS status,
    (ef.active_at AT TIME ZONE 'Asia/Jakarta')::date AS active_at,
    (ef.expired_at AT TIME ZONE 'Asia/Jakarta')::date AS expired_at,
    fo.id AS file_id, ef.create_at AS created_at
"""
_FROM = "FROM employee_file ef LEFT JOIN file_object fo ON fo.storage_key = ef.path_file"

# Ambang urgensi kedaluwarsa (hari).
CRITICAL_DAYS = 7
WARNING_DAYS = 30


class DocumentRepository(BaseRepository):
    """Query tabel employee_file."""

    async def employee_of_user(self, user_id: UUID | str) -> str | None:
        val = await self.scalar(
            "SELECT employee_id FROM users WHERE user_id = CAST(:uid AS uuid) AND delete_at IS NULL",
            {"uid": str(user_id)},
        )
        return str(val) if val else None

    async def employee_exists(self, emp_id: UUID | str) -> bool:
        return bool(
            await self.scalar(
                "SELECT EXISTS (SELECT 1 FROM employee WHERE employee_id = CAST(:emp AS uuid) AND delete_at IS NULL)",
                {"emp": str(emp_id)},
            )
        )

    async def file_key(self, file_id: UUID | str) -> str | None:
        """storage_key file_object yang akan disimpan ke `path_file`, atau None bila berkas tidak ada."""
        key: str | None = await self.scalar(
            "SELECT storage_key FROM file_object WHERE id = CAST(:id AS uuid)", {"id": str(file_id)}
        )
        return key

    async def list_for_employee(self, emp_id: UUID | str) -> list[Any]:
        """Semua dokumen karyawan; yang berlaku di atas, lalu terbaru."""
        return list(
            await self.fetchall(
                f"""
                SELECT {_COLUMNS} {_FROM}
                WHERE ef.employee_id = CAST(:emp AS uuid) AND ef.delete_at IS NULL
                ORDER BY (ef.status = 'active') DESC, ef.type, ef.active_at DESC
                """,
                {"emp": str(emp_id)},
            )
        )

    async def get(self, doc_id: UUID | str, emp_id: UUID | str) -> Any:
        return await self.fetchone(
            f"""
            SELECT {_COLUMNS} {_FROM}
            WHERE ef.employee_file_id = CAST(:id AS uuid) AND ef.employee_id = CAST(:emp AS uuid)
              AND ef.delete_at IS NULL
            """,
            {"id": str(doc_id), "emp": str(emp_id)},
        )

    async def insert(
        self, emp_id: UUID | str, doc_type: str, path_file: str, active_at: date | None, expired_at: date | None
    ) -> UUID:
        """Dokumen baru sejenis menggantikan yang masih berlaku (lama → `extended`)."""
        await self.execute(
            """
            UPDATE employee_file SET status = 'extended', update_at = now()
            WHERE employee_id = CAST(:emp AS uuid) AND type = :type AND status = 'active' AND delete_at IS NULL
            """,
            {"emp": str(emp_id), "type": doc_type},
        )
        doc_id: UUID = await self.scalar(
            """
            INSERT INTO employee_file (employee_id, type, path_file, status, active_at, expired_at)
            VALUES (
                CAST(:emp AS uuid), :type, :path, 'active',
                COALESCE(CAST(:active AS date), (now() AT TIME ZONE 'Asia/Jakarta')::date)::timestamp
                    AT TIME ZONE 'Asia/Jakarta',
                CAST(:expired AS date)::timestamp AT TIME ZONE 'Asia/Jakarta'
            )
            RETURNING employee_file_id
            """,
            {"emp": str(emp_id), "type": doc_type, "path": path_file, "active": active_at, "expired": expired_at},
        )
        return doc_id

    async def deactivate(self, doc_id: UUID | str) -> None:
        await self.execute(
            "UPDATE employee_file SET status = 'not_active', update_at = now() "
            "WHERE employee_file_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"id": str(doc_id)},
        )

    async def archive(self, doc_id: UUID | str) -> None:
        """Soft delete — untuk dokumen yang salah unggah."""
        await self.execute(
            "UPDATE employee_file SET delete_at = now(), update_at = now() "
            "WHERE employee_file_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"id": str(doc_id)},
        )

    async def expiring(self, urgency: str | None) -> list[Any]:
        """Dokumen berlaku yang sudah/akan kedaluwarsa dalam WARNING_DAYS hari."""
        return list(
            await self.fetchall(
                """
                SELECT d.id, d.employee_id, d.full_name, d.doc_type, d.expiry_date, d.days_left, d.urgency
                FROM (
                    SELECT ef.employee_file_id AS id, ef.employee_id, e.full_name, ef.type AS doc_type,
                           x.expiry_date, x.days_left,
                           CASE WHEN x.days_left < 0 THEN 'EXPIRED'
                                WHEN x.days_left <= :critical THEN 'CRITICAL'
                                ELSE 'WARNING' END AS urgency
                    FROM employee_file ef
                    JOIN employee e ON e.employee_id = ef.employee_id AND e.delete_at IS NULL
                    CROSS JOIN LATERAL (
                        SELECT (ef.expired_at AT TIME ZONE 'Asia/Jakarta')::date AS expiry_date,
                               (ef.expired_at AT TIME ZONE 'Asia/Jakarta')::date
                                 - (now() AT TIME ZONE 'Asia/Jakarta')::date AS days_left
                    ) x
                    WHERE ef.status = 'active' AND ef.delete_at IS NULL AND ef.expired_at IS NOT NULL
                      AND x.days_left <= :warning
                ) d
                WHERE CAST(:urgency AS text) IS NULL OR d.urgency = :urgency
                ORDER BY d.days_left, d.full_name
                """,
                {"critical": CRITICAL_DAYS, "warning": WARNING_DAYS, "urgency": urgency},
            )
        )

    async def expire_overdue(self) -> int:
        """Pekerjaan berkala: dokumen berlaku yang tanggal kedaluwarsanya sudah lewat (WIB) → not_active."""
        rows = await self.fetchall(
            """
            UPDATE employee_file SET status = 'not_active', update_at = now()
            WHERE status = 'active' AND delete_at IS NULL
              AND (expired_at AT TIME ZONE 'Asia/Jakarta')::date < (now() AT TIME ZONE 'Asia/Jakarta')::date
            RETURNING employee_file_id
            """
        )
        return len(rows)
