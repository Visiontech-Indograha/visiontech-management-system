"""
app/modules/auth/repositories/auth_session_repository.py
Sesi login (`user_sessions`) dan percobaan masuk (`app_activity_logs`) — Master Schema V2.
Refresh token mentah tidak pernah disimpan; basis data hanya menyimpan SHA-256-nya.

Percobaan masuk dicatat sebagai baris audit `action = LOGIN_FAILED | LOGIN_SUCCESS`, `entity_table = 'users'`,
`entity_id = uuid5(email)`: login terdaftar maupun tidak dihitung sama (tidak membocorkan keberadaan akun),
email mentah tidak disimpan, dan hitungan memakai indeks `idx_activity_logs_entity` yang sudah ada.
"""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
from collections import namedtuple
from datetime import timedelta
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy.exc import SQLAlchemyError

from app.core.repository import BaseRepository
from app.core.time import utcnow

logger = logging.getLogger(__name__)

MAX_LOGIN_FAILURES = 5
LOCK_MINUTES = 15

LoginState = namedtuple("LoginState", ["failures", "locked_until", "retry_after_seconds"])
SessionIssueResult = namedtuple("SessionIssueResult", ["session_id", "family_id", "refresh_token", "expires_at"])
SessionRotateResult = namedtuple(
    "SessionRotateResult", ["session_id", "user_id", "refresh_token", "expires_at", "reused", "family_created_at"]
)


class AuthSessionRepository(BaseRepository):
    """Repositori sesi pengguna dan token JWT multi-device (tabel user_sessions)."""
    """
    CRUD untuk mengelola sesi otentikasi pengguna pada tabel user_sessions.
    """

    @staticmethod
    def login_key(login: str) -> UUID:
        """Kunci stabil untuk satu identitas login (email/username) tanpa menyimpan teksnya."""
        return uuid5(NAMESPACE_URL, f"vms-login:{login.strip().lower()}")

    async def failed_logins(self, login: str) -> LoginState:
        """Kegagalan beruntun dalam LOCK_MINUTES terakhir sejak login sukses / buka kunci terakhir; ≥ MAX → terkunci."""
        row = await self.fetchone(
            """
            WITH recent AS (
                SELECT action, created_at
                FROM app_activity_logs
                WHERE entity_table = 'users' AND entity_id = :key
                  AND action IN ('LOGIN_FAILED', 'LOGIN_SUCCESS', 'LOGIN_UNLOCKED')
                  AND created_at > now() - make_interval(mins => :mins)
            ), last_ok AS (
                SELECT max(created_at) AS at FROM recent WHERE action <> 'LOGIN_FAILED'
            )
            SELECT failures, locked_until,
                   GREATEST(0, CEIL(EXTRACT(EPOCH FROM locked_until - now())))::int AS retry_after_seconds
            FROM (
                SELECT count(*)::int AS failures,
                       CASE WHEN count(*) >= :max THEN max(r.created_at) + make_interval(mins => :mins) END
                           AS locked_until
                FROM recent r, last_ok
                WHERE r.action = 'LOGIN_FAILED' AND (last_ok.at IS NULL OR r.created_at > last_ok.at)
            ) s
            """,
            {"key": self.login_key(login), "mins": LOCK_MINUTES, "max": MAX_LOGIN_FAILURES},
        )
        # Semua waktu dihitung jam DB (now()) — jam aplikasi bisa selisih beberapa detik dari server DB.
        if row is None or row.locked_until is None or row.retry_after_seconds <= 0:
            return LoginState(failures=int(row.failures) if row else 0, locked_until=None, retry_after_seconds=0)
        return LoginState(
            failures=int(row.failures), locked_until=row.locked_until, retry_after_seconds=int(row.retry_after_seconds)
        )

    async def record_login_attempt(
        self, login: str, ip: str | None, successful: bool, reason: str | None = None,
        *, user_id: UUID | str | None = None, role: str | None = None, platform: str = "web",
        action: str | None = None,
    ) -> None:
        """Catat percobaan masuk ke jejak audit. Gagal mencatat tidak boleh menggagalkan login (SAVEPOINT).
        `action="LOGIN_UNLOCKED"`: buka kunci oleh HR/admin (mis. reset kata sandi)."""
        plat = "android_flutter" if platform == "mobile" else "web_react"
        try:
            async with self.db.begin_nested():
                await self.execute(
                    """
                    INSERT INTO app_activity_logs (
                        actor_user_id, actor_role, platform, action, entity_table, entity_id,
                        changed_diff, ip_address
                    ) VALUES (
                        CAST(:uid AS uuid), :role, CAST(:plat AS client_platform_enum), :action, 'users', :key,
                        CAST(:diff AS jsonb), CAST(:ip AS inet)
                    )
                    """,
                    {
                        "uid": str(user_id) if user_id else None,
                        "role": (role or "ANONYMOUS")[:30],
                        "plat": plat,
                        "action": action or ("LOGIN_SUCCESS" if successful else "LOGIN_FAILED"),
                        "key": self.login_key(login),
                        "diff": json.dumps({"reason": reason} if reason else {}),
                        "ip": ip,
                    },
                )
        except SQLAlchemyError:
            # mis. partisi app_activity_logs bulan berjalan belum dibuat — catat, jangan blokir login.
            logger.exception("Percobaan login tidak dapat dicatat ke app_activity_logs")

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

        plat = "android_flutter" if "android" in platform.lower() or "mobile" in platform.lower() else "web_react"
        device_name = (device_label or user_agent or "Perangkat tanpa nama")[:100]

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

    async def find_active_family_by_device(self, user_id: UUID | str, device_name: str) -> UUID | None:
        """Rantai sesi aktif milik perangkat yang sama (device_name sama) — untuk masuk ulang tanpa ganda."""
        val = await self.scalar(
            """
            SELECT token_family_id
            FROM user_sessions
            WHERE user_id = CAST(:uid AS uuid) AND device_name = :device
              AND is_revoked = FALSE AND expires_at > now() AND delete_at IS NULL
            ORDER BY update_at DESC LIMIT 1
            """,
            {"uid": user_id, "device": device_name[:100]},
        )
        return UUID(str(val)) if val else None

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


# Alias backward compatibility
CRUDSession = AuthSessionRepository
