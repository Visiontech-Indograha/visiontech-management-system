"""
app/repositories/attendance_session_repo.py
Sesi absensi (V-12). Jarak, radius, status, terlambat, dan pulang cepat TIDAK ditulis di sini —
trigger `attendance_geofence` / `attendance_checkout` (db/02) yang menghitungnya dari jam & lokasi
server; aplikasi hanya membaca hasilnya kembali. SQL ditulis utuh (bukan f-string) agar diperiksa V-01.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base_repo import BaseRepo


class AttendanceSessionRepo(BaseRepo):

    async def employee_of(self, user_id: UUID | str) -> Any:
        return await self.scalar("SELECT employee_id FROM vms.app_user WHERE id = :uid", {"uid": user_id})

    async def open_session(self, employee_id: UUID | str) -> Any:
        """Sesi terbuka terbaru (belum check-out, tidak ditolak) — tanggal berapa pun."""
        return await self.fetchone(
            """
            SELECT id, employee_id, work_date, site_id, site_label, check_in_at, check_out_at,
                   distance_m, is_late, is_early_leave, status, explanation, reviewed_at
            FROM vms.attendance
            WHERE employee_id = :emp AND check_out_at IS NULL AND status <> 'REJECTED'
            ORDER BY check_in_at DESC LIMIT 1
            """,
            {"emp": employee_id},
        )

    async def active_on(self, employee_id: UUID | str, work_date: Any) -> bool:
        return bool(await self.scalar(
            """
            SELECT EXISTS (SELECT 1 FROM vms.attendance
                           WHERE employee_id = :emp AND work_date = :day AND status <> 'REJECTED')
            """,
            {"emp": employee_id, "day": work_date},
        ))

    async def site_label(self, site_id: UUID | str, org_id: UUID | str) -> Any:
        return await self.scalar(
            "SELECT name FROM vms.site WHERE id = :site AND organization_id = :org AND deleted_at IS NULL",
            {"site": site_id, "org": org_id},
        )

    async def insert(self, *, org_id: str, employee_id: Any, work_date: Any, site_id: UUID, site_label: str,
                     lng: float, lat: float, origin: str, selfie_file_id: UUID | None,
                     face_result: str | None, face_similarity: float | None) -> Any:
        # radius_m NOT NULL diisi trigger; nilai 0 hanya pengisi sebelum trigger berjalan.
        return await self.fetchone(
            """
            INSERT INTO vms.attendance (
                organization_id, employee_id, work_date, site_id, site_label, check_in_at,
                location, location_origin, radius_m, selfie_file_id, face_result, face_similarity
            ) VALUES (
                :org, :emp, :day, :site, :label, now(),
                ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography, :origin, 0, :selfie, :face, :sim
            )
            RETURNING id, employee_id, work_date, site_id, site_label, check_in_at, check_out_at,
                      distance_m, is_late, is_early_leave, status, explanation, reviewed_at
            """,
            {"org": org_id, "emp": employee_id, "day": work_date, "site": site_id, "label": site_label,
             "lng": lng, "lat": lat, "origin": origin, "selfie": selfie_file_id,
             "face": face_result, "sim": face_similarity},
        )

    async def close(self, attendance_id: UUID | str) -> Any:
        return await self.fetchone(
            """
            UPDATE vms.attendance SET check_out_at = now() WHERE id = :id
            RETURNING id, employee_id, work_date, site_id, site_label, check_in_at, check_out_at,
                      distance_m, is_late, is_early_leave, status, explanation, reviewed_at
            """,
            {"id": attendance_id},
        )

    async def get(self, attendance_id: UUID | str, org_id: UUID | str) -> Any:
        return await self.fetchone(
            """
            SELECT id, employee_id, work_date, site_id, site_label, check_in_at, check_out_at,
                   distance_m, is_late, is_early_leave, status, explanation, reviewed_at
            FROM vms.attendance WHERE id = :id AND organization_id = :org
            FOR UPDATE
            """,
            {"id": attendance_id, "org": org_id},
        )

    async def list_page(self, org_id: str, *, employee_id: Any, date_from: Any, date_to: Any,
                        status: str | None, limit: int, offset: int) -> tuple[list[Any], int]:
        """Absensi organisasi dengan filter opsional (NULL = semua), terbaru dulu. → (baris, total)."""
        params = {"org": org_id, "emp": employee_id, "date_from": date_from, "date_to": date_to,
                  "status": status, "limit": limit, "offset": offset}
        rows = await self.fetchall(
            """
            SELECT id, employee_id, work_date, site_id, site_label, check_in_at, check_out_at,
                   distance_m, is_late, is_early_leave, status, explanation, reviewed_at
            FROM vms.attendance
            WHERE organization_id = CAST(:org AS uuid)
              AND (CAST(:emp AS uuid) IS NULL OR employee_id = CAST(:emp AS uuid))
              AND (CAST(:date_from AS date) IS NULL OR work_date >= CAST(:date_from AS date))
              AND (CAST(:date_to AS date) IS NULL OR work_date <= CAST(:date_to AS date))
              AND (CAST(:status AS text) IS NULL OR CAST(status AS text) = CAST(:status AS text))
            ORDER BY work_date DESC, check_in_at DESC
            LIMIT :limit OFFSET :offset
            """,
            params,
        )
        total = await self.scalar(
            """
            SELECT count(*) FROM vms.attendance
            WHERE organization_id = CAST(:org AS uuid)
              AND (CAST(:emp AS uuid) IS NULL OR employee_id = CAST(:emp AS uuid))
              AND (CAST(:date_from AS date) IS NULL OR work_date >= CAST(:date_from AS date))
              AND (CAST(:date_to AS date) IS NULL OR work_date <= CAST(:date_to AS date))
              AND (CAST(:status AS text) IS NULL OR CAST(status AS text) = CAST(:status AS text))
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
                review_note = :note
            WHERE id = :id
            """,
            {"status": status, "emp": reviewer, "note": note, "id": attendance_id},
        )
