"""
app/crud/crud_attendance_session.py
Sesi absensi VMS Master Schema V2.
Mendukung validasi koordinat GPS (Haversine), radius toleransi, validasi wajah,
status persetujuan OM ('AUTO_VALID', 'PENDING_OM', 'APPROVED_BY_OM', 'REJECTED_BY_OM'),
zona kota (DALAM_KOTA / LUAR_KOTA), dan kalkulasi uang makan.
"""

from __future__ import annotations

import math
from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository


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
        Mengambil profil karyawan dan kewenangan akun.
        """
        return await self.fetchone(
            """
            SELECT e.employee_id,
                   'FIELD' AS attendance_mode,
                   e.division_id AS unit_id,
                   (u.system_role IN ('SUPER_ADMIN', 'OPERATIONAL_MANAGER', 'ADMIN_HR_GA')) AS is_admin
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
            """
            SELECT a.attendance_id AS id,
                   a.employee_id,
                   a.office_id AS organization_id,
                   a.attendance_date AS work_date,
                   COALESCE(a.daily_plan_id, a.office_id) AS site_id,
                   COALESCE(wpd.site_name, o.name, 'Lokasi Kerja') AS site_label,
                   a.clock_in_at AS check_in_at,
                   a.clock_out_at AS check_out_at,
                   a.distance_to_target_m::float AS distance_m,
                   (a.clock_in_at::time > a.scheduled_in) AS is_late,
                   (a.clock_out_at IS NOT NULL AND a.clock_out_at::time < a.scheduled_out) AS is_early_leave,
                   CASE
                       WHEN a.om_approval_status = 'AUTO_VALID' THEN 'AUTO_VALID'
                       WHEN a.om_approval_status = 'APPROVED_BY_OM' THEN 'APPROVED'
                       WHEN a.om_approval_status = 'REJECTED_BY_OM' THEN 'REJECTED'
                       ELSE 'NEEDS_REVIEW'
                   END AS status,
                   a.out_of_radius_note AS explanation,
                   a.update_at AS reviewed_at,
                   NULL::uuid AS selfie_file_id,
                   CASE WHEN a.face_match_score >= 80.0 THEN 'MATCH' ELSE 'MISMATCH' END AS face_result,
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

    async def auto_checkout_unclosed(
        self,
        org_id: UUID | str,
        work_date: Any,
        close_time: Any,
        explanation: str,
    ) -> list[Any]:
        """Menutup otomatis sesi absensi yang belum ditutup pada jam penutupan harian."""
        return list(
            await self.fetchall(
                """
                UPDATE attendance
                   SET clock_out_at = :close_time,
                       out_of_radius_note = COALESCE(out_of_radius_note || '; ', '') || :explanation,
                       update_at = NOW()
                 WHERE office_id = CAST(:org AS uuid)
                   AND attendance_date = :work_date
                   AND clock_in_at IS NOT NULL
                   AND clock_out_at IS NULL
                   AND om_approval_status <> 'REJECTED_BY_OM'
                   AND delete_at IS NULL
                RETURNING attendance_id AS id, employee_id, 'Kantor' AS site_label
                """,
                {"org": str(org_id), "work_date": work_date, "close_time": close_time, "explanation": explanation},
            )
        )

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
        """Mendapatkan data lokasi (office atau work_plan_daily) dan menghitung jaraknya."""
        return await self.fetchone(
            """
            SELECT o.office_id AS id,
                   o.name,
                   NULL::uuid AS unit_id,
                   ROUND(
                       6371000 * 2 * ASIN(
                           SQRT(
                               POWER(SIN(RADIANS(:lat - o.latitude) / 2), 2) +
                               COS(RADIANS(:lat)) * COS(RADIANS(o.latitude)) *
                               POWER(SIN(RADIANS(:lng - o.longitude) / 2), 2)
                           )
                       )
                   )::numeric AS distance_m,
                   o.attendance_radius_m AS radius_m
            FROM office o
            WHERE o.office_id = CAST(:site AS uuid) AND o.delete_at IS NULL
            UNION ALL
            SELECT wpd.daily_plan_id AS id,
                   wpd.site_name AS name,
                   NULL::uuid AS unit_id,
                   ROUND(
                       6371000 * 2 * ASIN(
                           SQRT(
                               POWER(SIN(RADIANS(:lat - wpd.site_lat) / 2), 2) +
                               COS(RADIANS(:lat)) * COS(RADIANS(wpd.site_lat)) *
                               POWER(SIN(RADIANS(:lng - wpd.site_lng) / 2), 2)
                           )
                       )
                   )::numeric AS distance_m,
                   wpd.attendance_radius_m AS radius_m
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
        """Mencari lokasi sah terdekat (kantor cabang/pusat terdekat)."""
        return await self.fetchone(
            """
            SELECT o.office_id AS id,
                   o.name,
                   NULL::uuid AS unit_id,
                   ROUND(
                       6371000 * 2 * ASIN(
                           SQRT(
                               POWER(SIN(RADIANS(:lat - o.latitude) / 2), 2) +
                               COS(RADIANS(:lat)) * COS(RADIANS(o.latitude)) *
                               POWER(SIN(RADIANS(:lng - o.longitude) / 2), 2)
                           )
                       )
                   )::numeric AS distance_m,
                   o.attendance_radius_m AS radius_m
            FROM office o
            WHERE o.delete_at IS NULL
            ORDER BY distance_m - o.attendance_radius_m ASC
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
        # 1. Dapatkan info lokasi target (office atau daily plan)
        target = await self.site_for_check_in(site_id, org_id, lng, lat)
        distance_to_target = int(float(target.distance_m)) if target else 0
        radius_m = int(target.radius_m) if target else 100
        is_within_radius = distance_to_target <= radius_m

        # 2. Dapatkan kantor utama untuk kalkulasi zona kota & uang makan
        main_office = await self.fetchone(
            """
            SELECT office_id, latitude, longitude, city_boundary_radius_m, in_city_meal_rate, out_city_meal_rate,
                   clock_in_time, clock_out_time
            FROM office
            WHERE is_main_office = TRUE AND delete_at IS NULL
            LIMIT 1
            """
        )
        if not main_office:
            main_office = await self.fetchone(
                """
                SELECT office_id, latitude, longitude, city_boundary_radius_m, in_city_meal_rate, out_city_meal_rate,
                       clock_in_time, clock_out_time
                FROM office
                WHERE delete_at IS NULL
                ORDER BY create_at ASC
                LIMIT 1
                """
            )

        if main_office:
            dist_main = _haversine_distance(lat, lng, float(main_office.latitude), float(main_office.longitude))
            boundary_m = int(main_office.city_boundary_radius_m)
            sched_in = main_office.clock_in_time
            sched_out = main_office.clock_out_time
            if dist_main <= boundary_m:
                city_zone = "DALAM_KOTA"
                meal_rate = float(main_office.in_city_meal_rate)
            else:
                city_zone = "LUAR_KOTA"
                meal_rate = float(main_office.out_city_meal_rate)
            resolved_office_id = main_office.office_id
        else:
            dist_main = distance_to_target
            city_zone = "DALAM_KOTA"
            meal_rate = 35000.00
            sched_in = "07:00:00"
            sched_out = "16:00:00"
            resolved_office_id = site_id

        # Tentukan target_location_type dan daily_plan_id
        is_daily_plan = bool(
            await self.scalar(
                "SELECT 1 FROM work_plan_daily WHERE daily_plan_id = CAST(:sid AS uuid)",
                {"sid": str(site_id)},
            )
        )
        if is_daily_plan:
            target_type = "WORK_PLAN_DAILY"
            daily_plan_id = site_id
        else:
            target_type = "OFFICE"
            daily_plan_id = None

        om_status = "AUTO_VALID" if is_within_radius else "PENDING_OM"
        face_score = float(face_similarity * 100.0) if face_similarity is not None else 95.00

        return await self.fetchone(
            """
            INSERT INTO attendance (
                employee_id, attendance_date, target_location_type, office_id, daily_plan_id,
                scheduled_in, scheduled_out, clock_in_at, in_lat, in_lng,
                face_match_score, face_photo_path, distance_to_target_m,
                is_within_attendance_radius, out_of_radius_photo_path, out_of_radius_note,
                om_approval_status, distance_from_main_office_m, city_zone_status,
                meal_allowance_amount
            ) VALUES (
                CAST(:emp AS uuid), :work_date, :target_type, CAST(:office_id AS uuid), CAST(:daily_id AS uuid),
                CAST(:sched_in AS time), CAST(:sched_out AS time), COALESCE(CAST(:at AS timestamptz), NOW()),
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
                      (clock_in_at::time > scheduled_in) AS is_late,
                      (clock_out_at IS NOT NULL AND clock_out_at::time < scheduled_out) AS is_early_leave,
                      CASE
                          WHEN om_approval_status = 'AUTO_VALID' THEN 'AUTO_VALID'
                          WHEN om_approval_status = 'APPROVED_BY_OM' THEN 'APPROVED'
                          WHEN om_approval_status = 'REJECTED_BY_OM' THEN 'REJECTED'
                          ELSE 'NEEDS_REVIEW'
                      END AS status,
                      out_of_radius_note AS explanation, update_at AS reviewed_at,
                      NULL::uuid AS selfie_file_id,
                      CASE WHEN face_match_score >= 80.0 THEN 'MATCH' ELSE 'MISMATCH' END AS face_result,
                      (face_match_score / 100.0)::float AS face_similarity,
                      NULL::text AS check_out_face_result, NULL::float AS check_out_face_similarity
            """,
            {
                "emp": str(employee_id),
                "work_date": work_date,
                "target_type": target_type,
                "office_id": str(resolved_office_id),
                "daily_id": str(daily_plan_id) if daily_plan_id else None,
                "sched_in": sched_in,
                "sched_out": sched_out,
                "at": at,
                "in_lat": lat,
                "in_lng": lng,
                "face_score": face_score,
                "photo_path": f"/uploads/att/{employee_id}_{work_date}.jpg",
                "dist_target": distance_to_target,
                "in_radius": is_within_radius,
                "out_photo": f"/uploads/att/out_{employee_id}.jpg" if not is_within_radius else None,
                "note": explanation,
                "om_status": om_status,
                "dist_main": dist_main,
                "city_zone": city_zone,
                "meal_amount": meal_rate,
                "label": site_label,
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
    ) -> Any:
        """Menutup sesi absensi (check-out)."""
        return await self.fetchone(
            """
            UPDATE attendance
               SET clock_out_at = NOW(),
                   out_of_radius_note = COALESCE(out_of_radius_note || '; ', '') || COALESCE(:exp, ''),
                   update_at = NOW()
             WHERE attendance_id = CAST(:id AS uuid) AND delete_at IS NULL
            RETURNING attendance_id AS id, employee_id, attendance_date AS work_date,
                      COALESCE(daily_plan_id, office_id) AS site_id, 'Lokasi Kerja' AS site_label,
                      clock_in_at AS check_in_at, clock_out_at AS check_out_at,
                      distance_to_target_m::float AS distance_m,
                      (clock_in_at::time > scheduled_in) AS is_late,
                      (clock_out_at IS NOT NULL AND clock_out_at::time < scheduled_out) AS is_early_leave,
                      CASE
                          WHEN om_approval_status = 'AUTO_VALID' THEN 'AUTO_VALID'
                          WHEN om_approval_status = 'APPROVED_BY_OM' THEN 'APPROVED'
                          WHEN om_approval_status = 'REJECTED_BY_OM' THEN 'REJECTED'
                          ELSE 'NEEDS_REVIEW'
                      END AS status,
                      out_of_radius_note AS explanation, update_at AS reviewed_at,
                      NULL::uuid AS selfie_file_id,
                      CASE WHEN face_match_score >= 80.0 THEN 'MATCH' ELSE 'MISMATCH' END AS face_result,
                      (face_match_score / 100.0)::float AS face_similarity,
                      NULL::text AS check_out_face_result, NULL::float AS check_out_face_similarity,
                      NULL::float AS check_out_distance_m, FALSE AS check_out_outside,
                      NULL::uuid AS check_out_selfie_file_id, NULL::text AS check_out_explanation
            """,
            {"id": str(attendance_id), "exp": explanation.strip() if explanation else None},
        )

    async def reviewer_employee_ids(self, org_id: UUID | str, employee_id: UUID | str) -> list[str]:
        """Karyawan yang berwenang meninjau absensi (OM, PM, Superadmin)."""
        rows = await self.fetchall(
            """
            SELECT DISTINCT CAST(u.employee_id AS text) AS employee_id
            FROM users u
            WHERE u.system_role IN ('SUPER_ADMIN', 'OPERATIONAL_MANAGER', 'PROJECT_MANAGER', 'ADMIN_HR_GA')
              AND u.employee_id IS NOT NULL
              AND u.employee_id <> CAST(:emp AS uuid)
              AND u.delete_at IS NULL
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
            """
            UPDATE attendance
               SET out_of_radius_note = NULLIF(concat_ws('; ', out_of_radius_note, CAST(:note AS text)), ''),
                   om_approval_status = CASE WHEN om_approval_status = 'AUTO_VALID'
                                         THEN 'PENDING_OM' ELSE om_approval_status END,
                   update_at = NOW()
             WHERE attendance_id = CAST(:id AS uuid) AND delete_at IS NULL
            RETURNING attendance_id AS id, employee_id, attendance_date AS work_date,
                      COALESCE(daily_plan_id, office_id) AS site_id, 'Lokasi Kerja' AS site_label,
                      clock_in_at AS check_in_at, clock_out_at AS check_out_at,
                      distance_to_target_m::float AS distance_m,
                      (clock_in_at::time > scheduled_in) AS is_late,
                      (clock_out_at IS NOT NULL AND clock_out_at::time < scheduled_out) AS is_early_leave,
                      CASE
                          WHEN om_approval_status = 'AUTO_VALID' THEN 'AUTO_VALID'
                          WHEN om_approval_status = 'APPROVED_BY_OM' THEN 'APPROVED'
                          WHEN om_approval_status = 'REJECTED_BY_OM' THEN 'REJECTED'
                          ELSE 'NEEDS_REVIEW'
                      END AS status,
                      out_of_radius_note AS explanation, update_at AS reviewed_at,
                      NULL::uuid AS selfie_file_id,
                      CASE WHEN face_match_score >= 80.0 THEN 'MATCH' ELSE 'MISMATCH' END AS face_result,
                      (face_match_score / 100.0)::float AS face_similarity,
                      NULL::text AS check_out_face_result, NULL::float AS check_out_face_similarity
            """,
            {"id": str(attendance_id), "note": note},
        )

    async def set_face(
        self,
        attendance_id: UUID | str,
        event: str,
        *,
        check_id: UUID | str | None,
        result: str,
        similarity: float | None,
        flag_review: bool,
    ) -> Any:
        """Menyimpan hasil pengenalan wajah pada absen masuk/pulang."""
        score = float(similarity * 100.0) if similarity is not None else 95.0
        return await self.fetchone(
            """
            UPDATE attendance
               SET face_match_score = :score,
                   om_approval_status = CASE
                       WHEN CAST(:flag AS boolean) AND om_approval_status = 'AUTO_VALID'
                       THEN 'PENDING_OM'
                       ELSE om_approval_status
                   END,
                   update_at = NOW()
             WHERE attendance_id = CAST(:id AS uuid) AND delete_at IS NULL
            RETURNING attendance_id AS id, employee_id, attendance_date AS work_date,
                      COALESCE(daily_plan_id, office_id) AS site_id, 'Lokasi Kerja' AS site_label,
                      clock_in_at AS check_in_at, clock_out_at AS check_out_at,
                      distance_to_target_m::float AS distance_m,
                      (clock_in_at::time > scheduled_in) AS is_late,
                      (clock_out_at IS NOT NULL AND clock_out_at::time < scheduled_out) AS is_early_leave,
                      CASE
                          WHEN om_approval_status = 'AUTO_VALID' THEN 'AUTO_VALID'
                          WHEN om_approval_status = 'APPROVED_BY_OM' THEN 'APPROVED'
                          WHEN om_approval_status = 'REJECTED_BY_OM' THEN 'REJECTED'
                          ELSE 'NEEDS_REVIEW'
                      END AS status,
                      out_of_radius_note AS explanation, update_at AS reviewed_at,
                      NULL::uuid AS selfie_file_id,
                      CASE WHEN face_match_score >= 80.0 THEN 'MATCH' ELSE 'MISMATCH' END AS face_result,
                      (face_match_score / 100.0)::float AS face_similarity,
                      NULL::text AS check_out_face_result, NULL::float AS check_out_face_similarity
            """,
            {"id": str(attendance_id), "score": score, "flag": flag_review},
        )

    async def get(self, attendance_id: UUID | str, org_id: UUID | str) -> Any:
        """Mengambil satu rekaman absensi berdasarkan ID."""
        return await self.fetchone(
            """
            SELECT a.attendance_id AS id,
                   a.employee_id,
                   a.attendance_date AS work_date,
                   COALESCE(a.daily_plan_id, a.office_id) AS site_id,
                   COALESCE(wpd.site_name, o.name, 'Lokasi Kerja') AS site_label,
                   a.clock_in_at AS check_in_at,
                   a.clock_out_at AS check_out_at,
                   a.distance_to_target_m::float AS distance_m,
                   (a.clock_in_at::time > a.scheduled_in) AS is_late,
                   (a.clock_out_at IS NOT NULL AND a.clock_out_at::time < a.scheduled_out) AS is_early_leave,
                   CASE
                       WHEN a.om_approval_status = 'AUTO_VALID' THEN 'AUTO_VALID'
                       WHEN a.om_approval_status = 'APPROVED_BY_OM' THEN 'APPROVED'
                       WHEN a.om_approval_status = 'REJECTED_BY_OM' THEN 'REJECTED'
                       ELSE 'NEEDS_REVIEW'
                   END AS status,
                   a.out_of_radius_note AS explanation,
                   a.update_at AS reviewed_at,
                   NULL::uuid AS selfie_file_id,
                   CASE WHEN a.face_match_score >= 80.0 THEN 'MATCH' ELSE 'MISMATCH' END AS face_result,
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
                """
                SELECT (CAST(:emp AS uuid) IS DISTINCT FROM (
                    SELECT employee_id FROM users WHERE user_id = CAST(:viewer AS uuid)
                ))
                   AND EXISTS (
                       SELECT 1 FROM users
                       WHERE user_id = CAST(:viewer AS uuid)
                         AND system_role IN ('SUPER_ADMIN', 'OPERATIONAL_MANAGER', 'PROJECT_MANAGER', 'ADMIN_HR_GA')
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
    ) -> tuple[list[Any], int]:
        """Mengambil daftar absensi berpaginasi dengan informasi can_review."""
        status_filter = status
        # Normalize status filter jika berasal dari frontend ('NEEDS_REVIEW' -> 'PENDING_OM' atau mapping sebaliknya)
        params = {
            "viewer": str(viewer_user_id),
            "emp": str(employee_id) if employee_id else None,
            "date_from": date_from,
            "date_to": date_to,
            "status": status_filter,
            "scope": scope,
            "limit": limit,
            "offset": offset,
        }

        where_clauses = [
            "a.delete_at IS NULL",
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
                   (a.clock_in_at::time > a.scheduled_in) AS is_late,
                   (a.clock_out_at IS NOT NULL AND a.clock_out_at::time < a.scheduled_out) AS is_early_leave,
                   CASE
                       WHEN a.om_approval_status = 'AUTO_VALID' THEN 'AUTO_VALID'
                       WHEN a.om_approval_status = 'APPROVED_BY_OM' THEN 'APPROVED'
                       WHEN a.om_approval_status = 'REJECTED_BY_OM' THEN 'REJECTED'
                       ELSE 'NEEDS_REVIEW'
                   END AS status,
                   a.out_of_radius_note AS explanation,
                   a.update_at AS reviewed_at,
                   NULL::uuid AS selfie_file_id,
                   a.out_of_radius_note AS review_note,
                   e.full_name AS employee_name,
                   CASE WHEN a.face_match_score >= 80.0 THEN 'MATCH' ELSE 'MISMATCH' END AS face_result,
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
                       EXISTS (
                           SELECT 1 FROM users u
                           WHERE u.user_id = CAST(:viewer AS uuid)
                             AND u.system_role IN (
                                  'SUPER_ADMIN', 'OPERATIONAL_MANAGER', 'PROJECT_MANAGER', 'ADMIN_HR_GA'
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
                """
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
                       (a.clock_in_at::time > a.scheduled_in) AS is_late,
                       (a.clock_out_at IS NOT NULL AND a.clock_out_at::time < a.scheduled_out) AS is_early_leave,
                       NULL::float AS check_out_distance_m,
                       FALSE AS check_out_outside,
                       a.city_zone_status::text AS city_category
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


CRUDAttendanceSession = AttendanceSessionRepository
