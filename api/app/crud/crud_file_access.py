"""
app/crud/crud_file_access.py
Tautan sebuah berkas (V-17): dokumen pribadi, swafoto absensi, bukti pekerjaan (laporan harian,
insiden, laporan akhir) — beserta apakah pengguna pemiliknya. Keputusan boleh/tidak ada di
`api/deps.py::check_file_access`.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDFileAccess(CRUDBase):
    """
    Kelas operasi CRUD untuk menangani hak akses dan izin berkas (file).
    Memeriksa keterkaitan berkas (sebagai dokumen pribadi, swafoto absensi, atau bukti pekerjaan)
    guna memastikan izin pengunduhan/tontonan sesuai R-17.
    """

    async def links(self, file_id: UUID | str, org_id: UUID | str, user_id: UUID | str,
                    view_all_attendance: bool = False) -> Any:
        """
        Mendapatkan metadata tautan dan peran (role) dari suatu berkas berdasarkan ID-nya,
        untuk memvalidasi apakah pengguna memiliki hak akses terhadap file tersebut.
        Mengembalikan None jika berkas tidak ditemukan atau milik organisasi lain.

        Args:
            file_id (UUID | str): ID file.
            org_id (UUID | str): ID organisasi dari pengguna yang merequest.
            user_id (UUID | str): ID pengguna yang meminta akses.
            view_all_attendance (bool): Flag apakah pengguna berhak melihat semua data absensi. Defaults to False.

        Returns:
            Any: Baris data (Row) yang berisi metadata file dan bendera (flags) hak akses.
        """
        # Melakukan sub-kueri (EXISTS) secara paralel terhadap tabel-tabel terkait:
        # dokumen (employee_document), absensi (attendance), dan bukti laporan (report_evidence, dll).
        # Hasilnya adalah serangkaian nilai boolean dan array ID rencana (plan_ids) untuk validasi di lapisan atas.
        return await self.fetchone(
            """
            SELECT f.storage_key, f.mime_type,
                   f.uploaded_by IS NOT DISTINCT FROM CAST(:user AS uuid) AS is_uploader,
                   EXISTS (SELECT 1 FROM vms.employee_document d WHERE d.file_id = f.id) AS personal_document,
                   EXISTS (SELECT 1 FROM vms.employee_document d
                           JOIN vms.app_user u ON u.employee_id = d.employee_id
                           WHERE d.file_id = f.id AND u.id = CAST(:user AS uuid)) AS own_document,
                   EXISTS (SELECT 1 FROM vms.attendance a WHERE a.selfie_file_id = f.id) AS selfie,
                   EXISTS (SELECT 1 FROM vms.attendance a
                           JOIN vms.app_user u ON u.employee_id = a.employee_id
                           WHERE a.selfie_file_id = f.id AND u.id = CAST(:user AS uuid)) AS own_selfie,
                   EXISTS (SELECT 1 FROM vms.attendance a
                           WHERE a.selfie_file_id = f.id
                             AND vms.attendance_viewable(CAST(:viewer AS uuid), CAST(:view_all AS boolean),
                                                         a.employee_id)) AS selfie_viewable,
                   ARRAY(
                       SELECT wd.work_plan_id FROM vms.report_evidence re
                       JOIN vms.daily_report dr ON dr.id = re.daily_report_id
                       JOIN vms.work_plan_day wd ON wd.id = dr.work_plan_day_id
                       WHERE re.file_id = f.id
                       UNION
                       SELECT ir.work_plan_id FROM vms.incident_evidence ie
                       JOIN vms.incident_report ir ON ir.id = ie.incident_id
                       WHERE ie.file_id = f.id
                       UNION
                       SELECT fe.work_plan_id FROM vms.final_report_evidence fe WHERE fe.file_id = f.id
                   ) AS plan_ids
            FROM vms.file_object f
            WHERE f.id = CAST(:file AS uuid) AND f.organization_id = CAST(:org AS uuid)
            """,
            {"file": str(file_id), "org": org_id, "user": user_id,
             "viewer": str(user_id), "view_all": view_all_attendance},
        )
