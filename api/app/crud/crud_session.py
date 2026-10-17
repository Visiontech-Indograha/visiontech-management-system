"""
app/crud/crud_session.py
Sesi login dan percobaan masuk menggunakan tabel user_sessions (Master Schema V2).
Refresh token mentah tidak pernah disimpan; basis data hanya menyimpan SHA-256-nya.
"""

from __future__ import annotations

import hashlib
import secrets
from collections import namedtuple
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

from app.core.time import utcnow

from .base import CRUDBase

MAX_LOGIN_FAILURES = 5
LOCK_WINDOW = "15 minutes"

LoginState = namedtuple("LoginState", ["failures", "locked_until", "retry_after_seconds"])
SessionIssueResult = namedtuple("SessionIssueResult", ["session_id", "family_id", "refresh_token", "expires_at"])
SessionRotateResult = namedtuple(
    "SessionRotateResult", ["session_id", "user_id", "refresh_token", "expires_at", "reused", "family_created_at"]
)


class CRUDSession(CRUDBase):
    """
    CRUD untuk mengelola sesi otentikasi pengguna pada tabel user_sessions.
    """

    async def failed_logins(self, login: str) -> Any:
        return LoginState(failures=0, locked_until=None, retry_after_seconds=0)

    async def record_login_attempt(
        self, login: str, ip: str | None, successful: bool, reason: str | None = None
    ) -> None:
        # Percobaan login
        pass

    async def issue(
        self,
        org_id: UUID | str,
        user_id: UUID | str,
        device_label: str,
        fingerprint: str | None,
        ip: str | None,
        user_agent: str,
        platform: str = "web_react",
    ) -> SessionIssueResult:
        session_id = uuid4()
        family_id = uuid4()
        raw_refresh_token = secrets.token_hex(32)
        token_hash = hashlib.sha256(raw_refresh_token.encode("utf-8")).hexdigest()
        expires_at = utcnow() + timedelta(days=7)

        # Map platform string to client_platform_enum
        plat = "android_flutter" if "android" in platform.lower() or "mobile" in platform.lower() else "web_react"
        device_name = (device_label or user_agent or "Web Browser")[:100]

        await self.execute(
            """
            INSERT INTO user_sessions (
                session_id, user_id, token_family_id, refresh_token_hash,
                platform, device_name, ip_address, is_revoked, expires_at
            )
            VALUES (
                :sid, :uid, :fid, :hash, CAST(:plat AS client_platform_enum), :device, CAST(:ip AS inet), FALSE, :exp
            )
            """,
            {
                "sid": session_id,
                "uid": user_id,
                "fid": family_id,
                "hash": token_hash,
                "plat": plat,
                "device": device_name,
                "ip": ip,
                "exp": expires_at,
            },
        )
        return SessionIssueResult(
            session_id=session_id,
            family_id=family_id,
            refresh_token=raw_refresh_token,
            expires_at=expires_at,
        )

    async def rotate(self, raw_refresh_token: str, ip: str | None, user_agent: str) -> SessionRotateResult:
        token_hash = hashlib.sha256(raw_refresh_token.encode("utf-8")).hexdigest()
        row = await self.fetchone(
            """
            SELECT session_id, user_id, token_family_id, platform,
                   device_name, is_revoked, expires_at, create_at, delete_at
            FROM user_sessions
            WHERE refresh_token_hash = :hash
            """,
            {"hash": token_hash},
        )
        if not row:
            return SessionRotateResult(
                session_id=None, user_id=None, refresh_token=None, expires_at=None, reused=False, family_created_at=None
            )

        if row.is_revoked or row.delete_at is not None or row.expires_at < utcnow():
            await self.execute(
                "UPDATE user_sessions SET is_revoked = TRUE, update_at = now() WHERE token_family_id = :fid",
                {"fid": row.token_family_id},
            )
            return SessionRotateResult(
                session_id=row.session_id,
                user_id=row.user_id,
                refresh_token=None,
                expires_at=None,
                reused=True,
                family_created_at=row.create_at,
            )

        await self.execute(
            "UPDATE user_sessions SET is_revoked = TRUE, update_at = now() WHERE session_id = :sid",
            {"sid": row.session_id},
        )

        new_session_id = uuid4()
        new_raw_token = secrets.token_hex(32)
        new_token_hash = hashlib.sha256(new_raw_token.encode("utf-8")).hexdigest()
        new_expires_at = utcnow() + timedelta(days=7)

        await self.execute(
            """
            INSERT INTO user_sessions (
                session_id, user_id, token_family_id, refresh_token_hash,
                platform, device_name, ip_address, is_revoked, expires_at
            )
            VALUES (
                :sid, :uid, :fid, :hash, :plat, :device, CAST(:ip AS inet), FALSE, :exp
            )
            """,
            {
                "sid": new_session_id,
                "uid": row.user_id,
                "fid": row.token_family_id,
                "hash": new_token_hash,
                "plat": row.platform,
                "device": (user_agent or row.device_name)[:100],
                "ip": ip,
                "exp": new_expires_at,
            },
        )

        return SessionRotateResult(
            session_id=new_session_id,
            user_id=row.user_id,
            refresh_token=new_raw_token,
            expires_at=new_expires_at,
            reused=False,
            family_created_at=row.create_at,
        )

    async def count_active_devices(self, user_id: UUID | str) -> int:
        return int(
            await self.scalar(
                """
                SELECT count(DISTINCT token_family_id)::int
                FROM user_sessions
                WHERE user_id = :uid AND is_revoked = FALSE AND expires_at > now() AND delete_at IS NULL
                """,
                {"uid": user_id},
            )
            or 0
        )

    async def ensure_device_limit(self, user_id: UUID | str, limit: int = 4) -> None:
        """Mencabut sesi terlama jika jumlah perangkat aktif telah mencapai batas."""
        active = await self.count_active_devices(user_id)
        if active >= limit:
            oldest_family = await self.scalar(
                """
                SELECT token_family_id
                FROM user_sessions
                WHERE user_id = :uid AND is_revoked = FALSE AND expires_at > now() AND delete_at IS NULL
                ORDER BY create_at ASC LIMIT 1
                """,
                {"uid": user_id},
            )
            if oldest_family:
                await self.revoke_family(user_id, oldest_family, "Batas perangkat tercapai - sesi terlama dikeluarkan")

    async def find_active_family_by_fingerprint(self, user_id: UUID | str, fingerprint: str) -> UUID | None:
        val = await self.scalar(
            """
            SELECT token_family_id
            FROM user_sessions
            WHERE user_id = :uid AND is_revoked = FALSE AND expires_at > now() AND delete_at IS NULL
            ORDER BY update_at DESC LIMIT 1
            """,
            {"uid": user_id},
        )
        return UUID(str(val)) if val else None

    async def revoke_active_by_device(
        self, user_id: UUID | str, fingerprint: str | None, user_agent: str, reason: str
    ) -> int:
        rows = await self.fetchall(
            """
            UPDATE user_sessions
            SET is_revoked = TRUE, update_at = now()
            WHERE user_id = CAST(:uid AS uuid)
              AND is_revoked = FALSE
              AND (
                  device_name = :agent
                  OR device_name = 'Web Login'
                  OR device_name = 'Aplikasi HP'
              )
            RETURNING session_id
            """,
            {"uid": user_id, "agent": (user_agent or "Web")[:100]},
        )
        return len(rows)

    async def revoke_family(self, user_id: UUID | str, family_id: UUID | str, reason: str) -> None:
        await self.execute(
            """
            UPDATE user_sessions
            SET is_revoked = TRUE, update_at = now()
            WHERE user_id = :uid AND token_family_id = :family AND is_revoked = FALSE
            """,
            {"uid": user_id, "family": family_id},
        )

    async def revoke_by_refresh_token(self, raw_refresh_token: str, reason: str) -> None:
        token_hash = hashlib.sha256(raw_refresh_token.encode("utf-8")).hexdigest()
        await self.execute(
            "UPDATE user_sessions SET is_revoked = TRUE, update_at = now() WHERE refresh_token_hash = :hash",
            {"hash": token_hash},
        )

    async def list_active(self, user_id: UUID | str) -> list[Any]:
        return list(
            await self.fetchall(
                """
                SELECT
                    CAST(s.session_id AS text) AS id,
                    s.device_name AS device_label,
                    CAST(host(s.ip_address) AS text) AS ip_address,
                    s.device_name AS user_agent,
                    s.update_at AS last_used_at,
                    s.create_at AS issued_at
                FROM user_sessions s
                WHERE s.user_id = :uid AND s.is_revoked = FALSE AND s.expires_at > now() AND s.delete_at IS NULL
                ORDER BY s.update_at DESC
                """,
                {"uid": user_id},
            )
        )

    async def revoke_session(self, user_id: UUID | str, session_id: UUID | str, reason: str) -> bool:
        revoked = await self.scalar(
            """
            WITH target AS (
                SELECT token_family_id FROM user_sessions
                WHERE session_id = :sid AND user_id = :uid AND is_revoked = FALSE
            )
            UPDATE user_sessions s
            SET is_revoked = TRUE, update_at = now()
            FROM target
            WHERE s.token_family_id = target.token_family_id AND s.is_revoked = FALSE
            RETURNING 1
            """,
            {"sid": session_id, "uid": user_id},
        )
        return bool(revoked)

    async def revoke_other_sessions(self, user_id: UUID | str, keep_session_id: UUID | str, reason: str) -> int:
        rows = await self.fetchall(
            """
            UPDATE user_sessions
            SET is_revoked = TRUE, update_at = now()
            WHERE user_id = :uid AND is_revoked = FALSE
              AND token_family_id IS DISTINCT FROM (SELECT token_family_id FROM user_sessions WHERE session_id = :keep)
            RETURNING session_id
            """,
            {"uid": user_id, "keep": keep_session_id},
        )
        return len(rows)

    async def revoke_all_for_user(self, user_id: UUID | str, reason: str) -> int:
        rows = await self.fetchall(
            """
            UPDATE user_sessions
            SET is_revoked = TRUE, update_at = now()
            WHERE user_id = :uid AND is_revoked = FALSE
            RETURNING session_id
            """,
            {"uid": user_id},
        )
        return len(rows)
