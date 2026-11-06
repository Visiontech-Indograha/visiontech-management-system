"""
app/shared/device_credential_repository.py

Kredensial perangkat (tabel `device_credential`) untuk masuk dengan sidik jari. Token mentah tidak pernah
disimpan atau dicatat: hanya SHA-256-nya. Dipakai modul auth, akun, dan penugasan peran (pencabutan).
Tidak commit: transaksi milik permintaan. Audit (terbit/pakai/cabut) ke `app_activity_logs` tanpa token.
"""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
from collections import namedtuple
from typing import Any
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from app.core.repository import BaseRepository

logger = logging.getLogger(__name__)

CREDENTIAL_DAYS = 30

Consumed = namedtuple("Consumed", ["credential_id", "user_id", "device_name"])
Issued = namedtuple("Issued", ["credential_id", "expires_at"])
Known = namedtuple("Known", ["credential_id", "user_id", "device_name", "revoked_reason", "expires_at"])


def new_token() -> str:
    """Token acak 256-bit (43 karakter URL-safe)."""
    return secrets.token_urlsafe(32)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class DeviceCredentialRepository(BaseRepository):
    async def _audit(
        self, ids: list[UUID], user_id: UUID | str, action: str, *, ip: str | None = None, **diff: Any
    ) -> None:
        """Catat ke jejak audit. Gagal mencatat tidak boleh menggagalkan proses (SAVEPOINT)."""
        if not ids:
            return
        try:
            async with self.db.begin_nested():
                await self.execute(
                    """
                    INSERT INTO app_activity_logs (
                        actor_user_id, actor_role, platform, action, entity_table, entity_id, changed_diff,
                        ip_address
                    )
                    SELECT CAST(:uid AS uuid), 'USER', 'android_flutter', :action, 'device_credential', t.id,
                           CAST(:diff AS jsonb), CAST(:ip AS inet)
                    FROM unnest(CAST(:ids AS uuid[])) AS t(id)
                    """,
                    {"uid": str(user_id), "action": action, "ids": ids, "ip": ip,
                     "diff": json.dumps(diff, default=str)},
                )
        except SQLAlchemyError:
            logger.exception("Audit kredensial perangkat tidak dapat dicatat")

    async def _revoke(self, where: str, params: dict[str, Any], reason: str, user_id: UUID | str) -> int:
        rows = await self.fetchall(
            f"""
            UPDATE device_credential
            SET revoked_at = now(), revoked_reason = :reason
            WHERE revoked_at IS NULL AND delete_at IS NULL AND {where}
            RETURNING credential_id, user_id
            """,
            {**params, "reason": reason},
        )
        ids = [r.credential_id for r in rows]
        await self._audit(ids, user_id, "DEVICE_CRED_REVOKED", reason=reason)
        return len(ids)

    async def issue(self, user_id: UUID | str, device_name: str, raw_token: str, ip: str | None = None) -> Issued:
        """Terbitkan kredensial baru; yang aktif untuk (akun, perangkat) yang sama dicabut lebih dulu."""
        await self.revoke_device(user_id, device_name, "REISSUED")
        row = await self.fetchone(
            """
            INSERT INTO device_credential (user_id, device_name, token_hash, expires_at)
            VALUES (CAST(:uid AS uuid), :device, :hash, now() + make_interval(days => :days))
            RETURNING credential_id, expires_at
            """,
            {"uid": str(user_id), "device": device_name[:100], "hash": hash_token(raw_token),
             "days": CREDENTIAL_DAYS},
        )
        await self._audit([row.credential_id], user_id, "DEVICE_CRED_ISSUED", ip=ip, device=device_name[:100])
        return Issued(row.credential_id, row.expires_at)

    async def consume(self, raw_token: str, ip: str | None = None) -> Consumed | None:
        """Pakai token sekali: UPDATE bersyarat (hanya satu pemakaian serentak yang berhasil) lalu catat."""
        row = await self.fetchone(
            """
            UPDATE device_credential
            SET revoked_at = now(), revoked_reason = 'ROTATED', last_used_at = now()
            WHERE token_hash = :hash AND revoked_at IS NULL AND delete_at IS NULL AND expires_at > now()
            RETURNING credential_id, user_id, device_name
            """,
            {"hash": hash_token(raw_token)},
        )
        if row is None:
            return None
        await self._audit([row.credential_id], row.user_id, "DEVICE_CRED_USED", ip=ip)
        return Consumed(row.credential_id, row.user_id, row.device_name)

    async def lookup(self, raw_token: str) -> Known | None:
        """Baris untuk token ini apa adanya (termasuk yang sudah dicabut/kedaluwarsa), untuk deteksi pemakaian ulang."""
        row = await self.fetchone(
            "SELECT credential_id, user_id, device_name, revoked_reason, expires_at FROM device_credential "
            "WHERE token_hash = :hash AND delete_at IS NULL",
            {"hash": hash_token(raw_token)},
        )
        if row is None:
            return None
        return Known(row.credential_id, row.user_id, row.device_name, row.revoked_reason, row.expires_at)

    async def note_reuse(self, credential_id: UUID, user_id: UUID | str, device_name: str, ip: str | None) -> None:
        """Token yang sudah dirotasi dipakai lagi (kemungkinan bocor): kredensial aktif perangkat itu dicabut."""
        await self.revoke_device(user_id, device_name, "REUSE_DETECTED")
        await self._audit([credential_id], user_id, "DEVICE_CRED_REUSE", ip=ip, device=device_name)

    async def revoke_user(self, user_id: UUID | str, reason: str) -> int:
        """Semua kredensial akun (ganti sandi, nonaktif, hapus, peran dicabut)."""
        return await self._revoke("user_id = CAST(:uid AS uuid)", {"uid": str(user_id)}, reason, user_id)

    async def revoke_device(self, user_id: UUID | str, device_name: str, reason: str) -> int:
        return await self._revoke(
            "user_id = CAST(:uid AS uuid) AND device_name = :device",
            {"uid": str(user_id), "device": device_name[:100]}, reason, user_id,
        )

    async def revoke_other_devices(self, user_id: UUID | str, keep_session_id: UUID | str, reason: str) -> int:
        return await self._revoke(
            "user_id = CAST(:uid AS uuid) AND device_name IS DISTINCT FROM "
            "(SELECT device_name FROM user_sessions WHERE session_id = CAST(:sid AS uuid))",
            {"uid": str(user_id), "sid": str(keep_session_id)}, reason, user_id,
        )

    async def revoke_for_session(self, user_id: UUID | str, session_id: UUID | str, reason: str) -> int:
        """Kredensial perangkat milik sesi ini (perangkat dikeluarkan dari daftar sesi)."""
        return await self._revoke(
            "user_id = CAST(:uid AS uuid) AND device_name = "
            "(SELECT device_name FROM user_sessions WHERE session_id = CAST(:sid AS uuid) "
            "AND user_id = CAST(:uid AS uuid))",
            {"uid": str(user_id), "sid": str(session_id)}, reason, user_id,
        )

    async def revoke_for_refresh_hash(self, refresh_hash: str, reason: str) -> int:
        """Logout: kredensial perangkat milik sesi dengan refresh token ini."""
        row = await self.fetchone(
            "SELECT user_id, device_name FROM user_sessions WHERE refresh_token_hash = :h", {"h": refresh_hash}
        )
        if row is None:
            return 0
        return await self.revoke_device(row.user_id, row.device_name, reason)

