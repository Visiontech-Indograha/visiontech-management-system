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

    async def employee_of(self, user_id: UUID | str) -> Any:
        return await self.scalar("SELECT employee_id FROM vms.app_user WHERE id = :uid", {"uid": user_id})

    async def attendance_mode_of(self, user_id: UUID | str) -> Any:
        """(employee_id, attendance_mode, unit_id) milik akun; None bila akun tidak tertaut karyawan."""
        return await self.fetchone(
            """
            SELECT e.id AS employee_id, e.attendance_mode, e.unit_id
            FROM vms.app_user u JOIN vms.employee e ON e.id = u.employee_id
            WHERE u.id = :uid
            """,
            {"uid": user_id},
        )

    async def open_session(self, employee_id: UUID | str, *, valid_only: bool = False) -> Any:
        """Sesi terbuka terbaru (belum check-out, tidak ditolak) — tanggal berapa pun.
        `valid_only`: hanya yang sudah valid (Valid otomatis / Disetujui) — syarat absen pulang (R-33)."""
        return await self.fetchone(
            """
            SELECT id, employee_id, work_date, site_id, site_label, check_in_at, check_out_at,
                   distance_m, is_late, is_early_leave, status, explanation, reviewed_at, selfie_file_id
            FROM vms.attendance
            WHERE employee_id = :emp AND check_out_at IS NULL AND status <> 'REJECTED'
              AND (NOT CAST(:valid AS boolean) OR status IN ('AUTO_VALID', 'APPROVED'))
            ORDER BY check_in_at DESC LIMIT 1
            """,
            {"emp": employee_id, "valid": valid_only},
        )

    async def active_on(self, employee_id: UUID | str, work_date: Any) -> bool:
        return bool(await self.scalar(
            """
            SELECT EXISTS (SELECT 1 FROM vms.attendance
                           WHERE employee_id = :emp AND work_date = :day AND status <> 'REJECTED')
            """,
            {"emp": employee_id, "day": work_date},
        ))

    async def rejected_on(self, employee_id: UUID | str, work_date: Any) -> int:
        """Jumlah pengajuan absensi yang ditolak pada tanggal itu."""
        return int(await self.scalar(
            """
            SELECT count(*) FROM vms.attendance
            WHERE employee_id = :emp AND work_date = :day AND status = 'REJECTED'
            """,
            {"emp": employee_id, "day": work_date},
        ) or 0)

    async def site_for_check_in(self, site_id: UUID | str, org_id: UUID | str, lng: float, lat: float) -> Any:
        """Nama, unit, jarak (m), dan radius lokasi — rumus sama dengan trigger `attendance_geofence`,
        dipakai untuk mewajibkan penjelasan sebelum insert. Status tetap diputuskan trigger."""
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
        # radius_m NOT NULL diisi trigger; nilai 0 hanya pengisi sebelum trigger berjalan.
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
                      distance_m, is_late, is_early_leave, status, explanation, reviewed_at, selfie_file_id
            """,
            {"org": org_id, "emp": employee_id, "day": work_date, "site": site_id, "label": site_label,
             "lng": lng, "lat": lat, "origin": origin, "selfie": selfie_file_id,
             "face": face_result, "sim": face_similarity, "source": source, "exp": explanation, "at": at},
        )

    async def close(self, attendance_id: UUID | str) -> Any:
        return await self.fetchone(
            """
            UPDATE vms.attendance SET check_out_at = now() WHERE id = :id
            RETURNING id, employee_id, work_date, site_id, site_label, check_in_at, check_out_at,
                      distance_m, is_late, is_early_leave, status, explanation, reviewed_at, selfie_file_id
            """,
            {"id": attendance_id},
        )

    async def get(self, attendance_id: UUID | str, org_id: UUID | str) -> Any:
        return await self.fetchone(
            """
            SELECT id, employee_id, work_date, site_id, site_label, check_in_at, check_out_at,
                   distance_m, is_late, is_early_leave, status, explanation, reviewed_at, selfie_file_id
            FROM vms.attendance WHERE id = :id AND organization_id = :org
            FOR UPDATE
            """,
            {"id": attendance_id, "org": org_id},
        )

    async def can_review(self, viewer_user_id: UUID | str, employee_id: UUID | str) -> bool:
        return bool(await self.scalar(
            "SELECT vms.attendance_can_review(CAST(:viewer AS uuid), CAST(:emp AS uuid))",
            {"viewer": str(viewer_user_id), "emp": str(employee_id)},
        ))

    async def list_page(self, org_id: str, viewer_user_id: str, *, view_all: bool, employee_id: Any,
                        date_from: Any, date_to: Any, status: str | None,
                        limit: int, offset: int) -> tuple[list[Any], int]:
        """Absensi dalam cakupan LIHAT peminta (R-33), terbaru dulu, + `can_review` per baris. → (baris, total)."""
        params = {"org": org_id, "viewer": viewer_user_id, "view_all": view_all, "emp": employee_id,
                  "date_from": date_from, "date_to": date_to, "status": status,
                  "limit": limit, "offset": offset}
        rows = await self.fetchall(
            """
            SELECT a.id, a.employee_id, a.work_date, a.site_id, a.site_label, a.check_in_at, a.check_out_at,
                   a.distance_m, a.is_late, a.is_early_leave, a.status, a.explanation, a.reviewed_at,
                   a.selfie_file_id, a.review_note, e.full_name AS employee_name,
                   a.offline, a.offline_note, a.check_out_requested_at,
                   vms.attendance_can_review(CAST(:viewer AS uuid), a.employee_id) AS can_review
            FROM vms.attendance a JOIN vms.employee e ON e.id = a.employee_id
            WHERE a.organization_id = CAST(:org AS uuid)
              AND vms.attendance_viewable(CAST(:viewer AS uuid), CAST(:view_all AS boolean), a.employee_id)
              AND (CAST(:emp AS uuid) IS NULL OR a.employee_id = CAST(:emp AS uuid))
              AND (CAST(:date_from AS date) IS NULL OR a.work_date >= CAST(:date_from AS date))
              AND (CAST(:date_to AS date) IS NULL OR a.work_date <= CAST(:date_to AS date))
              AND (CAST(:status AS text) IS NULL OR CAST(a.status AS text) = CAST(:status AS text))
            ORDER BY a.work_date DESC, a.check_in_at DESC
            LIMIT :limit OFFSET :offset
            """,
            params,
        )
        total = await self.scalar(
            """
            SELECT count(*) FROM vms.attendance a
            WHERE a.organization_id = CAST(:org AS uuid)
              AND vms.attendance_viewable(CAST(:viewer AS uuid), CAST(:view_all AS boolean), a.employee_id)
              AND (CAST(:emp AS uuid) IS NULL OR a.employee_id = CAST(:emp AS uuid))
              AND (CAST(:date_from AS date) IS NULL OR a.work_date >= CAST(:date_from AS date))
              AND (CAST(:date_to AS date) IS NULL OR a.work_date <= CAST(:date_to AS date))
              AND (CAST(:status AS text) IS NULL OR CAST(a.status AS text) = CAST(:status AS text))
            """,
            params,
        )
        return list(rows), int(total or 0)

    async def set_explanation(self, attendance_id: UUID | str, explanation: str) -> None:
        await self.execute("UPDATE vms.attendance SET explanation = :exp WHERE id = :id",
                           {"exp": explanation, "id": attendance_id})

    async def set_review(self, attendance_id: UUID | str, status: str, reviewer: Any, note: str) -> None:
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
