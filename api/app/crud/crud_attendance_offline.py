"""
app/crud/crud_attendance_offline.py
Absensi lapangan luring Master Schema V2 (tabel attendance & user_sessions).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDAttendanceOffline(CRUDBase):
    """
    Kelas operasi CRUD untuk menangani absensi luring (offline) Master Schema V2.
    """

    async def device_key(self, user_id: UUID | str, device_id: str) -> Any:
        """Kunci publik perangkat pengguna."""
        return "ed25519-device-key-mock"

    async def register_device_key(
        self, org_id: UUID | str, user_id: UUID | str, device_id: str, public_key: str
    ) -> None:
        pass

    async def has_event(self, org_id: UUID | str, event_id: UUID | str) -> bool:
        return False

    async def record_event(
        self,
        org_id: UUID | str,
        user_id: UUID | str,
        event_id: UUID | str,
        event_type: str,
        occurred_at: datetime,
        payload: dict[str, Any],
        raw_payload: str,
        signature: bytes,
    ) -> None:
        await self.execute(
            """
            INSERT INTO app_activity_logs (user_id, action, target_table, target_id, details)
            VALUES (CAST(:uid AS uuid), 'OFFLINE_ATTENDANCE', 'attendance', CAST(:eid AS uuid),
                    jsonb_build_object('type', :type, 'occurred_at', :occ))
            """,
            {"uid": str(user_id), "eid": str(event_id), "type": event_type, "occ": occurred_at.isoformat()},
        )

    async def local_work_date(self, org_id: UUID | str, at: datetime) -> Any:
        return await self.scalar(
            "SELECT (CAST(:at AS timestamptz) AT TIME ZONE 'Asia/Jakarta')::date",
            {"at": at},
        )

    async def mark_offline(self, attendance_id: UUID | str, note: str | None, force_review: bool) -> Any:
        return await self.fetchone(
            """
            UPDATE attendance
            SET notes = NULLIF(concat_ws('; ', notes, CAST(:note AS text)), ''),
                status = CASE WHEN :force AND status = 'AUTO_VALID' THEN 'NEEDS_REVIEW' ELSE status END,
                update_at = now()
            WHERE attendance_id = CAST(:id AS uuid)
            RETURNING attendance_id AS id, employee_id, work_date, office_id AS site_id,
                      'Kantor / Lapangan' AS site_label, check_in_time AS check_in_at,
                      check_out_time AS check_out_at, check_in_distance_m AS distance_m,
                      is_late, is_early_leave, status, notes AS explanation, update_at AS reviewed_at,
                      check_in_photo_path AS selfie_file_id
            """,
            {"id": str(attendance_id), "note": note, "force": force_review},
        )

    async def open_before(self, employee_id: UUID | str, at: datetime) -> Any:
        return await self.fetchone(
            """
            SELECT attendance_id AS id, status, check_in_time AS check_in_at
            FROM attendance
            WHERE employee_id = CAST(:emp AS uuid) AND check_out_time IS NULL AND status <> 'REJECTED'
              AND check_in_time <= :at AND delete_at IS NULL
            ORDER BY check_in_time DESC LIMIT 1
            """,
            {"emp": str(employee_id), "at": at},
        )

    async def close_at(
        self, attendance_id: UUID | str, at: datetime, *, lat: float | None = None, lng: float | None = None
    ) -> None:
        await self.execute(
            """
            UPDATE attendance
            SET check_out_time = :at,
                check_out_lat = :lat,
                check_out_long = :lng,
                update_at = now()
            WHERE attendance_id = CAST(:id AS uuid)
            """,
            {"at": at, "id": str(attendance_id), "lat": lat, "lng": lng},
        )

    async def request_checkout(self, attendance_id: UUID | str, at: datetime) -> None:
        await self.execute(
            """
            UPDATE attendance
            SET check_out_time = :at, update_at = now()
            WHERE attendance_id = CAST(:id AS uuid)
            """,
            {"at": at, "id": str(attendance_id)},
        )
