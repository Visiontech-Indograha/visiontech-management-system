"""
app/shared/access/file_access_repository.py
Tautan sebuah berkas (file_object) ke tabel pemakainya — dasar `check_file_access` (Master Schema V2).
Tabel pemakai menyimpan `file_object.storage_key` di kolom *_path / path_file.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository
from app.shared.access.office_scope import attendance_office_scope
from app.shared.access.pm_reach import pm_reaches_employee
from app.shared.access.scope_rules import work_order_visible_sql


class FileAccessRepository(BaseRepository):
    """Query tautan berkas: template, aset, profil, dokumen karyawan, swafoto, lampiran jadwal."""

    async def links(self, file_id: UUID | str, employee_id: UUID | str | None, *, is_pm: bool = False) -> Any:
        """Metadata berkas + jenis tautannya; None bila berkas tidak ada."""
        return await self.fetchone(
            f"""
            SELECT f.id, f.storage_key, f.mime_type, f.file_name, f.uploaded_by,
                   -- contoh/petunjuk kerja (image_requirement): semua pengguna yang login
                   (EXISTS (SELECT 1 FROM image_requirement ir
                           WHERE ir.path_image IN (f.storage_key, f.id::text)
                             AND ir.delete_at IS NULL)
                    -- foto carousel kampanye K3 yang sedang aktif: dilihat semua pengguna yang login
                    OR EXISTS (SELECT 1 FROM hse_campaigns hc
                           WHERE hc.media_paths ? f.id::text
                             AND hc.is_active = TRUE AND hc.delete_at IS NULL)
                   ) AS public_in_org,
                   -- foto/berkas aset: dibatasi cakupan aset (asset_file_visible di access_service)
                   (EXISTS (SELECT 1 FROM tool t WHERE t.photo_path = f.storage_key AND t.delete_at IS NULL)
                    OR EXISTS (SELECT 1 FROM vehicle v WHERE v.photo_path = f.storage_key AND v.delete_at IS NULL)
                    OR EXISTS (SELECT 1 FROM vehicle_file vf WHERE vf.path_file = f.storage_key)
                    OR EXISTS (SELECT 1 FROM vehicle_inspection vi WHERE vi.path_file = f.storage_key)
                    OR EXISTS (SELECT 1 FROM asset_assignment aa WHERE aa.handover_photo_path = f.storage_key)
                   ) AS asset_file,
                   (SELECT pe.employee_id FROM employee pe WHERE pe.profile_photo_path = f.storage_key LIMIT 1)
                       AS profile_owner,
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
                           AND {pm_reaches_employee('CAST(:emp AS uuid)', 'a.employee_id')}) AS selfie_pm,
                   EXISTS (SELECT 1 FROM attendance a JOIN employee se ON se.employee_id = a.employee_id
                           WHERE f.storage_key IN (a.face_photo_path, a.out_of_radius_photo_path)
                           AND {attendance_office_scope('CAST(:emp AS uuid)', 'se.office_id')}) AS selfie_office,
                   EXISTS (SELECT 1 FROM attendance a
                           WHERE f.storage_key IN (a.face_photo_path, a.out_of_radius_photo_path)
                           AND a.employee_id = CAST(:emp AS uuid)) AS own_selfie,
                   -- foto titik survei WO (work_order_survey_points.photos_json, bentuk {file_id} atau larik lama)
                   EXISTS (SELECT 1 FROM work_order_survey_points p
                           WHERE p.delete_at IS NULL AND (p.photos_json @> jsonb_build_array(
                               jsonb_build_object('file_id', f.id::text))
                           OR p.photos_json ? f.id::text OR p.photos_json ? f.storage_key)) AS survey_point_file,
                   EXISTS (SELECT 1 FROM work_order_survey_points p
                           JOIN client_work_orders wo ON wo.work_order_id = p.work_order_id AND wo.delete_at IS NULL
                           WHERE p.delete_at IS NULL AND (p.photos_json @> jsonb_build_array(
                               jsonb_build_object('file_id', f.id::text))
                           OR p.photos_json ? f.id::text OR p.photos_json ? f.storage_key)
                           AND {work_order_visible_sql('wo')}) AS survey_point_visible,
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
            {"fid": str(file_id), "emp": str(employee_id) if employee_id else None,
             "viewer_emp": str(employee_id) if employee_id else None, "pm": is_pm},
        )
