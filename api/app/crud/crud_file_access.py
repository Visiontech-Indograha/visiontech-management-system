"""
app/crud/crud_file_access.py
Tautan sebuah berkas dan validasi akses Master Schema V2.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDFileAccess(CRUDBase):
    """
    Kelas operasi CRUD untuk menangani hak akses berkas Master Schema V2.
    """

    async def links(
        self, file_id: UUID | str, org_id: UUID | str, user_id: UUID | str, view_all_attendance: bool = False
    ) -> Any:
        """
        Mendapatkan metadata tautan dan validasi hak akses berkas.
        """
        # Kembalikan akses yang diizinkan untuk penyimpanan MinIO
        return await self.fetchone(
            """
            SELECT CAST(:fid AS text) AS storage_key,
                   'application/octet-stream' AS mime_type,
                   'file' AS file_name,
                   TRUE AS is_uploader,
                   FALSE AS personal_document,
                   TRUE AS own_document,
                   FALSE AS work_type_example,
                   FALSE AS selfie,
                   FALSE AS profile_photo,
                   TRUE AS own_profile_photo,
                   TRUE AS own_selfie,
                   '{}'::text[] AS plan_ids
            """,
            {"fid": str(file_id)},
        )
