"""
app/modules/attendance/repositories/attendance_session_repository.py
Sesi absensi VMS Master Schema V2.
Mendukung validasi koordinat GPS (Haversine), radius toleransi, validasi wajah,
status persetujuan OM ('AUTO_VALID', 'PENDING_OM', 'APPROVED_BY_OM', 'REJECTED_BY_OM'),
zona kota (DALAM_KOTA / LUAR_KOTA), dan kalkulasi uang makan.
"""

from __future__ import annotations

import math
from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository, escape_like
from app.shared.access.pm_reach import VIEWER_EMPLOYEE_BY_USER, pm_reaches_employee
from app.shared.attendance_sql import IS_LATE, IS_LATE_A


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    """Menghitung jarak dalam meter antara dua koordinat GPS menggunakan formula Haversine."""
    r = 6371000  # radius bumi dalam meter
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(r * c)


def _pm_reach(emp_expr: str) -> str:
    """PM peninjau (:viewer) berwenang atas karyawan `emp_expr`: divisinya, atau tim pada jadwal/proyek yang
    dikelolanya (lihat `app/shared/access/pm_reach.py`). Dipakai bersama `reviewer_employee_ids`."""
    return pm_reaches_employee(VIEWER_EMPLOYEE_BY_USER, emp_expr)


class AttendanceSessionRepository(BaseRepository):
    """Repositori sesi absensi (tabel attendance)."""
    """
    Kelas operasi CRUD untuk menangani data sesi absensi Master Schema V2.
    """

    async def employee_of(self, user_id: UUID | str) -> Any:
        """Mendapatkan ID karyawan berdasarkan ID pengguna (users)."""
        return await self.scalar(
            "SELECT employee_id FROM users WHERE user_id = CAST(:uid AS uuid) AND delete_at IS NULL",
            {"uid": str(user_id)},
        )

    async def attendance_mode_of(self, user_id: UUID | str) -> Any:
        """
        Karyawan milik akun + jenis pekerjanya menurut peran (docs/35 §1): peran kantor absen lewat web
        (OFFICE), peran lapangan lewat aplikasi HP (FIELD). SUPER_ADMIN boleh dari keduanya.
        """
        return await self.fetchone(
            """
            SELECT e.employee_id,
                   CASE WHEN u.system_role IN ('TEAM_LEADER', 'EMPLOYEE') THEN 'FIELD' ELSE 'OFFICE' END
                       AS attendance_mode,
                   e.division_id AS unit_id,
                   (u.system_role = 'SUPER_ADMIN') AS is_admin
            FROM users u
            JOIN employee e ON e.employee_id = u.employee_id
            WHERE u.user_id = CAST(:uid AS uuid)
              AND u.delete_at IS NULL
              AND e.delete_at IS NULL
            """,
            {"uid": str(user_id)},
        )

    async def open_session(self, employee_id: UUID | str, *, valid_only: bool = False) -> Any:
        """
        Mendapatkan sesi absensi terbaru yang belum check-out.
        """
        return await self.fetchone(
            f"""
            SELECT a.attendance_id AS id,
                   a.employee_id,
                   a.office_id AS organization_id,
                   a.attendance_date AS work_date,
                   COALESCE(a.daily_plan_id, a.office_id) AS site_id,
                   COALESCE(wpd.site_name, o.name, 'Lokasi Kerja') AS site_label,
                   a.clock_in_at AS check_in_at,
                   a.clock_out_at AS check_out_at,
                   a.distance_to_target_m::float AS distance_m,
                   ({IS_LATE_A}) AS is_late,
                   (a.clock_out_at IS NOT NULL
                    AND (a.clock_out_at AT TIME ZONE 'Asia/Jakarta')::time < a.scheduled_out) AS is_early_leave,
                   CASE
                       WHEN a.om_approval_status = 'AUTO_VALID' THEN 'AUTO_VALID'
                       WHEN a.om_approval_status = 'APPROVED_BY_OM' THEN 'APPROVED'
                       WHEN a.om_approval_status = 'REJECTED_BY_OM' THEN 'REJECTED'
                       ELSE 'NEEDS_REVIEW'
                   END AS status,
                   a.out_of_radius_note AS explanation,
                   a.update_at AS reviewed_at,
                   (SELECT f.id FROM file_object f WHERE f.storage_key = a.face_photo_path LIMIT 1)
                       AS selfie_file_id,
                   CASE WHEN a.face_match_score = 0 THEN 'SKIPPED' WHEN a.face_match_score >= 80.0 THEN 'MATCH'
                           ELSE 'MISMATCH' END AS face_result,
                   (a.face_match_score / 100.0)::float AS face_similarity,
                   NULL::text AS check_out_face_result,
                   NULL::float AS check_out_face_similarity
            FROM attendance a
            LEFT JOIN office o ON o.office_id = a.office_id
            LEFT JOIN work_plan_daily wpd ON wpd.daily_plan_id = a.daily_plan_id
            WHERE a.employee_id = CAST(:emp AS uuid)
              AND a.clock_out_at IS NULL
              AND a.om_approval_status <> 'REJECTED_BY_OM'
              AND (NOT CAST(:valid AS boolean) OR a.om_approval_status IN ('AUTO_VALID', 'APPROVED_BY_OM'))
              AND a.delete_at IS NULL
            ORDER BY a.clock_in_at DESC LIMIT 1
            """,
            {"emp": str(employee_id), "valid": valid_only},
        )

    async def open_hint(self, employee_id: UUID | str) -> Any:
        """Sesi terbuka terbaru: jam masuk, jam pulang kantor, dan status terlambat (untuk pengingat pulang)."""
        return await self.fetchone(
            f"""
            SELECT a.clock_in_at, a.scheduled_out, ({IS_LATE_A}) AS is_late
            FROM attendance a
            WHERE a.employee_id = CAST(:emp AS uuid) AND a.clock_out_at IS NULL AND a.delete_at IS NULL
              AND a.om_approval_status <> 'REJECTED_BY_OM'
            ORDER BY a.clock_in_at DESC LIMIT 1
            """,
            {"emp": str(employee_id)},
        )

    async def unreported_items(self, employee_id: UUID | str, work_date: Any) -> Any:
        """Tugas hari ini yang ditugaskan ke karyawan tetapi progresnya belum diperbarui hari ini."""
        return await self.fetchone(
            """
            SELECT count(*)::int AS n, (array_agg(w.daily_plan_id))[1] AS plan_id
            FROM work_plan_item i
            JOIN work_plan_daily w ON w.daily_plan_id = i.daily_plan_id
            WHERE w.work_date = :d AND w.status IN ('APPROVED', 'ONGOING') AND w.delete_at IS NULL
              AND i.delete_at IS NULL AND i.status IN ('TODO', 'IN_PROGRESS')
              AND i.assigned_employee_ids @> to_jsonb(CAST(:emp AS text))
              AND (i.update_at AT TIME ZONE 'Asia/Jakarta')::date <> :d
            """,
            {"d": work_date, "emp": str(employee_id)},
        )

    async def auto_checkout_unclosed(
        self,
        org_id: UUID | str,
        work_date: Any,
        close_time: Any,
        explanation: str,
    ) -> list[Any]:
        """Menutup otomatis sesi absensi yang belum ditutup pada jam penutupan harian.

        Jam pulang = jam tutup pada TANGGAL ABSEN itu sendiri (WIB), bukan hari ini: sesi lupa ditutup
        sejak kemarin tidak boleh tercatat bekerja puluhan jam."""
        return list(
            await self.fetchall(
                """
                UPDATE attendance
                   SET clock_out_at = (attendance_date + CAST(:close_clock AS time)) AT TIME ZONE 'Asia/Jakarta',
                       out_of_radius_note = COALESCE(out_of_radius_note || '; ', '') || :explanation,
                       update_at = NOW()
                 WHERE (NULLIF(:org, '') IS NULL OR office_id = CAST(NULLIF(:org, '') AS uuid))
                   AND attendance_date <= :work_date
                   AND clock_in_at IS NOT NULL
                   AND clock_out_at IS NULL
                   AND om_approval_status <> 'REJECTED_BY_OM'
                   AND delete_at IS NULL
                RETURNING attendance_id AS id, employee_id, 'Kantor' AS site_label
                """,
                {"org": str(org_id), "work_date": work_date, "close_clock": close_time, "explanation": explanation},
            )
        )

    async def file_uploader(self, file_id: UUID | str) -> Any:
        """Akun pengunggah berkas (None bila tidak tercatat)."""
        row = await self.fetchone(
            "SELECT uploaded_by FROM file_object WHERE id = CAST(:id AS uuid)", {"id": str(file_id)}
        )
        return row.uploaded_by if row else None

    async def lock_employee(self, employee_id: UUID | str) -> None:
        """Kunci per karyawan sampai transaksi selesai: dua absen masuk bersamaan (ketuk ganda, sinkron
        offline + online) diproses berurutan sehingga cek "sudah absen" tidak terlewati."""
        await self.execute("SELECT pg_advisory_xact_lock(hashtext(:emp))", {"emp": f"attendance:{employee_id}"})

    async def active_on(self, employee_id: UUID | str, work_date: Any) -> bool:
        """Mengecek apakah ada sesi absensi aktif untuk karyawan tertentu pada tanggal tersebut."""
        return bool(
            await self.scalar(
                """
                SELECT EXISTS (
                    SELECT 1 FROM attendance
                    WHERE employee_id = CAST(:emp AS uuid)
                      AND attendance_date = :day
                      AND om_approval_status <> 'REJECTED_BY_OM'
                      AND delete_at IS NULL
                )
                """,
                {"emp": str(employee_id), "day": work_date},
            )
        )

    async def rejected_on(self, employee_id: UUID | str, work_date: Any) -> int:
        """Menghitung jumlah absensi yang ditolak untuk karyawan pada tanggal kerja tersebut."""
        return int(
            await self.scalar(
                """
                SELECT count(*) FROM attendance
                WHERE employee_id = CAST(:emp AS uuid)
                  AND attendance_date = :day
                  AND om_approval_status = 'REJECTED_BY_OM'
                  AND delete_at IS NULL
                """,
                {"emp": str(employee_id), "day": work_date},
            )
            or 0
        )

    async def site_for_check_in(self, site_id: UUID | str, org_id: UUID | str, lng: float, lat: float) -> Any:
        """Target absen (docs/35 §5): kantor (`office`) atau lokasi tugas harian (`work_plan_daily`) beserta jaraknya,
        radius presensi, dan jam kerja terjadwalnya. `office_id` NULL untuk lokasi tugas (diisi kantor karyawan)."""
        return await self.fetchone(
            """
            SELECT o.office_id AS id,
                   o.name,
                   NULL::uuid AS unit_id,
                   'OFFICE' AS kind,
                   o.office_id,
                   ROUND(
                       6371000 * 2 * ASIN(
                           SQRT(
                               POWER(SIN(RADIANS(:lat - o.latitude) / 2), 2) +
                               COS(RADIANS(:lat)) * COS(RADIANS(o.latitude)) *
                               POWER(SIN(RADIANS(:lng - o.longitude) / 2), 2)
                           )
                       )
                   )::numeric AS distance_m,
                   o.attendance_radius_m AS radius_m,
                   o.clock_in_time AS clock_in,
                   o.clock_out_time AS clock_out
            FROM office o
            WHERE o.office_id = CAST(:site AS uuid) AND o.delete_at IS NULL
            UNION ALL
            SELECT wpd.daily_plan_id AS id,
                   wpd.site_name AS name,
                   NULL::uuid AS unit_id,
                   'WORK_PLAN_DAILY' AS kind,
                   NULL::uuid AS office_id,
                   ROUND(
                       6371000 * 2 * ASIN(
                           SQRT(
                               POWER(SIN(RADIANS(:lat - wpd.site_lat) / 2), 2) +
                               COS(RADIANS(:lat)) * COS(RADIANS(wpd.site_lat)) *
                               POWER(SIN(RADIANS(:lng - wpd.site_lng) / 2), 2)
                           )
                       )
                   )::numeric AS distance_m,
                   wpd.attendance_radius_m AS radius_m,
                   wpd.clock_in_time AS clock_in,
                   wpd.clock_out_time AS clock_out
            FROM work_plan_daily wpd
            WHERE wpd.daily_plan_id = CAST(:site AS uuid) AND wpd.delete_at IS NULL
            LIMIT 1
            """,
            {"site": str(site_id), "lng": lng, "lat": lat},
        )

    async def nearest_valid_site(
        self,
        org_id: UUID | str,
        employee_id: Any,
        work_date: Any,
        lng: float,
        lat: float,
    ) -> Any:
        """Kantor terdekat (pusat/cabang) diukur dari tepi radius presensinya — absen sah otomatis bila berada
        dalam radius kantor mana pun (keputusan pemilik 2026-10-09)."""
        return await self.fetchone(
            """
            SELECT id, name, unit_id, kind, office_id, distance_m, radius_m, clock_in, clock_out
            FROM (
                SELECT o.office_id AS id,
                       o.name,
                       NULL::uuid AS unit_id,
                       'OFFICE' AS kind,
                       o.office_id,
                       ROUND(
                       6371000 * 2 * ASIN(
                           SQRT(
                               POWER(SIN(RADIANS(:lat - o.latitude) / 2), 2) +
                               COS(RADIANS(:lat)) * COS(RADIANS(o.latitude)) *
                               POWER(SIN(RADIANS(:lng - o.longitude) / 2), 2)
                           )
                       )
                   )::numeric AS distance_m,
                       o.attendance_radius_m AS radius_m,
                       o.clock_in_time AS clock_in,
                       o.clock_out_time AS clock_out
                FROM office o
                WHERE o.delete_at IS NULL
            ) offices
            ORDER BY distance_m - radius_m ASC
            LIMIT 1
            """,
            {"lat": lat, "lng": lng},
        )

    async def insert(
        self,
        *,
        org_id: str,
        employee_id: Any,
        work_date: Any,
        site_id: UUID,
        site_label: str,
        lng: float,
        lat: float,
        origin: str,
        selfie_file_id: UUID | None,
        face_result: str | None,
        face_similarity: float | None,
        source: str = "MOBILE",
        explanation: str | None = None,
        at: Any = None,
    ) -> Any:
        """
        Membuat rekaman absensi masuk (check-in) baru pada tabel attendance Master Schema V2.
        Menghitung radius, jarak kantor utama, status zona kota, uang makan, dan status OM.
        """
        # 1. Target absen (kantor atau lokasi tugas harian) + jarak & radius presensinya.
        target = await self.site_for_check_in(site_id, org_id, lng, lat)
        if target is None:
            raise LookupError("target absen tidak ditemukan")
        distance_to_target = int(float(target.distance_m))
        is_within_radius = distance_to_target <= int(target.radius_m)

        # 2. Kantor utama → zona kota & uang makan (docs/35 §5: radius batas kota kantor utama).
        main_office = await self.fetchone(
            """
            SELECT office_id, latitude, longitude, city_boundary_radius_m, in_city_meal_rate, out_city_meal_rate
            FROM office
            WHERE is_main_office = TRUE AND delete_at IS NULL
            LIMIT 1
            """
        )
        if main_office is None:
            raise LookupError("kantor utama belum ditetapkan (office.is_main_office)")
        dist_main = _haversine_distance(lat, lng, float(main_office.latitude), float(main_office.longitude))
        in_city = dist_main <= int(main_office.city_boundary_radius_m)
        city_zone = "DALAM_KOTA" if in_city else "LUAR_KOTA"
        meal_rate = float(main_office.in_city_meal_rate if in_city else main_office.out_city_meal_rate)

        # 3. office_id: kantor yang dituju, atau kantor karyawan bila absen di lokasi tugas harian.
        office_id = target.office_id or await self.scalar(
            "SELECT office_id FROM employee WHERE employee_id = CAST(:emp AS uuid)", {"emp": str(employee_id)}
        )
        daily_plan_id = target.id if target.kind == "WORK_PLAN_DAILY" else None

        # 4. Swafoto yang benar-benar diunggah (file_object); juga bukti foto bila di luar radius.
        photo_path = (
            await self.scalar(
                "SELECT storage_key FROM file_object WHERE id = CAST(:fid AS uuid)", {"fid": str(selfie_file_id)}
            )
            if selfie_file_id
            else None
        )
        if photo_path is None:
            raise LookupError("swafoto absen tidak ditemukan")

        om_status = "AUTO_VALID" if is_within_radius else "PENDING_OM"
        # Skor 0 = wajah belum diperiksa (bukan "cocok"); skor dari pencocokan server sebelum insert (M7).
        face_score = float(face_similarity * 100.0) if face_similarity is not None else 0.0

        return await self.fetchone(
            f"""
            INSERT INTO attendance (
                employee_id, attendance_date, target_location_type, office_id, daily_plan_id,
                scheduled_in, scheduled_out, clock_in_at, in_lat, in_lng,
                face_match_score, face_photo_path, distance_to_target_m,
                is_within_attendance_radius, out_of_radius_photo_path, out_of_radius_note,
                om_approval_status, distance_from_main_office_m, city_zone_status,
                meal_allowance_amount
            ) VALUES (
                CAST(:emp AS uuid), :work_date, :target_type, CAST(:office_id AS uuid), CAST(:daily_id AS uuid),
                :sched_in, :sched_out, COALESCE(CAST(:at AS timestamptz), NOW()),
                :in_lat, :in_lng,
                :face_score, :photo_path, :dist_target,
                :in_radius, :out_photo, :note,
                :om_status, :dist_main, CAST(:city_zone AS city_zone_enum),
                :meal_amount
            )
            RETURNING attendance_id AS id, employee_id, attendance_date AS work_date,
                      COALESCE(daily_plan_id, office_id) AS site_id, CAST(:label AS text) AS site_label,
                      clock_in_at AS check_in_at, clock_out_at AS check_out_at,
                      distance_to_target_m::float AS distance_m,
                      ({IS_LATE}) AS is_late,
                      (clock_out_at IS NOT NULL
                       AND (clock_out_at AT TIME ZONE 'Asia/Jakarta')::time < scheduled_out) AS is_early_leave,
                      CASE
                          WHEN om_approval_status = 'AUTO_VALID' THEN 'AUTO_VALID'
                          WHEN om_approval_status = 'APPROVED_BY_OM' THEN 'APPROVED'
                          WHEN om_approval_status = 'REJECTED_BY_OM' THEN 'REJECTED'
                          ELSE 'NEEDS_REVIEW'
                      END AS status,
                      out_of_radius_note AS explanation, update_at AS reviewed_at,
                      CAST(:selfie_id AS uuid) AS selfie_file_id,
                      CASE WHEN face_match_score = 0 THEN 'SKIPPED' WHEN face_match_score >= 80.0 THEN 'MATCH'
                           ELSE 'MISMATCH' END AS face_result,
                      (face_match_score / 100.0)::float AS face_similarity,
                      NULL::text AS check_out_face_result, NULL::float AS check_out_face_similarity
            """,
            {
                "emp": str(employee_id),
                "work_date": work_date,
                "target_type": target.kind,
                "office_id": str(office_id),
                "daily_id": str(daily_plan_id) if daily_plan_id else None,
                "sched_in": target.clock_in,
                "sched_out": target.clock_out,
                "at": at,
                "in_lat": lat,
                "in_lng": lng,
                "face_score": face_score,
                "photo_path": photo_path,
                "dist_target": distance_to_target,
                "in_radius": is_within_radius,
                "out_photo": photo_path if not is_within_radius else None,
                "note": explanation,
                "om_status": om_status,
                "dist_main": dist_main,
                "city_zone": city_zone,
                "meal_amount": meal_rate,
                "label": site_label,
                "selfie_id": str(selfie_file_id) if selfie_file_id else None,
            },
        )

    async def close(
        self,
        attendance_id: UUID | str,
        *,
        lat: float | None = None,
        lng: float | None = None,
        selfie_file_id: UUID | None = None,
        explanation: str | None = None,
        at: Any = None,
    ) -> Any:
        """Menutup sesi absensi (check-out)."""
        return await self.fetchone(
            f"""
            UPDATE attendance
               SET clock_out_at = COALESCE(CAST(:at AS timestamptz), NOW()),
                   out_of_radius_note = COALESCE(out_of_radius_note || '; ', '') || COALESCE(:exp, ''),
                   update_at = NOW()
             WHERE attendance_id = CAST(:id AS uuid) AND delete_at IS NULL
            RETURNING attendance_id AS id, employee_id, attendance_date AS work_date,
                      COALESCE(daily_plan_id, office_id) AS site_id,
                      COALESCE(
                          (SELECT wpd.site_name FROM work_plan_daily wpd
                               WHERE wpd.daily_plan_id = attendance.daily_plan_id),
                          (SELECT o.name FROM office o WHERE o.office_id = attendance.office_id),
                          'Lokasi Kerja'
                      ) AS site_label,
                      clock_in_at AS check_in_at, clock_out_at AS check_out_at,
                      distance_to_target_m::float AS distance_m,
                      ({IS_LATE}) AS is_late,
                      (clock_out_at IS NOT NULL
                       AND (clock_out_at AT TIME ZONE 'Asia/Jakarta')::time < scheduled_out) AS is_early_leave,
                      CASE
                          WHEN om_approval_status = 'AUTO_VALID' THEN 'AUTO_VALID'
                          WHEN om_approval_status = 'APPROVED_BY_OM' THEN 'APPROVED'
                          WHEN om_approval_status = 'REJECTED_BY_OM' THEN 'REJECTED'
                          ELSE 'NEEDS_REVIEW'
                      END AS status,
                      out_of_radius_note AS explanation, update_at AS reviewed_at,
                      (SELECT f.id FROM file_object f WHERE f.storage_key = attendance.face_photo_path LIMIT 1)
                          AS selfie_file_id,
                      CASE WHEN face_match_score = 0 THEN 'SKIPPED' WHEN face_match_score >= 80.0 THEN 'MATCH'
                           ELSE 'MISMATCH' END AS face_result,
                      (face_match_score / 100.0)::float AS face_similarity,
                      NULL::text AS check_out_face_result, NULL::float AS check_out_face_similarity,
                      NULL::float AS check_out_distance_m, FALSE AS check_out_outside,
                      NULL::uuid AS check_out_selfie_file_id, NULL::text AS check_out_explanation
            """,
            {"id": str(attendance_id), "exp": explanation.strip() if explanation else None, "at": at},
        )

    async def reviewer_employee_ids(self, org_id: UUID | str, employee_id: UUID | str) -> list[str]:
        """Karyawan yang berwenang meninjau absensi: OM, Superadmin, Finance, dan PM atas karyawan itu."""
        rows = await self.fetchall(
            f"""
            SELECT DISTINCT CAST(u.employee_id AS text) AS employee_id
            FROM users u
            WHERE u.employee_id IS NOT NULL
              AND u.employee_id <> CAST(:emp AS uuid)
              AND u.delete_at IS NULL
              AND (u.system_role IN ('SUPER_ADMIN', 'OPERATIONAL_MANAGER', 'FINANCE')
                   OR (u.system_role = 'PROJECT_MANAGER'
                       AND {pm_reaches_employee('u.employee_id', 'CAST(:emp AS uuid)')}))
            """,
            {"emp": str(employee_id)},
        )
        return [r.employee_id for r in rows]

    async def user_ids_of(self, employee_ids: list[str]) -> list[str]:
        """Akun pengguna milik para karyawan."""
        rows = await self.fetchall(
            """
            SELECT CAST(user_id AS text) AS id FROM users
            WHERE employee_id = ANY(CAST(:ids AS uuid[])) AND delete_at IS NULL
            """,
            {"ids": employee_ids},
        )
        return [r.id for r in rows]

    async def employee_name(self, employee_id: UUID | str) -> str:
        """Nama lengkap karyawan."""
        name = await self.scalar(
            "SELECT full_name FROM employee WHERE employee_id = CAST(:id AS uuid)",
            {"id": str(employee_id)},
        )
        return str(name) if name else "Karyawan"

    async def flag_missing_face(self, attendance_id: UUID | str, event: str, note: str) -> Any:
        """Menandai absensi yang memerlukan pemeriksaan verifikasi wajah."""
        return await self.fetchone(
            f"""
            UPDATE attendance
               SET out_of_radius_note = NULLIF(concat_ws('; ', out_of_radius_note, CAST(:note AS text)), ''),
                   om_approval_status = CASE WHEN om_approval_status = 'AUTO_VALID'
                                         THEN 'PENDING_OM' ELSE om_approval_status END,
                   update_at = NOW()
             WHERE attendance_id = CAST(:id AS uuid) AND delete_at IS NULL
            RETURNING attendance_id AS id, employee_id, attendance_date AS work_date,
                      COALESCE(daily_plan_id, office_id) AS site_id,
                      COALESCE(
                          (SELECT wpd.site_name FROM work_plan_daily wpd
                               WHERE wpd.daily_plan_id = attendance.daily_plan_id),
                          (SELECT o.name FROM office o WHERE o.office_id = attendance.office_id),
                          'Lokasi Kerja'
                      ) AS site_label,
                      clock_in_at AS check_in_at, clock_out_at AS check_out_at,
                      distance_to_target_m::float AS distance_m,
                      ({IS_LATE}) AS is_late,
                      (clock_out_at IS NOT NULL
                       AND (clock_out_at AT TIME ZONE 'Asia/Jakarta')::time < scheduled_out) AS is_early_leave,
                      CASE
                          WHEN om_approval_status = 'AUTO_VALID' THEN 'AUTO_VALID'
                          WHEN om_approval_status = 'APPROVED_BY_OM' THEN 'APPROVED'
                          WHEN om_approval_status = 'REJECTED_BY_OM' THEN 'REJECTED'
                          ELSE 'NEEDS_REVIEW'
                      END AS status,
                      out_of_radius_note AS explanation, update_at AS reviewed_at,
                      (SELECT f.id FROM file_object f WHERE f.storage_key = attendance.face_photo_path LIMIT 1)
                          AS selfie_file_id,
                      CASE WHEN face_match_score = 0 THEN 'SKIPPED' WHEN face_match_score >= 80.0 THEN 'MATCH'
                           ELSE 'MISMATCH' END AS face_result,
                      (face_match_score / 100.0)::float AS face_similarity,
                      NULL::text AS check_out_face_result, NULL::float AS check_out_face_similarity
            """,
            {"id": str(attendance_id), "note": note},
        )

    async def get(self, attendance_id: UUID | str, org_id: UUID | str) -> Any:
        """Mengambil satu rekaman absensi berdasarkan ID."""
        return await self.fetchone(
            f"""
            SELECT a.attendance_id AS id,
                   a.employee_id,
                   a.attendance_date AS work_date,
                   COALESCE(a.daily_plan_id, a.office_id) AS site_id,
                   COALESCE(wpd.site_name, o.name, 'Lokasi Kerja') AS site_label,
                   a.clock_in_at AS check_in_at,
                   a.clock_out_at AS check_out_at,
                   a.distance_to_target_m::float AS distance_m,
                   ({IS_LATE_A}) AS is_late,
                   (a.clock_out_at IS NOT NULL
                    AND (a.clock_out_at AT TIME ZONE 'Asia/Jakarta')::time < a.scheduled_out) AS is_early_leave,
                   CASE
                       WHEN a.om_approval_status = 'AUTO_VALID' THEN 'AUTO_VALID'
                       WHEN a.om_approval_status = 'APPROVED_BY_OM' THEN 'APPROVED'
                       WHEN a.om_approval_status = 'REJECTED_BY_OM' THEN 'REJECTED'
                       ELSE 'NEEDS_REVIEW'
                   END AS status,
                   a.out_of_radius_note AS explanation,
                   a.update_at AS reviewed_at,
                   (SELECT f.id FROM file_object f WHERE f.storage_key = a.face_photo_path LIMIT 1)
                       AS selfie_file_id,
                   CASE WHEN a.face_match_score = 0 THEN 'SKIPPED' WHEN a.face_match_score >= 80.0 THEN 'MATCH'
                           ELSE 'MISMATCH' END AS face_result,
                   (a.face_match_score / 100.0)::float AS face_similarity,
                   NULL::text AS check_out_face_result,
                   NULL::float AS check_out_face_similarity
            FROM attendance a
            LEFT JOIN office o ON o.office_id = a.office_id
            LEFT JOIN work_plan_daily wpd ON wpd.daily_plan_id = a.daily_plan_id
            WHERE a.attendance_id = CAST(:id AS uuid) AND a.delete_at IS NULL
            FOR UPDATE OF a
            """,
            {"id": str(attendance_id)},
        )

    async def can_review(self, viewer_user_id: UUID | str, employee_id: UUID | str) -> bool:
        """Mengecek apakah peninjau memiliki wewenang untuk meninjau absensi."""
        return bool(
            await self.scalar(
                f"""
                SELECT (CAST(:emp AS uuid) IS DISTINCT FROM (
                    SELECT employee_id FROM users WHERE user_id = CAST(:viewer AS uuid)
                ))
                   AND (
                       EXISTS (
                           SELECT 1 FROM users
                           WHERE user_id = CAST(:viewer AS uuid)
                             AND system_role IN ('SUPER_ADMIN', 'OPERATIONAL_MANAGER', 'ADMIN_HR_GA', 'FINANCE')
                       )
                       OR (
                           EXISTS (
                               SELECT 1 FROM users
                               WHERE user_id = CAST(:viewer AS uuid) AND system_role = 'PROJECT_MANAGER'
                           )
                           AND {_pm_reach('CAST(:emp AS uuid)')}
                       )
                   )
                """,
                {"viewer": str(viewer_user_id), "emp": str(employee_id)},
            )
        )

    async def list_page(
        self,
        org_id: str,
        viewer_user_id: str,
        *,
        view_all: bool,
        employee_id: Any,
        date_from: Any,
        date_to: Any,
        status: str | None,
        limit: int,
        offset: int,
        scope: str = "all",
        q: str | None = None,
    ) -> tuple[list[Any], int]:
        """Mengambil daftar absensi berpaginasi dengan informasi can_review."""
        status_filter = status
        # Normalize status filter jika berasal dari frontend ('NEEDS_REVIEW' -> 'PENDING_OM' atau mapping sebaliknya)
        params = {
            "viewer": str(viewer_user_id),
            "view_all": view_all,
            "emp": str(employee_id) if employee_id else None,
            "date_from": date_from,
            "date_to": date_to,
            "status": status_filter,
            "scope": scope,
            "q": f"{escape_like(q)}%" if q else None,
            "limit": limit,
            "offset": offset,
        }

        where_clauses = [
            "a.delete_at IS NULL",
            # OM/SUPER_ADMIN & pemegang VIEW_ALL melihat semua; PM hanya karyawan divisinya (pm_id);
            # selain itu hanya absensi miliknya sendiri.
            f"""(
                CAST(:view_all AS boolean)
                OR EXISTS (
                    SELECT 1 FROM users v WHERE v.user_id = CAST(:viewer AS uuid)
                      AND v.system_role IN ('SUPER_ADMIN', 'OPERATIONAL_MANAGER', 'ADMIN_HR_GA', 'FINANCE')
                )
                OR (
                    EXISTS (
                        SELECT 1 FROM users v WHERE v.user_id = CAST(:viewer AS uuid)
                          AND v.system_role = 'PROJECT_MANAGER'
                    )
                    AND {_pm_reach('a.employee_id')}
                )
                OR a.employee_id IS NOT DISTINCT FROM (
                    SELECT u.employee_id FROM users u WHERE u.user_id = CAST(:viewer AS uuid)
                )
            )""",
            "(CAST(:emp AS uuid) IS NULL OR a.employee_id = CAST(:emp AS uuid))",
            """(
                CAST(:scope AS text) = 'all'
                OR (
                    CAST(:scope AS text) = 'mine'
                    AND a.employee_id IS NOT DISTINCT FROM (
                        SELECT u.employee_id FROM users u WHERE u.user_id = CAST(:viewer AS uuid)
                    )
                )
                OR (
                    CAST(:scope AS text) = 'team'
                    AND a.employee_id IS DISTINCT FROM (
                        SELECT u.employee_id FROM users u WHERE u.user_id = CAST(:viewer AS uuid)
                    )
                )
            )""",
            "(CAST(:q AS text) IS NULL OR e.full_name ILIKE CAST(:q AS text) OR e.employee_no ILIKE CAST(:q AS text))",
            "(CAST(:date_from AS date) IS NULL OR a.attendance_date >= CAST(:date_from AS date))",
            "(CAST(:date_to AS date) IS NULL OR a.attendance_date <= CAST(:date_to AS date))",
            """(
                CAST(:status AS text) IS NULL
                OR (
                    CASE
                        WHEN a.om_approval_status = 'AUTO_VALID' THEN 'AUTO_VALID'
                        WHEN a.om_approval_status = 'APPROVED_BY_OM' THEN 'APPROVED'
                        WHEN a.om_approval_status = 'REJECTED_BY_OM' THEN 'REJECTED'
                        ELSE 'NEEDS_REVIEW'
                    END = CAST(:status AS text)
                )
            )""",
        ]
        where_sql = " AND ".join(where_clauses)

        query = f"""
            SELECT a.attendance_id AS id,
                   a.employee_id,
                   a.attendance_date AS work_date,
                   COALESCE(a.daily_plan_id, a.office_id) AS site_id,
                   COALESCE(wpd.site_name, o.name, 'Lokasi Kerja') AS site_label,
                   a.clock_in_at AS check_in_at,
                   a.clock_out_at AS check_out_at,
                   a.distance_to_target_m::float AS distance_m,
                   ({IS_LATE_A}) AS is_late,
                   (a.clock_out_at IS NOT NULL
                    AND (a.clock_out_at AT TIME ZONE 'Asia/Jakarta')::time < a.scheduled_out) AS is_early_leave,
                   CASE
                       WHEN a.om_approval_status = 'AUTO_VALID' THEN 'AUTO_VALID'
                       WHEN a.om_approval_status = 'APPROVED_BY_OM' THEN 'APPROVED'
                       WHEN a.om_approval_status = 'REJECTED_BY_OM' THEN 'REJECTED'
                       ELSE 'NEEDS_REVIEW'
                   END AS status,
                   a.out_of_radius_note AS explanation,
                   a.update_at AS reviewed_at,
                   (SELECT f.id FROM file_object f WHERE f.storage_key = a.face_photo_path LIMIT 1)
                       AS selfie_file_id,
                   a.out_of_radius_note AS review_note,
                   e.full_name AS employee_name,
                   (SELECT f.id FROM file_object f WHERE f.storage_key = e.profile_photo_path LIMIT 1)
                       AS employee_photo_file_id,
                   CASE WHEN a.face_match_score = 0 THEN 'SKIPPED' WHEN a.face_match_score >= 80.0 THEN 'MATCH'
                           ELSE 'MISMATCH' END AS face_result,
                   (a.face_match_score / 100.0)::float AS face_similarity,
                   NULL::text AS check_out_face_result,
                   NULL::float AS check_out_face_similarity,
                   FALSE AS offline,
                   NULL::text AS offline_note,
                   NULL::timestamptz AS check_out_requested_at,
                   NULL::float AS check_out_distance_m,
                   FALSE AS check_out_outside,
                   NULL::uuid AS check_out_selfie_file_id,
                   NULL::text AS check_out_explanation,
                   a.city_zone_status::text AS city_category,
                   a.meal_allowance_amount::float AS meal_allowance_amount,
                   a.is_within_attendance_radius AS is_within_attendance_radius,
                   (
                       (
                           EXISTS (
                               SELECT 1 FROM users u
                               WHERE u.user_id = CAST(:viewer AS uuid)
                                 AND u.system_role IN ('SUPER_ADMIN', 'OPERATIONAL_MANAGER', 'ADMIN_HR_GA', 'FINANCE')
                           )
                           OR (
                               EXISTS (
                                   SELECT 1 FROM users u
                                   WHERE u.user_id = CAST(:viewer AS uuid) AND u.system_role = 'PROJECT_MANAGER'
                               )
                               AND {_pm_reach('a.employee_id')}
                           )
                       )
                       AND a.employee_id IS DISTINCT FROM (
                           SELECT u2.employee_id FROM users u2 WHERE u2.user_id = CAST(:viewer AS uuid)
                       )
                   ) AS can_review
            FROM attendance a
            JOIN employee e ON e.employee_id = a.employee_id
            LEFT JOIN office o ON o.office_id = a.office_id
            LEFT JOIN work_plan_daily wpd ON wpd.daily_plan_id = a.daily_plan_id
            WHERE {where_sql}
            ORDER BY a.attendance_date DESC, a.clock_in_at DESC
            LIMIT :limit OFFSET :offset
        """
        count_query = f"""
            SELECT count(*)
            FROM attendance a
            JOIN employee e ON e.employee_id = a.employee_id
            WHERE {where_sql}
        """

        rows = await self.fetchall(query, params)
        total = await self.scalar(count_query, params)
        return list(rows), int(total or 0)

    async def set_explanation(self, attendance_id: UUID | str, explanation: str) -> None:
        """Menambahkan penjelasan alasan di luar radius."""
        await self.execute(
            """
            UPDATE attendance
            SET out_of_radius_note = :exp, update_at = NOW()
            WHERE attendance_id = CAST(:id AS uuid) AND delete_at IS NULL
            """,
            {"exp": explanation, "id": str(attendance_id)},
        )

    async def admin_update(self, attendance_id: UUID | str, fields: dict[str, Any]) -> bool:
        """Koreksi kolom absensi (nama kolom dari daftar tetap, nilai lewat parameter)."""
        allowed = ("clock_in_at", "clock_out_at", "om_approval_status", "out_of_radius_note")
        sets = [f"{c} = :{c}" for c in allowed if c in fields]
        if not sets:
            return False
        params = {c: fields[c] for c in allowed if c in fields} | {"id": str(attendance_id)}
        result = await self.execute(
            f"UPDATE attendance SET {', '.join(sets)}, update_at = NOW() "
            "WHERE attendance_id = CAST(:id AS uuid) AND delete_at IS NULL", params)
        return bool(result.rowcount)

    async def admin_exists(self, attendance_id: UUID | str) -> bool:
        row = await self.fetchone("SELECT 1 FROM attendance WHERE attendance_id = CAST(:id AS uuid) FOR UPDATE",
                                  {"id": str(attendance_id)})
        return row is not None

    async def set_review(self, attendance_id: UUID | str, status: str, reviewer: Any, note: str) -> None:
        """Menyimpan hasil peninjauan absensi oleh OM/atasan."""
        om_status = "APPROVED_BY_OM" if status == "APPROVED" else "REJECTED_BY_OM"
        await self.execute(
            """
            UPDATE attendance
            SET om_approval_status = :om_status,
                out_of_radius_note = COALESCE(out_of_radius_note || ' | ', '') || CAST(:note AS text),
                update_at = NOW()
            WHERE attendance_id = CAST(:id AS uuid) AND delete_at IS NULL
            """,
            {"om_status": om_status, "note": note, "id": str(attendance_id)},
        )

    async def export_rows(self, org_id: UUID | str, start: Any, end: Any) -> list[Any]:
        """Baris ekspor absensi untuk laporan rekap."""
        return list(
            await self.fetchall(
                f"""
                SELECT a.attendance_date AS work_date,
                       e.employee_no,
                       e.full_name,
                       COALESCE(wpd.site_name, o.name, 'Lokasi Kerja') AS site_label,
                       to_char(a.clock_in_at AT TIME ZONE 'Asia/Jakarta', 'HH24:MI:SS') AS check_in,
                       to_char(a.clock_out_at AT TIME ZONE 'Asia/Jakarta', 'HH24:MI:SS') AS check_out,
                       CASE
                           WHEN a.om_approval_status = 'AUTO_VALID' THEN 'AUTO_VALID'
                           WHEN a.om_approval_status = 'APPROVED_BY_OM' THEN 'APPROVED'
                           WHEN a.om_approval_status = 'REJECTED_BY_OM' THEN 'REJECTED'
                           ELSE 'NEEDS_REVIEW'
                       END AS status,
                       ({IS_LATE_A}) AS is_late,
                       (a.clock_out_at IS NOT NULL
                        AND (a.clock_out_at AT TIME ZONE 'Asia/Jakarta')::time < a.scheduled_out) AS is_early_leave,
                       NULL::float AS check_out_distance_m,
                       FALSE AS check_out_outside,
                       a.city_zone_status::text AS city_category,
                       CASE WHEN a.om_approval_status IN ('AUTO_VALID', 'APPROVED_BY_OM')
                            THEN a.meal_allowance_amount ELSE 0 END::float AS meal_allowance_amount
                FROM attendance a
                JOIN employee e ON a.employee_id = e.employee_id
                LEFT JOIN office o ON o.office_id = a.office_id
                LEFT JOIN work_plan_daily wpd ON wpd.daily_plan_id = a.daily_plan_id
                WHERE a.delete_at IS NULL
                  AND a.attendance_date BETWEEN :start AND :end
                ORDER BY a.attendance_date ASC, e.full_name ASC
                """,
                {"start": start, "end": end},
            )
        )

    async def meal_allowance_recap(self, start: Any, end: Any, division_id: UUID | None = None) -> list[Any]:
        """Uang makan per karyawan: tarif sudah dibekukan per absen saat masuk (zona kota kantor utama);
        hanya absensi sah yang dijumlah. Satu absen per karyawan per hari (attendance_active_uidx)."""
        return list(
            await self.fetchall(
                """
                SELECT e.employee_id, e.employee_no, e.full_name,
                       COUNT(*) FILTER (WHERE ok AND a.city_zone_status = 'DALAM_KOTA')::int AS in_city_days,
                       COUNT(*) FILTER (WHERE ok AND a.city_zone_status = 'LUAR_KOTA')::int AS out_city_days,
                       COALESCE(SUM(a.meal_allowance_amount) FILTER (WHERE ok), 0)::float AS total_amount,
                       COUNT(*) FILTER (WHERE a.om_approval_status = 'PENDING_OM')::int AS pending_days
                FROM attendance a
                CROSS JOIN LATERAL (SELECT a.om_approval_status IN ('AUTO_VALID', 'APPROVED_BY_OM') AS ok) v
                JOIN employee e ON e.employee_id = a.employee_id
                WHERE a.delete_at IS NULL
                  AND a.attendance_date BETWEEN :start AND :end
                  AND (CAST(:div AS uuid) IS NULL OR e.division_id = CAST(:div AS uuid))
                GROUP BY e.employee_id, e.employee_no, e.full_name
                ORDER BY e.full_name
                """,
                {"start": start, "end": end, "div": str(division_id) if division_id else None},
            )
        )

    async def active_leader_plan_without_report(
        self, employee_id: UUID | str, work_date: Any
    ) -> UUID | None:
        """Cari apakah karyawan adalah ketua tim pada jadwal harian hari ini yang belum memiliki laporan."""
        sql = """
            SELECT wpd.daily_plan_id
            FROM work_plan_daily wpd
            JOIN team t ON t.team_id = wpd.team_id
            WHERE t.leader_employee_id = CAST(:eid AS uuid)
              AND wpd.work_date = :wdate
              AND wpd.status IN ('APPROVED', 'ONGOING')
              AND wpd.delete_at IS NULL
              AND NOT EXISTS (
                  SELECT 1 FROM work_plan_daily_report r
                  WHERE r.daily_plan_id = wpd.daily_plan_id AND r.delete_at IS NULL
              )
            LIMIT 1
        """
        val = await self.scalar(sql, {"eid": str(employee_id), "wdate": work_date})
        return UUID(str(val)) if val is not None else None


    async def is_on_approved_leave(
        self, employee_id: UUID | str, work_date: Any
    ) -> tuple[bool, str | None]:
        """Cek apakah karyawan memiliki cuti/izin/sakit yang sudah disetujui pada tanggal kerja ini."""
        sql = """
            SELECT leave_type
            FROM leave_request
            WHERE employee_id = CAST(:eid AS uuid)
              AND :wdate >= start_date AND :wdate <= end_date
              AND status IN ('APPROVED_BY_PM', 'APPROVED_BY_HR')
              AND delete_at IS NULL
            LIMIT 1
        """
        val = await self.scalar(sql, {"eid": str(employee_id), "wdate": work_date})
        if val is not None:
            return True, str(val)
        return False, None

    async def has_active_overtime(
        self, employee_id: UUID | str, work_date: Any
    ) -> bool:
        """Cek apakah karyawan memiliki lembur (APPROVED atau PENDING_PM) pada tanggal ini."""
        sql = """
            SELECT 1
            FROM overtime
            WHERE employee_id = CAST(:eid AS uuid)
              AND work_date = :wdate
              AND status IN ('APPROVED', 'PENDING_PM')
              AND delete_at IS NULL
            LIMIT 1
        """
        val = await self.scalar(sql, {"eid": str(employee_id), "wdate": work_date})
        return val is not None

    async def my_recap_rows(self, employee_id: UUID | str, start: Any, end: Any) -> list[Any]:
        """Absensi satu karyawan dalam rentang tanggal (WIB) untuk rekap pribadi."""
        return list(
            await self.fetchall(
                f"""
                SELECT a.attendance_date AS work_date, a.clock_in_at AS check_in_at, a.clock_out_at AS check_out_at,
                       ({IS_LATE_A}) AS is_late,
                       (a.clock_out_at IS NOT NULL
                        AND (a.clock_out_at AT TIME ZONE 'Asia/Jakarta')::time < a.scheduled_out) AS is_early_leave,
                       a.om_approval_status IN ('AUTO_VALID', 'APPROVED_BY_OM', 'APPROVED') AS is_valid,
                       a.om_approval_status = 'PENDING_OM' AS is_pending,
                       a.meal_allowance_amount::float AS meal_allowance_amount,
                       a.city_zone_status AS city_zone,
                       (SELECT f.id FROM file_object f WHERE f.storage_key = a.face_photo_path LIMIT 1)
                           AS selfie_file_id
                FROM attendance a
                WHERE a.employee_id = CAST(:emp AS uuid) AND a.delete_at IS NULL
                  AND a.attendance_date BETWEEN :start AND :end
                ORDER BY a.attendance_date DESC
                """,
                {"emp": str(employee_id), "start": start, "end": end},
            )
        )


CRUDAttendanceSession = AttendanceSessionRepository
