"""
app/crud/crud_employee.py
Kueri karyawan (daftar, detail, tambah, ubah, bentrok jadwal, V-29). Satu-satunya tempat SQL karyawan.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDEmployee(CRUDBase):
    """
    Kelas operasi CRUD untuk data karyawan (seperti manajemen status aktif,
    riwayat penempatan/mutasi, dan pemutusan hubungan kerja/offboarding).
    """

    async def employee_of_user(self, user_id: UUID | str) -> Any:
        """
        Mendapatkan ID karyawan yang dikaitkan dengan sebuah akun pengguna.

        Args:
            user_id (UUID | str): ID pengguna (app_user).

        Returns:
            Any: ID karyawan (UUID) jika ada.
        """
        # Mengambil kolom employee_id dari tabel app_user
        return await self.scalar("SELECT employee_id FROM vms.app_user WHERE id = CAST(:uid AS uuid)", {"uid": user_id})

    async def lock(self, employee_id: UUID | str, org_id: UUID | str) -> Any:
        """
        Mengunci baris karyawan tertentu untuk keperluan pembaruan data secara aman (FOR UPDATE).

        Args:
            employee_id (UUID | str): ID karyawan.
            org_id (UUID | str): ID organisasi karyawan tersebut.

        Returns:
            Any: Status karyawan (apakah dihapus, aktif, dan unitnya).
        """
        # Mengunci baris menggunakan FOR UPDATE agar tidak ada transaksi lain yang mengubah data ini bersamaan
        return await self.fetchone(
            """
            SELECT id, deleted_at IS NOT NULL AS deleted, is_active, CAST(unit_id AS text) AS unit_id
            FROM vms.employee WHERE id = :id AND organization_id = :org
            FOR UPDATE
            """,
            {"id": employee_id, "org": org_id},
        )

    async def restore(self, employee_id: UUID | str) -> None:
        """
        Memulihkan (restore) karyawan yang sebelumnya dihapus secara lunak (soft deleted).
        Karyawan akan kembali dengan status NONAKTIF, dan akunnya tetap dinonaktifkan (dicabut).
        Ini mewakili operasi domain.js RESTORE_EMPLOYEE.

        Args:
            employee_id (UUID | str): ID karyawan.
        """
        # Menghapus tanda deleted_at, mengatur status is_active ke false, lalu menonaktifkan akun terkait di app_user
        await self.execute(
            "UPDATE vms.employee SET deleted_at = NULL, is_active = false, updated_at = now() WHERE id = :id",
            {"id": employee_id})
        await self.execute("UPDATE vms.app_user SET is_active = false WHERE employee_id = :id", {"id": employee_id})

    async def archive(self, employee_id: UUID | str) -> None:
        """
        Melakukan hapus lunak (soft delete) terhadap karyawan.
        Data akan tersembunyi dari daftar, namun data historis (seperti SK, absensi, dokumen) tetap terjaga.

        Args:
            employee_id (UUID | str): ID karyawan.
        """
        # Mengatur nilai deleted_at menjadi waktu saat ini dan menonaktifkan karyawan serta akun penggunanya
        await self.execute(
            "UPDATE vms.employee SET deleted_at = now(), is_active = false, updated_at = now() WHERE id = :id",
            {"id": employee_id})
        await self.execute("UPDATE vms.app_user SET is_active = false WHERE employee_id = :id", {"id": employee_id})

    async def assignments(self, employee_id: UUID | str, org_id: UUID | str) -> list[Any] | None:
        """
        Mendapatkan riwayat penempatan (jabatan/unit) karyawan, diurutkan dari yang terbaru.
        Mengembalikan None bila karyawan bukan milik organisasi ini.

        Args:
            employee_id (UUID | str): ID karyawan.
            org_id (UUID | str): ID organisasi.

        Returns:
            list[Any] | None: Daftar riwayat penempatan karyawan.
        """
        # Memastikan karyawan benar-benar terdaftar di organisasi yang diminta sebelum mengambil riwayatnya
        if not await self.scalar("SELECT 1 FROM vms.employee WHERE id = :id AND organization_id = :org",
                                 {"id": employee_id, "org": org_id}):
            return None
        # Mengambil riwayat penempatan dan JOIN dengan tabel business_unit untuk mendapatkan nama unit
        return list(await self.fetchall(
            """
            SELECT a.id, a.employee_id, a.position, a.unit_id, u.name AS unit_name, a.valid_from, a.valid_to
            FROM vms.employee_assignment a LEFT JOIN vms.business_unit u ON u.id = a.unit_id
            WHERE a.employee_id = :id
            ORDER BY a.valid_from DESC, a.valid_to DESC NULLS FIRST
            """,
            {"id": employee_id}))

    async def last_assignment_start(self, employee_id: UUID | str) -> Any:
        """
        Mendapatkan tanggal mulai dari penempatan (assignment) yang paling terakhir (terbaru).

        Args:
            employee_id (UUID | str): ID karyawan.

        Returns:
            Any: Tanggal (date) mulai penempatan terakhir.
        """
        # Menggunakan agregasi MAX() untuk mendapatkan tanggal valid_from terbesar
        return await self.scalar(
            "SELECT max(valid_from) FROM vms.employee_assignment WHERE employee_id = :id", {"id": employee_id})

    async def promote(self, employee_id: UUID | str, position: str, unit_id: str | None, valid_from: Any) -> Any:
        """
        Mempromosikan atau memutasi karyawan ke jabatan/unit baru.
        Tindakan ini akan menutup riwayat penempatan lama dan membuka riwayat baru mulai tanggal yang ditentukan,
        serta memperbarui data induk karyawan secara sinkron.

        Args:
            employee_id (UUID | str): ID karyawan.
            position (str): Jabatan baru.
            unit_id (str | None): ID unit bisnis baru.
            valid_from (Any): Tanggal mulai berlaku penempatan baru.

        Returns:
            Any: Baris data penempatan yang baru dibuat.
        """
        # Menutup penempatan saat ini (yang valid_to-nya masih NULL) dengan mengatur valid_to sama dengan tanggal mulai penempatan baru
        await self.execute(
            "UPDATE vms.employee_assignment SET valid_to = :start WHERE employee_id = :id AND valid_to IS NULL",
            {"id": employee_id, "start": valid_from})
        # Membuat record penempatan baru
        row = await self.fetchone(
            """
            INSERT INTO vms.employee_assignment (employee_id, position, unit_id, valid_from)
            VALUES (:id, :pos, :unit, :start)
            RETURNING id, employee_id, position, unit_id, valid_from, valid_to
            """,
            {"id": employee_id, "pos": position, "unit": unit_id, "start": valid_from})
        # Memperbarui data posisi dan unit di tabel utama karyawan (vms.employee)
        await self.execute(
            "UPDATE vms.employee SET position = :pos, unit_id = :unit, updated_at = now() WHERE id = :id",
            {"id": employee_id, "pos": position, "unit": unit_id})
        return row

    async def on_running_plan(self, employee_id: UUID | str) -> bool:
        """
        Mengecek apakah karyawan saat ini masih terlibat dalam Surat Kerja (SK) yang sedang berjalan
        (bukan berstatus DRAFT, COMPLETED, atau CANCELLED).
        Ini krusial sebelum melakukan pemberhentian kerja (offboard).

        Args:
            employee_id (UUID | str): ID karyawan.

        Returns:
            bool: True jika masih terkait dengan SK berjalan, False jika tidak.
        """
        # Mengecek apakah karyawan bertindak sebagai PM (Project Manager), ketua (leader), atau
        # anggota tim dengan masa berlaku yang mencakup masa tak terhingga (upper_inf)
        # pada Surat Kerja (work_plan) yang aktif.
        return bool(await self.scalar(
            """
            SELECT EXISTS (
                SELECT 1 FROM vms.work_plan wp
                WHERE wp.deleted_at IS NULL AND wp.status NOT IN ('DRAFT', 'COMPLETED', 'CANCELLED')
                  AND (wp.pm_employee_id = :emp OR wp.leader_employee_id = :emp
                       OR EXISTS (SELECT 1 FROM vms.work_plan_member m
                                  WHERE m.work_plan_id = wp.id AND m.employee_id = :emp
                                    AND upper_inf(m.valid_period))))
            """,
            {"emp": employee_id}))

    async def offboard(self, employee_id: UUID | str, reason: str, today: Any) -> None:
        """
        Mengakhiri masa kerja karyawan (offboarding).
        Status karyawan akan dinonaktifkan, jabatan terbukanya ditutup per hari ini, dan
        akun aplikasinya akan dicabut/dinonaktifkan.

        Args:
            employee_id (UUID | str): ID karyawan.
            reason (str): Alasan pemberhentian.
            today (Any): Tanggal (hari ini) untuk menutup penempatan.
        """
        # Menonaktifkan karyawan di tabel utama beserta mencatat alasan dan waktu offboarding
        await self.execute(
            """
            UPDATE vms.employee SET is_active = false, offboarded_at = now(), offboarding_reason = :reason,
                   updated_at = now()
             WHERE id = :id
            """,
            {"id": employee_id, "reason": reason})
        # Menutup periode validitas dari riwayat penempatan (assignment) yang terbuka
        await self.execute(
            """
            UPDATE vms.employee_assignment SET valid_to = GREATEST(valid_from, CAST(:today AS date))
             WHERE employee_id = :id AND valid_to IS NULL
            """,
            {"id": employee_id, "today": today})
        # Menonaktifkan akses akun karyawan di tabel app_user
        await self.execute("UPDATE vms.app_user SET is_active = false WHERE employee_id = :id", {"id": employee_id})

    _COLUMNS = """id, employee_no, full_name, position, unit_id, email, phone, join_date, birth_date, address,
                  emergency_contact, attendance_mode, is_active, offboarded_at, offboarding_reason, photo_file_id"""

    @staticmethod
    def _list_filter(is_active: bool | None, q: str | None) -> tuple[str, dict[str, Any]]:
        # Karyawan terhapus disembunyikan (V-29).
        where = ["organization_id = :org", "deleted_at IS NULL"]
        params: dict[str, Any] = {}
        if is_active is not None:
            where.append("is_active = :is_active")
            params["is_active"] = is_active
        if q:
            where.append("(full_name ILIKE :q OR employee_no ILIKE :q)")
            params["q"] = f"%{q}%"
        return " AND ".join(where), params

    async def count_in_org(self, org_id: UUID | str, is_active: bool | None, q: str | None) -> int:
        """Jumlah karyawan (belum terhapus) sesuai filter."""
        where, params = self._list_filter(is_active, q)
        row = await self.fetchone(f"SELECT COUNT(*) AS n FROM vms.employee WHERE {where}", {"org": org_id, **params})
        return int(row.n) if row else 0

    async def page_in_org(self, org_id: UUID | str, is_active: bool | None, q: str | None,
                          limit: int, offset: int) -> list[Any]:
        """Satu halaman karyawan, urut nama."""
        where, params = self._list_filter(is_active, q)
        return list(await self.fetchall(
            f"SELECT {self._COLUMNS} FROM vms.employee WHERE {where} ORDER BY full_name ASC LIMIT :limit OFFSET :offset",
            {"org": org_id, "limit": limit, "offset": offset, **params}))

    async def get_in_org(self, employee_id: UUID | str, org_id: UUID | str) -> Any:
        """Satu karyawan organisasi ini yang belum terhapus, atau None."""
        return await self.fetchone(
            f"SELECT {self._COLUMNS} FROM vms.employee WHERE id = :id AND organization_id = :org AND deleted_at IS NULL",
            {"id": employee_id, "org": org_id})

    async def insert(self, org_id: UUID | str, data: dict[str, Any]) -> Any:
        """Karyawan baru + penempatan perdana. → (id, is_active, offboarded_at, offboarding_reason, attendance_mode, photo_file_id)."""
        params = {
            "attendance_mode": data.get("attendance_mode", "FIELD"),
            "photo_file_id": data.get("photo_file_id"),
            **data,
            "org": org_id,
        }
        row = await self.fetchone(
            """
            INSERT INTO vms.employee (organization_id, employee_no, full_name, position, unit_id, email, phone,
                                      join_date, birth_date, address, emergency_contact, attendance_mode, photo_file_id)
            VALUES (:org, :employee_no, :full_name, :position, :unit_id, :email, :phone, :join_date, :birth_date,
                    :address, :emergency_contact, :attendance_mode, :photo_file_id)
            RETURNING id, is_active, offboarded_at, offboarding_reason, attendance_mode, photo_file_id
            """,
            params)
        await self.execute(
            """
            INSERT INTO vms.employee_assignment (employee_id, position, unit_id, valid_from)
            VALUES (:emp_id, :position, :unit_id, :join_date)
            """,
            {"emp_id": row.id, "position": data["position"], "unit_id": data["unit_id"],
             "join_date": data["join_date"]})
        return row

    async def update_fields(self, employee_id: UUID | str, org_id: UUID | str, fields: dict[str, Any]) -> Any:
        """Ubah kolom data pribadi (nama kolom dari skema EmployeeUpdate, bukan dari klien). → baris atau None."""
        assignments = ", ".join(f"{name} = :{name}" for name in fields)
        return await self.fetchone(
            f"UPDATE vms.employee SET {assignments} WHERE id = :id AND organization_id = :org "
            f"RETURNING {self._COLUMNS}",
            {"id": employee_id, "org": org_id, **fields})

    async def conflicts(self, employee_id: UUID | str, start: Any, end: Any, exclude_plan: UUID | str | None) -> list[Any]:
        """SK lain yang bentrok jadwal dengan rentang ini (P3-6, fungsi `personnel_conflict`)."""
        return list(await self.fetchall(
            "SELECT work_plan_id, number, title FROM vms.personnel_conflict(:emp, daterange(:start, :end, '[]'), :exclude)",
            {"emp": employee_id, "start": start, "end": end, "exclude": exclude_plan}))
