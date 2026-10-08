"""
app/crud/crud_attendance_session.py
Sesi absensi (V-12). Jarak, radius, status, terlambat, dan pulang cepat TIDAK ditulis di sini —
trigger `attendance_geofence` / `attendance_checkout` (db/02) yang menghitungnya dari jam & lokasi
server; aplikasi hanya membaca hasilnya kembali. SQL ditulis utuh (bukan f-string) agar diperiksa V-01.

Cakupan R-33 (keputusan pemilik 2026-10-02) ada di fungsi SQL (Alembic 0015, db/02) — satu sumber aturan
untuk daftar, rekap, swafoto, dan tinjau:
- `vms.attendance_viewable(viewer, view_all, employee)`: milik sendiri; Finance & OPS (`view_all`); PM → bawahan
  lapangan di unitnya.
- `vms.attendance_can_review(viewer, employee)`: tidak pernah milik sendiri; PM → bawahan lapangan;
  Finance → pekerja kantor selain Finance; OPS → Finance.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDAttendanceSession(CRUDBase):
    """
    Kelas operasi CRUD untuk menangani data sesi absensi (check-in, check-out, daftar absensi).
    Catatan: Jarak, status, keterlambatan dihitung otomatis via trigger di sisi database.
    """

    async def employee_of(self, user_id: UUID | str) -> Any:
        """
        Mendapatkan ID karyawan berdasarkan ID pengguna (user account).

        Args:
            user_id (UUID | str): ID pengguna.

        Returns:
            Any: ID karyawan (UUID) atau None.
        """
        # Mengambil ID karyawan dari tabel app_user untuk memastikan pengguna adalah karyawan
        return await self.scalar("SELECT employee_id FROM vms.app_user WHERE id = :uid", {"uid": user_id})

    async def attendance_mode_of(self, user_id: UUID | str) -> Any:
        """
        Mengambil informasi (employee_id, attendance_mode, unit_id, is_admin) yang terkait dengan sebuah akun pengguna.
        Mengembalikan None jika akun tidak ditautkan ke profil karyawan mana pun.

        Args:
            user_id (UUID | str): ID pengguna.

        Returns:
            Any: Record (Row) yang berisi detail karyawan, atau None.
        """
        # Melakukan JOIN antara app_user dan employee untuk mengambil mode absensi dan unit
        return await self.fetchone(
            """
            SELECT e.id AS employee_id, e.attendance_mode, e.unit_id,
                   EXISTS (SELECT 1 FROM vms.user_role r WHERE r.user_id = u.id AND r.role = 'ADMIN') AS is_admin
            FROM vms.app_user u JOIN vms.employee e ON e.id = u.employee_id
            WHERE u.id = :uid
            """,
            {"uid": user_id},
        )

    async def open_session(self, employee_id: UUID | str, *, valid_only: bool = False) -> Any:
        """
        Mendapatkan sesi absensi terbaru yang masih terbuka (belum check-out dan belum ditolak),
        berlaku untuk tanggal berapa pun.
        Jika `valid_only` bernilai True, hanya sesi yang otomatis valid atau disetujui yang dikembalikan (syarat check-out R-33).

        Args:
            employee_id (UUID | str): ID karyawan.
            valid_only (bool): Jika True, memfilter hanya sesi dengan status valid/disetujui. Defaults to False.

        Returns:
            Any: Data sesi absensi terbuka, atau None jika tidak ada.
        """
        # Mencari catatan check-in terakhir (ORDER BY check_in_at DESC LIMIT 1) yang kolom check_out_at-nya masih NULL.
        # Menambahkan kondisi pengecekan status berdasarkan parameter `valid_only`.
        return await self.fetchone(
            """
            SELECT id, employee_id, work_date, site_id, site_label, check_in_at, check_out_at,
                   distance_m, is_late, is_early_leave, status, explanation, reviewed_at, selfie_file_id,
                      face_result, face_similarity, check_out_face_result, check_out_face_similarity
            FROM vms.attendance
            WHERE employee_id = :emp AND check_out_at IS NULL AND status <> 'REJECTED'
              AND (NOT CAST(:valid AS boolean) OR status IN ('AUTO_VALID', 'APPROVED'))
            ORDER BY check_in_at DESC LIMIT 1
            """,
            {"emp": employee_id, "valid": valid_only},
        )

    async def active_on(self, employee_id: UUID | str, work_date: Any) -> bool:
        """
        Mengecek apakah ada sesi absensi aktif (tidak ditolak) untuk karyawan tertentu pada tanggal kerja tertentu.

        Args:
            employee_id (UUID | str): ID karyawan.
            work_date (Any): Tanggal kerja (date).

        Returns:
            bool: True jika ada absensi aktif, False jika tidak ada.
        """
        # Memeriksa keberadaan baris (EXISTS) untuk karyawan dan tanggal terkait dengan status selain 'REJECTED'
        return bool(await self.scalar(
            """
            SELECT EXISTS (SELECT 1 FROM vms.attendance
                           WHERE employee_id = :emp AND work_date = :day AND status <> 'REJECTED')
            """,
            {"emp": employee_id, "day": work_date},
        ))

    async def rejected_on(self, employee_id: UUID | str, work_date: Any) -> int:
        """
        Menghitung jumlah pengajuan absensi yang ditolak untuk karyawan pada tanggal kerja tersebut.

        Args:
            employee_id (UUID | str): ID karyawan.
            work_date (Any): Tanggal kerja (date).

        Returns:
            int: Jumlah absensi yang ditolak.
        """
        # Menghitung baris absensi yang berstatus 'REJECTED'
        return int(await self.scalar(
            """
            SELECT count(*) FROM vms.attendance
            WHERE employee_id = :emp AND work_date = :day AND status = 'REJECTED'
            """,
            {"emp": employee_id, "day": work_date},
        ) or 0)

    async def site_for_check_in(self, site_id: UUID | str, org_id: UUID | str, lng: float, lat: float) -> Any:
        """
        Mendapatkan informasi nama lokasi, unit, jarak (dalam meter), dan radius geofence.
        Rumus jarak (ST_Distance) sama dengan yang ada di fungsi trigger database,
        digunakan sementara di API untuk memvalidasi/mewajibkan penjelasan ('explanation') jika pengguna berada di luar radius.

        Args:
            site_id (UUID | str): ID lokasi (site).
            org_id (UUID | str): ID organisasi.
            lng (float): Garis bujur (longitude) posisi karyawan.
            lat (float): Garis lintang (latitude) posisi karyawan.

        Returns:
            Any: Baris data yang berisi nama lokasi, unit_id, jarak (distance_m), dan batas radius_m.
        """
        # Menghitung jarak spasial menggunakan PostGIS (ST_Distance) dari koordinat lokasi karyawan ke titik pusat lokasi absensi
        # serta mengambil batas toleransi radius (dari site atau menggunakan nilai default organisasi)
        return await self.fetchone(
            """
            SELECT s.name, s.unit_id,
                   round(ST_Distance(ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
                                     s.location)::numeric, 1) AS distance_m,
                   COALESCE(s.radius_m, o.geofence_radius_m, 100) AS radius_m
            FROM vms.site s JOIN vms.organization o ON o.id = s.organization_id
            WHERE s.id = :site AND s.organization_id = :org AND s.deleted_at IS NULL
            """,
            {"site": site_id, "org": org_id, "lng": lng, "lat": lat},
        )

    async def insert(self, *, org_id: str, employee_id: Any, work_date: Any, site_id: UUID, site_label: str,
                     lng: float, lat: float, origin: str, selfie_file_id: UUID | None,
                     face_result: str | None, face_similarity: float | None, source: str = "MOBILE",
                     explanation: str | None = None, at: Any = None) -> Any:
        """
        Membuat (menyisipkan) rekaman absensi masuk (check-in) baru.
        Catatan: Kolom radius_m harus NOT NULL, nilainya diset sementara 0, trigger database akan menimpanya.

        Args:
            org_id (str): ID organisasi.
            employee_id (Any): ID karyawan.
            work_date (Any): Tanggal kerja.
            site_id (UUID): ID lokasi absensi.
            site_label (str): Label/nama lokasi.
            lng (float): Bujur (longitude).
            lat (float): Lintang (latitude).
            origin (str): Asal/metode koordinat lokasi.
            selfie_file_id (UUID | None): ID file foto wajah.
            face_result (str | None): Hasil pengecekan wajah (e.g., 'MATCH', 'MISMATCH').
            face_similarity (float | None): Skor kemiripan wajah.
            source (str): Sumber absensi ('MOBILE', dll). Defaults to "MOBILE".
            explanation (str | None): Catatan penjelasan keterlambatan/jarak. Defaults to None.
            at (Any | None): Waktu check-in, menggunakan now() jika None.

        Returns:
            Any: Baris data absensi yang baru dibuat (RETURNING).
        """
        # Menyisipkan row ke vms.attendance dengan membentuk titik spasial (ST_MakePoint)
        # Baris yang dimasukkan (RETURNING) akan mengembalikan hasil setelah trigger db menghitung nilai-nilai sebenarnya.
        return await self.fetchone(
            """
            INSERT INTO vms.attendance (
                organization_id, employee_id, work_date, site_id, site_label, source, check_in_at,
                location, location_origin, radius_m, selfie_file_id, face_result, face_similarity, explanation
            ) VALUES (
                :org, :emp, :day, :site, :label, CAST(:source AS vms.attendance_source),
                COALESCE(CAST(:at AS timestamptz), now()),
                ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography, :origin, 0, :selfie, :face, :sim, :exp
            )
            RETURNING id, employee_id, work_date, site_id, site_label, check_in_at, check_out_at,
                      distance_m, is_late, is_early_leave, status, explanation, reviewed_at, selfie_file_id,
                      face_result, face_similarity, check_out_face_result, check_out_face_similarity
            """,
            {"org": org_id, "emp": employee_id, "day": work_date, "site": site_id, "label": site_label,
             "lng": lng, "lat": lat, "origin": origin, "selfie": selfie_file_id,
             "face": face_result, "sim": face_similarity, "source": source, "exp": explanation, "at": at},
        )

    async def close(self, attendance_id: UUID | str, *, lat: float | None = None, lng: float | None = None,
                    selfie_file_id: UUID | None = None, explanation: str | None = None) -> Any:
        """
        Menutup sesi absensi dengan menetapkan waktu check-out ke saat ini (now()).

        Args:
            attendance_id (UUID | str): ID absensi yang ingin ditutup.

        Returns:
            Any: Baris data absensi yang telah diperbarui.
        """
        # Memperbarui kolom check_out_at dan mengembalikan seluruh data absensi (RETURNING)
        return await self.fetchone(
            """
            UPDATE vms.attendance
               SET check_out_at = now(),
                   check_out_location = CASE WHEN CAST(:lat AS float8) IS NULL THEN NULL
                       ELSE ST_SetSRID(ST_MakePoint(CAST(:lng AS float8), CAST(:lat AS float8)), 4326)::geography END,
                   check_out_selfie_file_id = CAST(:selfie AS uuid), check_out_explanation = :exp
             WHERE id = :id
            RETURNING id, employee_id, work_date, site_id, site_label, check_in_at, check_out_at,
                      distance_m, is_late, is_early_leave, status, explanation, reviewed_at, selfie_file_id,
                      face_result, face_similarity, check_out_face_result, check_out_face_similarity,
                      check_out_distance_m, check_out_outside, check_out_selfie_file_id, check_out_explanation
            """,
            {"id": attendance_id, "lat": lat, "lng": lng, "selfie": str(selfie_file_id) if selfie_file_id else None,
             "exp": explanation.strip() if explanation else None},
        )

    async def flag_missing_face(self, attendance_id: UUID | str, event: str, note: str) -> Any:
        """
        Karyawan yang sudah mendaftar wajah absen TANPA data wajah: tidak ditolak, tetapi tidak lolos otomatis —
        naik ke antrean periksa dengan catatan server (tampil sebagai "Catatan server" di web).
        """
        col = "face_result" if event == "CHECK_IN" else "check_out_face_result"
        return await self.fetchone(
            f"""
            UPDATE vms.attendance
               SET {col} = 'SKIPPED'::vms.face_check_result,
                   offline_note = NULLIF(concat_ws('; ', offline_note, CAST(:note AS text)), ''),
                   status = CASE WHEN status = 'AUTO_VALID' THEN 'NEEDS_REVIEW'::vms.attendance_status ELSE status END
             WHERE id = :id
            RETURNING id, employee_id, work_date, site_id, site_label, check_in_at, check_out_at,
                      distance_m, is_late, is_early_leave, status, explanation, reviewed_at, selfie_file_id,
                      face_result, face_similarity, check_out_face_result, check_out_face_similarity
            """,
            {"id": attendance_id, "note": note},
        )

    async def set_face(self, attendance_id: UUID | str, event: str, *, check_id: UUID | str | None, result: str,
                       similarity: float | None, flag_review: bool) -> Any:
        """
        Menyimpan hasil pengenalan wajah (hitungan server) pada absen masuk atau pulang.
        `flag_review`: hasil bermasalah (NO_MATCH/LOW_QUALITY) menaikkan absensi ke antrean periksa —
        wajah tidak pernah menolak diam-diam, tetapi tidak juga lolos otomatis (docs/08 §6).
        """
        cols = ("face_check_id = :cid, face_result = CAST(:res AS vms.face_check_result), face_similarity = :sim"
                if event == "CHECK_IN" else
                "check_out_face_check_id = :cid, check_out_face_result = CAST(:res AS vms.face_check_result), "
                "check_out_face_similarity = :sim")
        review = ", status = CASE WHEN status = 'AUTO_VALID' THEN 'NEEDS_REVIEW'::vms.attendance_status ELSE status END"             if flag_review else ""
        return await self.fetchone(
            f"""
            UPDATE vms.attendance SET {cols}{review} WHERE id = :id
            RETURNING id, employee_id, work_date, site_id, site_label, check_in_at, check_out_at,
                      distance_m, is_late, is_early_leave, status, explanation, reviewed_at, selfie_file_id,
                      face_result, face_similarity, check_out_face_result, check_out_face_similarity
            """,
            {"id": attendance_id, "cid": check_id, "res": result, "sim": similarity},
        )

    async def get(self, attendance_id: UUID | str, org_id: UUID | str) -> Any:
        """
        Mengambil satu rekaman absensi berdasarkan ID dan ID organisasi.
        Catatan: Menggunakan 'FOR UPDATE' sehingga mengunci baris ini untuk mencegah race condition
        selama proses pembaruan data absensi.

        Args:
            attendance_id (UUID | str): ID absensi.
            org_id (UUID | str): ID organisasi.

        Returns:
            Any: Data absensi yang diminta dan telah dikunci.
        """
        # Mengambil dan mengunci baris data (FOR UPDATE) agar tidak dimodifikasi oleh transaksi lain
        return await self.fetchone(
            """
            SELECT id, employee_id, work_date, site_id, site_label, check_in_at, check_out_at,
                   distance_m, is_late, is_early_leave, status, explanation, reviewed_at, selfie_file_id,
                      face_result, face_similarity, check_out_face_result, check_out_face_similarity
            FROM vms.attendance WHERE id = :id AND organization_id = :org
            FOR UPDATE
            """,
            {"id": attendance_id, "org": org_id},
        )

    async def can_review(self, viewer_user_id: UUID | str, employee_id: UUID | str) -> bool:
        """
        Mengecek apakah seorang pengguna (viewer) memiliki hak untuk meninjau (review)
        absensi seorang karyawan.

        Args:
            viewer_user_id (UUID | str): ID pengguna yang melihat.
            employee_id (UUID | str): ID karyawan yang absensinya dilihat.

        Returns:
            bool: True jika pengguna boleh melakukan peninjauan.
        """
        # Memanggil fungsi database kustom vms.attendance_can_review untuk mengevaluasi hak peninjauan
        return bool(await self.scalar(
            "SELECT vms.attendance_can_review(CAST(:viewer AS uuid), CAST(:emp AS uuid))",
            {"viewer": str(viewer_user_id), "emp": str(employee_id)},
        ))

    async def list_page(self, org_id: str, viewer_user_id: str, *, view_all: bool, employee_id: Any,
                        date_from: Any, date_to: Any, status: str | None,
                        limit: int, offset: int, scope: str = "all") -> tuple[list[Any], int]:
        """
        Mengambil daftar absensi dengan pembagian halaman (pagination) berdasarkan izin pengguna.
        Hanya mengembalikan absensi yang boleh dilihat oleh pengguna (R-33).

        Args:
            org_id (str): ID organisasi.
            viewer_user_id (str): ID pengguna yang meminta data.
            view_all (bool): Apakah pengguna memiliki akses untuk melihat semua (e.g. role Finance/OPS).
            employee_id (Any): Filter berdasarkan ID karyawan spesifik.
            date_from (Any): Filter dari tanggal (awal).
            date_to (Any): Filter sampai tanggal (akhir).
            status (str | None): Filter berdasarkan status absensi (misal 'NEEDS_REVIEW').
            scope (str): `all` (semua yang boleh dilihat), `mine` (absensi pribadi), `team` (selain milik sendiri:
                anggota/umum). Memisahkan absensi pribadi dari absensi orang lain untuk PM/Finance/OPS.
            limit (int): Jumlah maksimum hasil (pagination).
            offset (int): Titik mulai (offset) untuk pagination.

        Returns:
            tuple[list[Any], int]: Tuple yang berisi daftar baris (rows) absensi dan jumlah total data (total count).
        """
        params = {"org": org_id, "viewer": viewer_user_id, "view_all": view_all, "emp": employee_id,
                  "date_from": date_from, "date_to": date_to, "status": status, "scope": scope,
                  "limit": limit, "offset": offset}
        # Mengambil baris absensi. Join dengan employee untuk mendapat nama.
        # Menggunakan vms.attendance_viewable di WHERE agar hanya menampilkan yang memiliki hak akses.
        # Menggunakan vms.attendance_can_review untuk menentukan flag 'can_review' per baris.
        rows = await self.fetchall(
            """
            SELECT a.id, a.employee_id, a.work_date, a.site_id, a.site_label, a.check_in_at, a.check_out_at,
                   a.distance_m, a.is_late, a.is_early_leave, a.status, a.explanation, a.reviewed_at,
                   a.selfie_file_id, a.review_note, e.full_name AS employee_name,
                   a.face_result, a.face_similarity, a.check_out_face_result, a.check_out_face_similarity,
                   a.offline, a.offline_note, a.check_out_requested_at,
                   a.check_out_distance_m, a.check_out_outside, a.check_out_selfie_file_id, a.check_out_explanation,
                   vms.attendance_city_category(a.employee_id, a.work_date) AS city_category,
                   vms.attendance_can_review(CAST(:viewer AS uuid), a.employee_id) AS can_review
            FROM vms.attendance a JOIN vms.employee e ON e.id = a.employee_id
            WHERE a.organization_id = CAST(:org AS uuid)
              AND vms.attendance_viewable(CAST(:viewer AS uuid), CAST(:view_all AS boolean), a.employee_id)
              AND (CAST(:emp AS uuid) IS NULL OR a.employee_id = CAST(:emp AS uuid))
              AND (CAST(:scope AS text) = 'all'
                   OR (CAST(:scope AS text) = 'mine' AND a.employee_id IS NOT DISTINCT FROM
                       (SELECT u.employee_id FROM vms.app_user u WHERE u.id = CAST(:viewer AS uuid)))
                   OR (CAST(:scope AS text) = 'team' AND a.employee_id IS DISTINCT FROM
                       (SELECT u.employee_id FROM vms.app_user u WHERE u.id = CAST(:viewer AS uuid))))
              AND (CAST(:date_from AS date) IS NULL OR a.work_date >= CAST(:date_from AS date))
              AND (CAST(:date_to AS date) IS NULL OR a.work_date <= CAST(:date_to AS date))
              AND (CAST(:status AS text) IS NULL OR CAST(a.status AS text) = CAST(:status AS text))
            ORDER BY a.work_date DESC, a.check_in_at DESC
            LIMIT :limit OFFSET :offset
            """,
            params,
        )
        # Menghitung total seluruh data absensi (count(*)) yang sesuai dengan filter (untuk pagination metadata)
        total = await self.scalar(
            """
            SELECT count(*) FROM vms.attendance a
            WHERE a.organization_id = CAST(:org AS uuid)
              AND vms.attendance_viewable(CAST(:viewer AS uuid), CAST(:view_all AS boolean), a.employee_id)
              AND (CAST(:emp AS uuid) IS NULL OR a.employee_id = CAST(:emp AS uuid))
              AND (CAST(:scope AS text) = 'all'
                   OR (CAST(:scope AS text) = 'mine' AND a.employee_id IS NOT DISTINCT FROM
                       (SELECT u.employee_id FROM vms.app_user u WHERE u.id = CAST(:viewer AS uuid)))
                   OR (CAST(:scope AS text) = 'team' AND a.employee_id IS DISTINCT FROM
                       (SELECT u.employee_id FROM vms.app_user u WHERE u.id = CAST(:viewer AS uuid))))
              AND (CAST(:date_from AS date) IS NULL OR a.work_date >= CAST(:date_from AS date))
              AND (CAST(:date_to AS date) IS NULL OR a.work_date <= CAST(:date_to AS date))
              AND (CAST(:status AS text) IS NULL OR CAST(a.status AS text) = CAST(:status AS text))
            """,
            params,
        )
        return list(rows), int(total or 0)

    async def set_explanation(self, attendance_id: UUID | str, explanation: str) -> None:
        """
        Menambahkan penjelasan (alasan) keterlambatan atau absen di luar lokasi.

        Args:
            attendance_id (UUID | str): ID absensi.
            explanation (str): Penjelasan/keterangan yang diberikan pengguna.
        """
        # Memperbarui kolom explanation pada rekaman absensi
        await self.execute("UPDATE vms.attendance SET explanation = :exp WHERE id = :id",
                           {"exp": explanation, "id": attendance_id})

    async def set_review(self, attendance_id: UUID | str, status: str, reviewer: Any, note: str) -> None:
        """
        Menyimpan hasil peninjauan absensi (misalnya APPROVED, REJECTED) oleh atasan atau tim terkait.
        Juga menangani persetujuan otomatis untuk check-out luring yang tertunda (R-34).

        Args:
            attendance_id (UUID | str): ID absensi.
            status (str): Status peninjauan yang baru.
            reviewer (Any): ID karyawan yang melakukan peninjauan.
            note (str): Catatan atau alasan peninjauan.
        """
        # Memperbarui status absensi, mengisi reviewer, waktu, dan catatan review.
        # Bila status diubah menjadi 'APPROVED' dan absensi belum punya jam check-out,
        # maka waktu check-out diisi dari waktu permintaan luring (check_out_requested_at).
        await self.execute(
            """
            UPDATE vms.attendance
            SET status = CAST(:status AS vms.attendance_status), reviewed_by = :emp, reviewed_at = now(),
                review_note = :note,
                -- R-34: absen pulang luring yang menunggu absen masuk disetujui → berlaku saat disetujui.
                check_out_at = CASE WHEN CAST(:status AS text) = 'APPROVED' AND check_out_at IS NULL
                                    THEN check_out_requested_at ELSE check_out_at END
            WHERE id = :id
            """,
            {"status": status, "emp": reviewer, "note": note, "id": attendance_id},
        )

    async def export_rows(self, org_id: UUID | str, start: Any, end: Any) -> list[Any]:
        """Baris ekspor Finance (P4-5): jam dalam zona waktu organisasi, urut tanggal lalu nama."""
        return list(await self.fetchall(
            """
            SELECT a.work_date, e.employee_no, e.full_name, a.site_label,
                   to_char(a.check_in_at AT TIME ZONE o.timezone, 'HH24:MI:SS') AS check_in,
                   to_char(a.check_out_at AT TIME ZONE o.timezone, 'HH24:MI:SS') AS check_out,
                   a.status, a.is_late, a.is_early_leave, a.check_out_distance_m, a.check_out_outside,
                   vms.attendance_city_category(a.employee_id, a.work_date) AS city_category
              FROM vms.attendance a
              JOIN vms.employee e ON a.employee_id = e.id
              JOIN vms.organization o ON o.id = a.organization_id
             WHERE a.organization_id = :org
               AND a.work_date BETWEEN :start AND :end
             ORDER BY a.work_date ASC, e.full_name ASC
            """,
            {"org": org_id, "start": start, "end": end}))
