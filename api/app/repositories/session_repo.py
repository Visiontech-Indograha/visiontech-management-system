"""
app/repositories/session_repo.py
Sesi login dan percobaan masuk — membungkus fungsi di db/04_signature_auth.sql.
Refresh token mentah tidak pernah disimpan; basis data hanya menyimpan SHA-256-nya.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base_repo import BaseRepo


class SessionRepo(BaseRepo):

    async def login_is_locked(self, login: str) -> bool:
        return bool(await self.scalar("SELECT vms.login_is_locked(:login)", {"login": login}))

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

    async def revoke_all_for_user(self, user_id: UUID | str, reason: str) -> int:
        return int(await self.scalar(
            "SELECT vms.revoke_sessions(:uid, :reason)", {"uid": user_id, "reason": reason}
        ) or 0)
