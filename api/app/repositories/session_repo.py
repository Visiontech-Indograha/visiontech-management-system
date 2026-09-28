"""
app/repositories/session_repo.py
Sesi login dan percobaan masuk — membungkus fungsi di db/04_signature_auth.sql.
Refresh token mentah tidak pernah disimpan; basis data hanya menyimpan SHA-256-nya.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base_repo import BaseRepo

# Sama dengan default vms.login_is_locked (db/04_signature_auth.sql): 5 gagal dalam 15 menit → terkunci.
MAX_LOGIN_FAILURES = 5
LOCK_WINDOW = "15 minutes"

# Kegagalan dalam jendela + kapan kunci lepas: saat kegagalan ke-5 terbaru keluar dari jendela.
# Pemanggil menyediakan `{login}` (parameter atau kolom berkorelasi).
FAILED_LOGINS_SQL = f"""
    SELECT count(*)::int AS failures,
           CASE WHEN count(*) >= {MAX_LOGIN_FAILURES}
                THEN (array_agg(attempted_at ORDER BY attempted_at DESC))[{MAX_LOGIN_FAILURES}]
                     + interval '{LOCK_WINDOW}' END AS locked_until
    FROM vms.login_attempt
    WHERE login = {{login}} AND NOT successful AND attempted_at > now() - interval '{LOCK_WINDOW}'
"""


class SessionRepo(BaseRepo):

    async def failed_logins(self, login: str) -> Any:
        """(failures, locked_until, retry_after_seconds) — dihitung dengan jam basis data."""
        return await self.fetchone(
            f"""
            SELECT f.failures, f.locked_until,
                   GREATEST(0, CEIL(EXTRACT(EPOCH FROM f.locked_until - now())))::int AS retry_after_seconds
            FROM ({FAILED_LOGINS_SQL.format(login=":login")}) f
            """,
            {"login": login},
        )

    async def record_login_attempt(
        self, login: str, ip: str | None, successful: bool, reason: str | None = None
    ) -> None:
        await self.execute(
            """
            INSERT INTO vms.login_attempt (login, ip_address, successful, reason)
            VALUES (:login, :ip, :successful, :reason)
            """,
            {"login": login, "ip": ip, "successful": successful, "reason": reason},
        )

    async def issue(
        self,
        org_id: UUID | str,
        user_id: UUID | str,
        device_label: str,
        fingerprint: str | None,
        ip: str | None,
        user_agent: str,
    ) -> Any:
        """Kembalikan (session_id, family_id, refresh_token, expires_at)."""
        return await self.fetchone(
            """
            SELECT session_id, family_id, refresh_token, expires_at
            FROM vms.issue_session(:org, :user_id, :device, :fingerprint, :ip, :agent)
            """,
            {
                "org": org_id, "user_id": user_id, "device": device_label,
                "fingerprint": fingerprint, "ip": ip, "agent": user_agent,
            },
        )

    async def rotate(self, raw_refresh_token: str, ip: str | None, user_agent: str) -> Any:
        """
        Kembalikan (session_id, user_id, refresh_token, expires_at, reused).
        Token tak dikenal → session_id NULL. Token lama dipakai ulang → reused = true dan
        seluruh rantai perangkat sudah dicabut oleh fungsi basis data.
        """
        return await self.fetchone(
            """
            SELECT session_id, user_id, refresh_token, expires_at, reused
            FROM vms.rotate_session(:rt, :ip, :agent)
            """,
            {"rt": raw_refresh_token, "ip": ip, "agent": user_agent},
        )

    async def revoke_by_refresh_token(self, raw_refresh_token: str, reason: str) -> None:
        await self.execute(
            """
            UPDATE vms.user_session
               SET state = 'REVOKED', revoked_at = now(), revoked_reason = :reason
             WHERE refresh_sha256 = digest(:rt, 'sha256') AND state = 'ACTIVE'
            """,
            {"rt": raw_refresh_token, "reason": reason},
        )

    async def list_active(self, user_id: UUID | str) -> list[Any]:
        """Satu baris per perangkat (rantai rotasi): sesi AKTIF belum kedaluwarsa; `issued_at` = masuk
        pertama kali di perangkat itu, bukan rotasi terakhir."""
        return list(await self.fetchall(
            """
            SELECT CAST(s.id AS text) AS id, s.device_label, CAST(host(s.ip_address) AS text) AS ip_address,
                   s.user_agent, s.last_used_at,
                   (SELECT min(f.issued_at) FROM vms.user_session f WHERE f.family_id = s.family_id) AS issued_at
            FROM vms.user_session s
            WHERE s.user_id = :uid AND s.state = 'ACTIVE' AND s.expires_at > now()
            ORDER BY COALESCE(s.last_used_at, s.issued_at) DESC
            """,
            {"uid": user_id}))

    async def revoke_session(self, user_id: UUID | str, session_id: UUID | str, reason: str) -> bool:
        """Cabut satu perangkat milik pengguna ini. False bila bukan miliknya / sudah tidak aktif."""
        revoked = await self.scalar(
            """
            WITH target AS (SELECT family_id FROM vms.user_session
                            WHERE id = :sid AND user_id = :uid AND state = 'ACTIVE')
            UPDATE vms.user_session s SET state = 'REVOKED', revoked_at = now(), revoked_reason = :reason
            FROM target WHERE s.family_id = target.family_id AND s.state = 'ACTIVE'
            RETURNING 1
            """,
            {"sid": session_id, "uid": user_id, "reason": reason})
        return bool(revoked)

    async def revoke_other_sessions(self, user_id: UUID | str, keep_session_id: UUID | str, reason: str) -> int:
        """Cabut semua perangkat lain; rantai sesi yang sedang dipakai tetap."""
        rows = await self.fetchall(
            """
            UPDATE vms.user_session SET state = 'REVOKED', revoked_at = now(), revoked_reason = :reason
            WHERE user_id = :uid AND state = 'ACTIVE'
              AND family_id IS DISTINCT FROM (SELECT family_id FROM vms.user_session WHERE id = :keep)
            RETURNING id
            """,
            {"uid": user_id, "keep": keep_session_id, "reason": reason})
        return len(rows)

    async def revoke_all_for_user(self, user_id: UUID | str, reason: str) -> int:
        return int(await self.scalar(
            "SELECT vms.revoke_sessions(:uid, :reason)", {"uid": user_id, "reason": reason}
        ) or 0)
