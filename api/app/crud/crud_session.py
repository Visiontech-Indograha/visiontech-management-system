"""
app/crud/crud_session.py
Sesi login dan percobaan masuk — membungkus fungsi di db/04_signature_auth.sql.
Refresh token mentah tidak pernah disimpan; basis data hanya menyimpan SHA-256-nya.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base import CRUDBase

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


class CRUDSession(CRUDBase):
    """
    CRUD untuk mengelola sesi otentikasi pengguna, termasuk login,
    pembuatan sesi, rotasi token, dan pencabutan sesi aktif.
    """

    async def failed_logins(self, login: str) -> Any:
        """
        Menghitung jumlah kegagalan login dan waktu penguncian akun (locked_until).

        Args:
            login (str): Identifier login (email/username).

        Returns:
            Any: Record berisi (failures, locked_until, retry_after_seconds).
        """
        # Mengambil informasi jumlah kegagalan login dari query yang sudah disiapkan.
        # Menghitung sisa waktu kunci (retry_after_seconds) menggunakan EPOCH time basis data.
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
        """
        Mencatat setiap percobaan login ke dalam riwayat login_attempt.

        Args:
            login (str): Identifier login (email/username).
            ip (str | None): Alamat IP pengguna.
            successful (bool): Status keberhasilan login.
            reason (str | None, optional): Alasan kegagalan (jika ada).
        """
        # Menyisipkan log percobaan login ke tabel login_attempt untuk keperluan audit
        # dan perlindungan brute-force.
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
        """
        Menerbitkan sesi baru dengan memanggil fungsi basis data `issue_session`.

        Args:
            org_id (UUID | str): ID organisasi.
            user_id (UUID | str): ID pengguna.
            device_label (str): Label perangkat.
            fingerprint (str | None): Sidik jari perangkat.
            ip (str | None): Alamat IP.
            user_agent (str): User agent dari browser/perangkat.

        Returns:
            Any: (session_id, family_id, refresh_token, expires_at).
        """
        # Memanggil fungsi tersimpan `issue_session` yang akan menangani
        # pembuatan token dan penyimpanan sesi baru secara aman.
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
        Merotasi refresh token menggunakan fungsi basis data `rotate_session`.

        Args:
            raw_refresh_token (str): Token refresh mentah yang digunakan.
            ip (str | None): Alamat IP asal rotasi.
            user_agent (str): User agent asal rotasi.

        Returns:
            Any: (session_id, user_id, refresh_token, expires_at, reused, family_created_at).
        """
        # Memanggil fungsi tersimpan `rotate_session`.
        # Jika token dicuri dan digunakan ulang, `reused` akan bernilai true.
        return await self.fetchone(
            """
            SELECT session_id, user_id, refresh_token, expires_at, reused, family_created_at
            FROM vms.rotate_session(:rt, :ip, :agent)
            """,
            {"rt": raw_refresh_token, "ip": ip, "agent": user_agent},
        )

    async def count_active_devices(self, user_id: UUID | str) -> int:
        """Menghitung jumlah rantai sesi unik (perangkat aktif) yang dimiliki pengguna."""
        return int(
            await self.scalar(
                """
                SELECT count(DISTINCT family_id)::int
                FROM vms.user_session
                WHERE user_id = :uid AND state = 'ACTIVE' AND expires_at > now()
                """,
                {"uid": user_id},
            )
            or 0
        )

    async def find_active_family_by_fingerprint(
        self, user_id: UUID | str, fingerprint: str
    ) -> UUID | None:
        """Mencari family_id aktif berdasarkan fingerprint perangkat."""
        val = await self.scalar(
            """
            SELECT family_id
            FROM vms.user_session
            WHERE user_id = :uid AND device_fingerprint = :fp AND state = 'ACTIVE' AND expires_at > now()
            LIMIT 1
            """,
            {"uid": user_id, "fp": fingerprint},
        )
        return UUID(str(val)) if val else None

    async def revoke_active_by_device(
        self, user_id: UUID | str, fingerprint: str | None, user_agent: str, reason: str
    ) -> int:
        """
        Mencabut SEMUA sesi aktif milik pengguna untuk perangkat yang sama
        (mencocokkan fingerprint jika ada, atau user-agent yang sama jika belum memiliki fingerprint).
        Mencegah pencatatan ganda pada tabel vms.user_session.
        """
        rows = await self.fetchall(
            """
            UPDATE vms.user_session
            SET state = 'REVOKED', revoked_at = now(), revoked_reason = :reason
            WHERE user_id = :uid
              AND state = 'ACTIVE'
              AND (
                  (:fp IS NOT NULL AND (
                      device_fingerprint = :fp
                      OR (device_fingerprint IS NULL AND user_agent = :agent)
                  ))
                  OR (:fp IS NULL AND user_agent = :agent)
              )
            RETURNING id
            """,
            {"uid": user_id, "fp": fingerprint, "agent": user_agent, "reason": reason},
        )
        return len(rows)

    async def revoke_family(self, user_id: UUID | str, family_id: UUID | str, reason: str) -> None:
        """Mencabut seluruh sesi dalam satu rantai perangkat (family_id)."""
        await self.execute(
            """
            UPDATE vms.user_session
            SET state = 'REVOKED', revoked_at = now(), revoked_reason = :reason
            WHERE user_id = :uid AND family_id = :family AND state = 'ACTIVE'
            """,
            {"uid": user_id, "family": family_id, "reason": reason},
        )

    async def revoke_by_refresh_token(self, raw_refresh_token: str, reason: str) -> None:
        """
        Mencabut sesi berdasarkan refresh token yang diberikan.

        Args:
            raw_refresh_token (str): Token refresh yang akan dicabut.
            reason (str): Alasan pencabutan.
        """
        # Token dicocokkan lewat SHA-256. Logout terjadi tanpa konteks pengguna → fungsi SECURITY DEFINER (0024),
        # bukan UPDATE langsung di bawah RLS.
        await self.execute("SELECT vms.revoke_session_by_token(:rt, :reason)",
                           {"rt": raw_refresh_token, "reason": reason})

    async def list_active(self, user_id: UUID | str) -> list[Any]:
        """
        Mengambil daftar seluruh sesi aktif yang dimiliki pengguna.

        Args:
            user_id (UUID | str): ID pengguna.

        Returns:
            list[Any]: Daftar sesi aktif pengguna.
        """
        # Mengambil sesi yang berstatus 'ACTIVE' dan belum melewati 'expires_at'.
        # Menghitung 'issued_at' asli dari keluarga sesi (family_id) yang sama.
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
        """
        Mencabut satu rantai sesi (perangkat) spesifik milik pengguna.

        Args:
            user_id (UUID | str): ID pengguna.
            session_id (UUID | str): ID sesi yang akan dicabut.
            reason (str): Alasan pencabutan.

        Returns:
            bool: True jika berhasil dicabut, False jika sesi tidak ditemukan/sudah tidak aktif.
        """
        # Menggunakan CTE (target) untuk menemukan family_id dari sesi yang diberikan,
        # lalu mencabut semua sesi dalam rantai tersebut yang masih aktif.
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
        """
        Mencabut semua sesi aktif selain sesi perangkat saat ini.

        Args:
            user_id (UUID | str): ID pengguna.
            keep_session_id (UUID | str): ID sesi yang ingin dipertahankan.
            reason (str): Alasan pencabutan.

        Returns:
            int: Jumlah sesi yang dicabut.
        """
        # Mencabut semua sesi aktif pengguna yang family_id-nya berbeda
        # dari family_id sesi yang ingin dipertahankan (keep_session_id).
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
        """
        Mencabut semua sesi aktif milik pengguna.

        Args:
            user_id (UUID | str): ID pengguna.
            reason (str): Alasan pencabutan.

        Returns:
            int: Jumlah sesi yang berhasil dicabut.
        """
        # Memanggil fungsi basis data vms.revoke_sessions untuk mencabut semua sesi.
        return int(await self.scalar(
            "SELECT vms.revoke_sessions(:uid, :reason)", {"uid": user_id, "reason": reason}
        ) or 0)
