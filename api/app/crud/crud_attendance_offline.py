"""
app/crud/crud_attendance_offline.py
Absensi lapangan luring (R-34): kunci publik perangkat, jejak peristiwa luring (idempoten), dan
penulisan absen masuk/pulang pada jam peristiwa (bukan jam terima). SQL ditulis utuh (V-01).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDAttendanceOffline(CRUDBase):
    """
    Kelas operasi CRUD untuk menangani absensi luring (offline).
    Menyediakan fungsionalitas untuk manajemen kunci perangkat dan sinkronisasi peristiwa luring.
    """

    async def device_key(self, user_id: UUID | str, device_id: str) -> Any:
        """
        Mengambil kunci publik (public key) aktif untuk perangkat pengguna tertentu.

        Args:
            user_id (UUID | str): ID pengguna.
            device_id (str): ID perangkat yang digunakan.

        Returns:
            Any: Kunci publik perangkat, atau None jika tidak ada yang aktif.
        """
        # Mengambil kunci publik (public_key) yang belum dicabut (revoked_at IS NULL)
        return await self.scalar(
            """
            SELECT public_key FROM vms.attendance_device_key
            WHERE user_id = CAST(:user AS uuid) AND device_id = :device AND revoked_at IS NULL
            """,
            {"user": str(user_id), "device": device_id},
        )

    async def register_device_key(self, org_id: UUID | str, user_id: UUID | str, device_id: str,
                                  public_key: str) -> None:
        """
        Mendaftarkan kunci publik baru untuk perangkat pengguna.
        Kunci publik yang sebelumnya aktif akan dicabut (revoked) tanpa dihapus untuk mempertahankan jejak audit.

        Args:
            org_id (UUID | str): ID organisasi.
            user_id (UUID | str): ID pengguna.
            device_id (str): ID perangkat.
            public_key (str): Kunci publik baru yang akan didaftarkan.
        """
        # Mencabut (revoke) kunci lama yang masih aktif dengan mengubah nilai revoked_at menjadi waktu saat ini
        await self.execute(
            """
            UPDATE vms.attendance_device_key SET revoked_at = now()
            WHERE user_id = CAST(:user AS uuid) AND device_id = :device AND revoked_at IS NULL
              AND public_key <> :key
            """,
            {"user": str(user_id), "device": device_id, "key": public_key},
        )
        # Menambahkan kunci publik baru hanya jika belum ada kunci aktif untuk perangkat tersebut
        await self.execute(
            """
            INSERT INTO vms.attendance_device_key (organization_id, user_id, device_id, public_key)
            SELECT CAST(:org AS uuid), CAST(:user AS uuid), :device, :key
            WHERE NOT EXISTS (SELECT 1 FROM vms.attendance_device_key
                              WHERE user_id = CAST(:user AS uuid) AND device_id = :device
                                AND revoked_at IS NULL)
            """,
            {"org": str(org_id), "user": str(user_id), "device": device_id, "key": public_key},
        )

    async def event(self, client_op_id: UUID | str) -> Any:
        """
        Mengambil data peristiwa sinkronisasi absensi luring berdasarkan ID operasi klien,
        digunakan untuk memastikan idempotensi (menghindari duplikasi pengiriman).

        Args:
            client_op_id (UUID | str): ID operasi dari klien (aplikasi).

        Returns:
            Any: Data peristiwa (event) jika sudah pernah diproses.
        """
        # Mencari apakah peristiwa (event) dengan ID operasi tersebut sudah tercatat di tabel
        return await self.fetchone(
            """
            SELECT client_op_id, user_id, kind, attendance_id, result
            FROM vms.attendance_offline_event WHERE client_op_id = CAST(:op AS uuid)
            """,
            {"op": str(client_op_id)},
        )

    async def record_event(self, *, client_op_id: UUID | str, org_id: UUID | str, user_id: UUID | str,
                           kind: str, attendance_id: Any, event_time: datetime, time_trusted: bool,
                           result: str) -> None:
        """
        Mencatat peristiwa (event) absensi luring ke dalam log database.

        Args:
            client_op_id (UUID | str): ID operasi dari klien.
            org_id (UUID | str): ID organisasi.
            user_id (UUID | str): ID pengguna.
            kind (str): Jenis peristiwa.
            attendance_id (Any): ID absensi terkait.
            event_time (datetime): Waktu terjadinya peristiwa di perangkat klien.
            time_trusted (bool): Apakah waktu perangkat dapat dipercaya (tidak dimanipulasi).
            result (str): Hasil pemrosesan peristiwa.
        """
        # Memasukkan catatan audit terkait peristiwa sinkronisasi luring
        await self.execute(
            """
            INSERT INTO vms.attendance_offline_event
                (client_op_id, organization_id, user_id, kind, attendance_id, event_time, time_trusted, result)
            VALUES (CAST(:op AS uuid), CAST(:org AS uuid), CAST(:user AS uuid), :kind, CAST(:att AS uuid),
                    :at, :trusted, :result)
            """,
            {"op": str(client_op_id), "org": str(org_id), "user": str(user_id), "kind": kind,
             "att": str(attendance_id) if attendance_id else None, "at": event_time,
             "trusted": time_trusted, "result": result},
        )

    async def file_sha256(self, file_id: UUID | str, org_id: UUID | str) -> Any:
        """
        Mendapatkan nilai hash SHA-256 (format hex) dari sebuah file objek (misalnya swafoto luring)
        untuk keperluan verifikasi integritas data.

        Args:
            file_id (UUID | str): ID file.
            org_id (UUID | str): ID organisasi.

        Returns:
            Any: String hash SHA-256 dari file.
        """
        # Mengambil nilai hash sha256 yang disandikan dengan format heksadesimal
        return await self.scalar(
            "SELECT encode(sha256, 'hex') FROM vms.file_object WHERE id = CAST(:id AS uuid) "
            "AND organization_id = CAST(:org AS uuid)",
            {"id": str(file_id), "org": str(org_id)},
        )

    async def local_date(self, org_id: UUID | str, at: datetime) -> Any:
        """
        Menghitung tanggal kerja (work date) berdasarkan zona waktu lokal organisasi.

        Args:
            org_id (UUID | str): ID organisasi.
            at (datetime): Waktu kejadian (UTC).

        Returns:
            Any: Objek tanggal (date) lokal organisasi.
        """
        # Mengubah timestamp ke zona waktu organisasi (TIME ZONE o.timezone) lalu mengambil tanggalnya
        return await self.scalar(
            "SELECT (CAST(:at AS timestamptz) AT TIME ZONE o.timezone)::date FROM vms.organization o "
            "WHERE o.id = CAST(:org AS uuid)",
            {"at": at, "org": str(org_id)},
        )

    async def mark_offline(self, attendance_id: UUID | str, note: str | None, force_review: bool) -> Any:
        """
        Menandai sebuah catatan absensi sebagai absensi luring (offline) beserta alasan teknisnya.
        Jika force_review bernilai True dan statusnya otomatis valid,
        maka status akan diturunkan menjadi 'NEEDS_REVIEW'.

        Args:
            attendance_id (UUID | str): ID absensi.
            note (str | None): Catatan/alasan status luring (misalnya waktu tak terverifikasi, dll).
            force_review (bool): Apakah harus memaksa peninjauan ulang (review).

        Returns:
            Any: Data absensi yang telah diperbarui.
        """
        # Memperbarui data absensi, mengubah kolom offline menjadi true dan menyisipkan catatan luring.
        # Menurunkan status menjadi 'NEEDS_REVIEW' jika absensi luring memiliki masalah verifikasi waktu/lokasi
        return await self.fetchone(
            """
            UPDATE vms.attendance
            SET offline = true, offline_note = NULLIF(concat_ws('; ', offline_note, CAST(:note AS text)), ''),
                status = CASE WHEN :force AND status = 'AUTO_VALID'
                              THEN CAST('NEEDS_REVIEW' AS vms.attendance_status) ELSE status END
            WHERE id = CAST(:id AS uuid)
            RETURNING id, employee_id, work_date, site_id, site_label, check_in_at, check_out_at,
                      distance_m, is_late, is_early_leave, status, explanation, reviewed_at, selfie_file_id
            """,
            {"id": str(attendance_id), "note": note, "force": force_review},
        )

    async def open_before(self, employee_id: UUID | str, at: datetime) -> Any:
        """
        Mencari sesi absensi masuk (check-in) terakhir yang belum ditutup (belum ada check-out)
        dan belum ditolak, sebelum suatu waktu tertentu.
        Digunakan untuk memasangkan check-out luring dengan check-in yang sesuai.

        Args:
            employee_id (UUID | str): ID karyawan.
            at (datetime): Batas waktu pencarian.

        Returns:
            Any: Data absensi yang ditemukan (jika ada).
        """
        # Mencari satu baris absensi yang masih terbuka (check_out_at IS NULL),
        # belum ada permintaan check-out, tidak ditolak, dan waktu check-in terjadi sebelum parameter 'at'
        return await self.fetchone(
            """
            SELECT id, status, check_in_at FROM vms.attendance
            WHERE employee_id = CAST(:emp AS uuid) AND check_out_at IS NULL AND status <> 'REJECTED'
              AND check_out_requested_at IS NULL AND check_in_at <= :at
            ORDER BY check_in_at DESC LIMIT 1
            """,
            {"emp": str(employee_id), "at": at},
        )

    async def close_at(self, attendance_id: UUID | str, at: datetime, *, lat: float | None = None,
                       lng: float | None = None) -> None:
        """
        Menutup sesi absensi dengan menetapkan waktu check-out ke waktu spesifik
        (bukan waktu saat ini).

        Args:
            attendance_id (UUID | str): ID absensi.
            at (datetime): Waktu check-out.
        """
        # Memperbarui kolom check_out_at dengan waktu yang ditentukan dari klien (saat luring)
        # Absen luring sudah terjadi: tidak ditolak karena swafoto/penjelasan kurang (trigger T7 hanya menandai).
        await self.execute("SELECT set_config('app.relax_checkout', 'on', true)")
        await self.execute(
            "UPDATE vms.attendance SET check_out_at = :at, "
            "check_out_location = CASE WHEN CAST(:lat AS float8) IS NULL THEN NULL "
            "ELSE ST_SetSRID(ST_MakePoint(CAST(:lng AS float8), CAST(:lat AS float8)), 4326)::geography END "
            "WHERE id = CAST(:id AS uuid)",
            {"at": at, "id": str(attendance_id), "lat": lat, "lng": lng})
        await self.execute("SELECT set_config('app.relax_checkout', 'off', true)")

    async def request_checkout(self, attendance_id: UUID | str, at: datetime) -> None:
        """
        Mengajukan permintaan check-out luring untuk sesi absensi yang masuknya belum divalidasi.
        Sistem akan menyetujui check-out ini setelah absen masuknya disetujui (R-34).

        Args:
            attendance_id (UUID | str): ID absensi.
            at (datetime): Waktu permintaan check-out luring.
        """
        # Menyimpan waktu permintaan check-out (check_out_requested_at) tanpa langsung memproses check-out
        await self.execute(
            "UPDATE vms.attendance SET check_out_requested_at = :at WHERE id = CAST(:id AS uuid)",
            {"at": at, "id": str(attendance_id)})
