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

    async def device_key(self, user_id: UUID | str, device_id: str) -> Any:
        return await self.scalar(
            """
            SELECT public_key FROM vms.attendance_device_key
            WHERE user_id = CAST(:user AS uuid) AND device_id = :device AND revoked_at IS NULL
            """,
            {"user": str(user_id), "device": device_id},
        )

    async def register_device_key(self, org_id: UUID | str, user_id: UUID | str, device_id: str,
                                  public_key: str) -> None:
        """Satu kunci aktif per akun & perangkat; kunci lama dicabut (bukan dihapus — jejak tetap ada)."""
        await self.execute(
            """
            UPDATE vms.attendance_device_key SET revoked_at = now()
            WHERE user_id = CAST(:user AS uuid) AND device_id = :device AND revoked_at IS NULL
              AND public_key <> :key
            """,
            {"user": str(user_id), "device": device_id, "key": public_key},
        )
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
        return await self.scalar(
            "SELECT encode(sha256, 'hex') FROM vms.file_object WHERE id = CAST(:id AS uuid) "
            "AND organization_id = CAST(:org AS uuid)",
            {"id": str(file_id), "org": str(org_id)},
        )

    async def local_date(self, org_id: UUID | str, at: datetime) -> Any:
        """Tanggal kerja peristiwa menurut zona waktu organisasi."""
        return await self.scalar(
            "SELECT (CAST(:at AS timestamptz) AT TIME ZONE o.timezone)::date FROM vms.organization o "
            "WHERE o.id = CAST(:org AS uuid)",
            {"at": at, "org": str(org_id)},
        )

    async def mark_offline(self, attendance_id: UUID | str, note: str | None, force_review: bool) -> Any:
        """Tandai absensi luring; bila ada alasan (jam tak terverifikasi, terlambat sinkron, lokasi palsu)
        status yang valid otomatis diturunkan ke Perlu review."""
        return await self.fetchone(
            """
            UPDATE vms.attendance
            SET offline = true, offline_note = :note,
                status = CASE WHEN :force AND status = 'AUTO_VALID'
                              THEN CAST('NEEDS_REVIEW' AS vms.attendance_status) ELSE status END
            WHERE id = CAST(:id AS uuid)
            RETURNING id, employee_id, work_date, site_id, site_label, check_in_at, check_out_at,
                      distance_m, is_late, is_early_leave, status, explanation, reviewed_at, selfie_file_id
            """,
            {"id": str(attendance_id), "note": note, "force": force_review},
        )

    async def open_before(self, employee_id: UUID | str, at: datetime) -> Any:
        """Absen masuk terakhir yang belum ditutup & tidak ditolak, sebelum jam pulang luring."""
        return await self.fetchone(
            """
            SELECT id, status, check_in_at FROM vms.attendance
            WHERE employee_id = CAST(:emp AS uuid) AND check_out_at IS NULL AND status <> 'REJECTED'
              AND check_out_requested_at IS NULL AND check_in_at <= :at
            ORDER BY check_in_at DESC LIMIT 1
            """,
            {"emp": str(employee_id), "at": at},
        )

    async def close_at(self, attendance_id: UUID | str, at: datetime) -> None:
        await self.execute("UPDATE vms.attendance SET check_out_at = :at WHERE id = CAST(:id AS uuid)",
                           {"at": at, "id": str(attendance_id)})

    async def request_checkout(self, attendance_id: UUID | str, at: datetime) -> None:
        """Absen pulang luring untuk absen masuk yang belum valid — berlaku saat disetujui (R-34)."""
        await self.execute(
            "UPDATE vms.attendance SET check_out_requested_at = :at WHERE id = CAST(:id AS uuid)",
            {"at": at, "id": str(attendance_id)})
