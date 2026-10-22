"""
app/shared/access/file_access_repository.py
Tautan sebuah berkas (file_object) ke tabel pemakainya — dasar `check_file_access` (Master Schema V2).
Tabel pemakai menyimpan `file_object.storage_key` di kolom *_path / path_file.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository


class FileAccessRepository(BaseRepository):
    """Query tautan berkas: template, aset, profil, dokumen karyawan, swafoto, lampiran jadwal."""

    async def links(self, file_id: UUID | str, employee_id: UUID | str | None) -> Any:
        """Metadata berkas + jenis tautannya; None bila berkas tidak ada."""
        return await self.fetchone(
            """
            SELECT f.id, f.storage_key, f.mime_type, f.file_name, f.uploaded_by,
                   (EXISTS (SELECT 1 FROM image_requirement ir
                           WHERE ir.path_image IN (f.storage_key, f.id::text) AND ir.delete_at IS NULL)
                    OR EXISTS (SELECT 1 FROM tool t WHERE t.photo_path = f.storage_key AND t.delete_at IS NULL)
                    OR EXISTS (SELECT 1 FROM vehicle v WHERE v.photo_path = f.storage_key AND v.delete_at IS NULL)
                    OR EXISTS (SELECT 1 FROM vehicle_file vf WHERE vf.path_file = f.storage_key)
                    OR EXISTS (SELECT 1 FROM vehicle_inspection vi WHERE vi.path_file = f.storage_key)
                    OR EXISTS (SELECT 1 FROM asset_assignment aa WHERE aa.handover_photo_path = f.storage_key)
                   ) AS public_in_org,
                   EXISTS (SELECT 1 FROM employee e WHERE e.profile_photo_path = f.storage_key) AS profile_photo,
                   EXISTS (SELECT 1 FROM employee e WHERE e.profile_photo_path = f.storage_key
                           AND e.employee_id = CAST(:emp AS uuid)) AS own_profile,
                   EXISTS (SELECT 1 FROM employee_file ef WHERE ef.path_file = f.storage_key) AS personal_document,
                   EXISTS (SELECT 1 FROM employee_file ef WHERE ef.path_file = f.storage_key
                           AND ef.employee_id = CAST(:emp AS uuid)) AS own_document,
                   EXISTS (SELECT 1 FROM attendance a
                           WHERE f.storage_key IN (a.face_photo_path, a.out_of_radius_photo_path))
                       AS selfie,
                   EXISTS (SELECT 1 FROM attendance a
                           WHERE f.storage_key IN (a.face_photo_path, a.out_of_radius_photo_path)
                           AND a.employee_id = CAST(:emp AS uuid)) AS own_selfie,
                   ARRAY(
                       SELECT wpa.daily_plan_id::text FROM work_plan_attachment wpa WHERE wpa.file_id = f.id
                       UNION  -- foto bukti / foto titik survei pada item jadwal
                       SELECT i.daily_plan_id::text FROM work_plan_item i
                       WHERE i.delete_at IS NULL
                         AND i.realization_photos_json @> jsonb_build_array(jsonb_build_object('file_id', f.id::text))
                       UNION  -- foto order (mis. layout laporan survei): lewat jadwal item order itu
                       SELECT i.daily_plan_id::text FROM work_completion wc
                       JOIN work_plan_item i ON i.completion_id = wc.completion_id AND i.delete_at IS NULL
                       WHERE wc.realization_photos_json @> jsonb_build_array(jsonb_build_object('file_id', f.id::text))
                   ) AS daily_plan_ids
            FROM file_object f
            WHERE f.id = CAST(:fid AS uuid)
            """,
            {"fid": str(file_id), "emp": str(employee_id) if employee_id else None},
        )
