"""
app/crud/crud_file.py
Metadata berkas unggahan Master Schema V2.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository


class FileRepository(BaseRepository):
    """Repositori pendaftaran dan metadata berkas storage."""
    """Pencatatan berkas baru Master Schema V2."""

    async def find_by_hash(self, org_id: UUID | str, sha256: bytes) -> Any:
        """Mencari berkas di organisasi dengan hash SHA256 yang sama untuk deduplikasi."""
        return await self.fetchone(
            """
            SELECT CAST(id AS text) AS id, storage_key, file_name, mime_type, byte_size
            FROM file_object
            WHERE organization_id = CAST(:org AS uuid) AND sha256 = :hash
            LIMIT 1
            """,
            {"org": org_id, "hash": sha256},
        )

    async def insert(
        self,
        *,
        file_id: str,
        org_id: UUID | str,
        storage_key: str,
        file_name: str | None,
        mime_type: str,
        byte_size: int,
        sha256: bytes,
        user_id: UUID | str,
    ) -> str:
        """Catat berkas baru (mengembalikan file_id langsung atau id hasil deduplikasi)."""
        row = await self.fetchone(
            """
            INSERT INTO file_object (
                id, organization_id, storage_key, file_name, mime_type, byte_size, sha256, uploaded_by
            )
            VALUES (
                CAST(:fid AS uuid), CAST(:org AS uuid), :storage_key,
                :file_name, :mime_type, :byte_size, :sha256, CAST(:uid AS uuid)
            )
            ON CONFLICT (organization_id, sha256) DO UPDATE
            SET file_name = EXCLUDED.file_name
            RETURNING CAST(id AS text) AS id
            """,
            {
                "fid": file_id,
                "org": org_id,
                "storage_key": storage_key,
                "file_name": file_name or "file",
                "mime_type": mime_type,
                "byte_size": byte_size,
                "sha256": sha256,
                "uid": user_id,
            },
        )
        return str(row.id) if row else str(file_id)



CRUDFile = FileRepository
