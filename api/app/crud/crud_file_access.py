"""
app/crud/crud_file_access.py
Tautan sebuah berkas dan validasi akses Master Schema V2.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.repository import CRUDBase


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
        row = await self.fetchone(
            """
            SELECT
                f.storage_key,
                f.mime_type,
                f.file_name,
                (f.uploaded_by = CAST(:uid AS uuid)) AS is_uploader,
                FALSE AS personal_document,
                FALSE AS own_document,
                FALSE AS work_type_example,
                FALSE AS selfie,
                (EXISTS (
                    SELECT 1 FROM employee e
                    WHERE e.profile_photo_path = CAST(f.id AS text) AND e.delete_at IS NULL
                )) AS profile_photo,
                (EXISTS (
                    SELECT 1 FROM employee e
                    JOIN users u ON u.employee_id = e.employee_id
                    WHERE e.profile_photo_path = CAST(f.id AS text)
                      AND u.user_id = CAST(:uid AS uuid)
                      AND e.delete_at IS NULL
                )) AS own_profile_photo,
                FALSE AS own_selfie,
                FALSE AS selfie_viewable,
                COALESCE((
                    SELECT array_agg(CAST(wpa.work_plan_id AS text))
                    FROM work_plan_attachment wpa
                    WHERE wpa.file_id = f.id
                ), ARRAY[]::text[]) AS plan_ids
            FROM file_object f
            WHERE f.id = CAST(:fid AS uuid)
            """,
            {"fid": str(file_id), "uid": str(user_id)},
        )
        if row:
            return row

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
                   FALSE AS selfie_viewable,
                   ARRAY[]::text[] AS plan_ids
            """,
            {"fid": str(file_id)},
        )

