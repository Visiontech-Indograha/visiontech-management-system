"""
app/modules/attendance/repositories/attendance_offline_repository.py
Absensi lapangan offline — Master Schema V2, tanpa tabel tambahan.

- Data absen tetap di `attendance` (sama dengan online).
- Kunci publik perangkat & event offline adalah jejak audit di `app_activity_logs` (relasi lewat
  `entity_table`/`entity_id`, indeks `idx_activity_logs_entity`):
    * `DEVICE_KEY_REGISTERED` — entity `users`/user_id, `changed_diff` = {device_id, public_key}
    * `OFFLINE_ATTENDANCE`    — entity `attendance_offline`/client_op_id (idempotensi kiriman ulang),
                                `changed_diff` = {kind, attendance_id, event_time, time_trusted, result}
- Hash swafoto dari `file_object.sha256`.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository

_STATUS = """
    CASE
        WHEN om_approval_status = 'AUTO_VALID' THEN 'AUTO_VALID'
        WHEN om_approval_status = 'APPROVED_BY_OM' THEN 'APPROVED'
        WHEN om_approval_status = 'REJECTED_BY_OM' THEN 'REJECTED'
        ELSE 'NEEDS_REVIEW'
    END
"""


class AttendanceOfflineRepository(BaseRepository):
    """Repositori absensi offline (perangkat terdaftar, event idempoten, penutupan sesi)."""

    async def device_key(self, user_id: UUID | str, device_id: str) -> str | None:
        """Kunci publik terbaru yang didaftarkan perangkat ini untuk akun ini."""
        key: str | None = await self.scalar(
            """
            SELECT changed_diff ->> 'public_key'
            FROM app_activity_logs
            WHERE entity_table = 'users' AND entity_id = CAST(:uid AS uuid)
              AND action = 'DEVICE_KEY_REGISTERED' AND changed_diff ->> 'device_id' = :device
            ORDER BY created_at DESC
            LIMIT 1
            """,
            {"uid": str(user_id), "device": device_id},
        )
        return key

    async def register_device_key(
        self, org_id: UUID | str, user_id: UUID | str, device_id: str, public_key: str
    ) -> None:
        """Catat kunci publik perangkat (pendaftaran ulang = baris baru; yang terbaru berlaku)."""
        await self.execute(
            """
            INSERT INTO app_activity_logs (
                actor_user_id, actor_role, platform, action, entity_table, entity_id, changed_diff
            )
            SELECT u.user_id, u.system_role::text, 'android_flutter', 'DEVICE_KEY_REGISTERED', 'users', u.user_id,
                   CAST(:diff AS jsonb)
            FROM users u
            WHERE u.user_id = CAST(:uid AS uuid)
            """,
            {"uid": str(user_id), "diff": json.dumps({"device_id": device_id, "public_key": public_key})},
        )

    async def event(self, client_op_id: UUID | str) -> Any:
        """Event offline yang sudah diproses (untuk kiriman ulang) → user_id, result, attendance_id; None bila baru."""
        return await self.fetchone(
            """
            SELECT actor_user_id AS user_id,
                   changed_diff ->> 'result' AS result,
                   CAST(changed_diff ->> 'attendance_id' AS uuid) AS attendance_id
            FROM app_activity_logs
            WHERE entity_table = 'attendance_offline' AND entity_id = CAST(:op AS uuid)
              AND action = 'OFFLINE_ATTENDANCE'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            {"op": str(client_op_id)},
        )

    async def record_event(
        self,
        *,
        client_op_id: UUID | str,
        org_id: UUID | str,
        user_id: UUID | str,
        kind: str,
        attendance_id: UUID | str | None,
        event_time: datetime,
        time_trusted: bool,
        result: str,
    ) -> None:
        """Catat hasil pemrosesan event offline (dasar idempotensi)."""
        await self.execute(
            """
            INSERT INTO app_activity_logs (
                actor_user_id, actor_role, platform, action, entity_table, entity_id, changed_diff
            )
            SELECT u.user_id, u.system_role::text, 'android_flutter', 'OFFLINE_ATTENDANCE', 'attendance_offline',
                   CAST(:op AS uuid), CAST(:diff AS jsonb)
            FROM users u
            WHERE u.user_id = CAST(:uid AS uuid)
            """,
            {
                "uid": str(user_id),
                "op": str(client_op_id),
                "diff": json.dumps({
                    "kind": kind,
                    "attendance_id": str(attendance_id) if attendance_id else None,
                    "event_time": event_time.isoformat(),
                    "time_trusted": time_trusted,
                    "result": result,
                }),
            },
        )

    async def file_sha256(self, file_id: UUID | str, org_id: UUID | str) -> str | None:
        """SHA-256 (hex) berkas yang diunggah — pembanding hash swafoto yang ditandatangani HP."""
        digest: str | None = await self.scalar(
            "SELECT encode(sha256, 'hex') FROM file_object WHERE id = CAST(:fid AS uuid)",
            {"fid": str(file_id)},
        )
        return digest

    async def local_date(self, org_id: UUID | str, at: datetime) -> Any:
        """Tanggal kerja peristiwa menurut WIB (zona seluruh kantor Visiontech)."""
        return await self.scalar(
            "SELECT (CAST(:at AS timestamptz) AT TIME ZONE 'Asia/Jakarta')::date",
            {"at": at},
        )

    async def mark_offline(self, attendance_id: UUID | str, note: str | None, force_review: bool) -> Any:
        """Tandai absen hasil sinkron offline: catatan alasan + naik ke antrean OM bila ada kejanggalan."""
        return await self.fetchone(
            f"""
            UPDATE attendance
            SET out_of_radius_note = NULLIF(concat_ws('; ', out_of_radius_note, CAST(:note AS text)), ''),
                om_approval_status = CASE
                    WHEN CAST(:force AS boolean) AND om_approval_status = 'AUTO_VALID' THEN 'PENDING_OM'
                    ELSE om_approval_status
                END,
                update_at = now()
            WHERE attendance_id = CAST(:id AS uuid) AND delete_at IS NULL
            RETURNING attendance_id AS id, {_STATUS} AS status
            """,
            {"id": str(attendance_id), "note": note, "force": force_review},
        )

    async def open_before(self, employee_id: UUID | str, at: datetime) -> Any:
        """Absen masuk yang belum ditutup dan terjadi sebelum `at` (target absen pulang offline)."""
        return await self.fetchone(
            f"""
            SELECT attendance_id AS id, {_STATUS} AS status, clock_in_at AS check_in_at
            FROM attendance
            WHERE employee_id = CAST(:emp AS uuid) AND clock_out_at IS NULL
              AND om_approval_status <> 'REJECTED_BY_OM'
              AND clock_in_at <= :at AND delete_at IS NULL
            ORDER BY clock_in_at DESC
            LIMIT 1
            """,
            {"emp": str(employee_id), "at": at},
        )

    async def close_at(
        self, attendance_id: UUID | str, at: datetime, *, lat: float | None = None, lng: float | None = None
    ) -> None:
        """Tutup sesi pada jam peristiwa offline (V2 tidak menyimpan koordinat pulang)."""
        await self.execute(
            "UPDATE attendance SET clock_out_at = :at, update_at = now() "
            "WHERE attendance_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"at": at, "id": str(attendance_id)},
        )

    async def request_checkout(self, attendance_id: UUID | str, at: datetime) -> None:
        """Absen masuk masih menunggu OM: jam pulang tetap dicatat; keputusan OM berlaku untuk seluruh absen."""
        await self.close_at(attendance_id, at)


CRUDAttendanceOffline = AttendanceOfflineRepository
