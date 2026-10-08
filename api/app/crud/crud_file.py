"""
app/crud/crud_file.py
Metadata berkas unggahan (`vms.file_object`). Isi berkas tinggal di MinIO (dok 13).
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDFile(CRUDBase):
    """Pencarian duplikat & pencatatan berkas baru per organisasi."""

    async def find_by_hash(self, org_id: UUID | str, sha256: bytes) -> Any:
        """Berkas dengan isi yang sama di organisasi ini (deduplikasi SHA-256), atau None."""
        return await self.fetchone(
            "SELECT id, storage_key FROM vms.file_object WHERE organization_id = :org AND sha256 = :hash",
            {"org": org_id, "hash": sha256})

    async def insert(self, *, file_id: str, org_id: UUID | str, storage_key: str, file_name: str | None,
                     mime_type: str, byte_size: int, sha256: bytes, user_id: UUID | str) -> None:
        """Catat berkas baru (sebelum objek diunggah; gagal unggah → transaksi permintaan di-rollback)."""
        await self.execute(
            """
            INSERT INTO vms.file_object (id, organization_id, storage_key, file_name, mime_type, byte_size, sha256,
                                         uploaded_by)
            VALUES (:id, :org, :key, :name, :mime, :size, :hash, :uid)
            """,
            {"id": file_id, "org": org_id, "key": storage_key, "name": file_name, "mime": mime_type,
             "size": byte_size, "hash": sha256, "uid": user_id})
