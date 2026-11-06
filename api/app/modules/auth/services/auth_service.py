"""
app/services/auth_service.py
Aturan bisnis autentikasi: login, rotasi refresh token, logout, ganti kata sandi.
Tidak menulis SQL (lewat crud) dan tidak tahu HTTP (cookie diurus router).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from app.core.alerts import send_security_alert
from app.core.config import settings
from app.core.errors import AppError, NotFoundError
from app.core.events import broker
from app.core.security import create_jwt_token, hash_password, verify_password
from app.core.time import utcnow
from app.database.session import set_request_context
from app.modules.auth.repositories.auth_session_repository import (
    MAX_LOGIN_FAILURES,
    CRUDSession,
)
from app.modules.auth.repositories.auth_user_repository import FIELD_ROLES, OFFICE_ROLES, CRUDUser
from app.shared.device_credential_repository import new_token

ACCESS_TOKEN_TTL = timedelta(minutes=15)
DEFAULT_ROLE = "field"


MAX_DEVICES = 4  # perangkat aktif per akun (CHANGELOG 2026-10-14)


@dataclass(frozen=True)
class ClientInfo:
    ip: str | None
    user_agent: str
    device_label: str | None = None  # header X-Device-Label; tanpa itu perangkat dikenali dari User-Agent
    fingerprint: str | None = None

    @property
    def device_name(self) -> str:
        """Nama perangkat di user_sessions.device_name — sekaligus identitas "perangkat yang sama"."""
        return (self.device_label or self.user_agent or "Perangkat tanpa nama")[:100]


@dataclass(frozen=True)
class IssuedTokens:
    access_token: str
    refresh_token: str


@dataclass(frozen=True)
class Profile:
    user_id: str
    email: str
    role: str
    permissions: list[str]
    employee_id: str | None = None  # karyawan milik akun ("Berkas saya"); None = akun tanpa karyawan
    attendance_mode: str | None = None  # FIELD = absen di HP, OFFICE = absen di web; None = tanpa karyawan
    division_id: str | None = None
    managed_division_ids: list[str] = field(default_factory=list)
    managed_divisions: list[dict[str, Any]] = field(default_factory=list)


def _inactive() -> AppError:
    """Mengembalikan error ketika akun tidak aktif."""
    return AppError("INACTIVE", "Akun Anda dinonaktifkan. Hubungi HR atau admin.", status=403)


def _revoked() -> AppError:
    """Mengembalikan error ketika token/sesi telah dicabut atau invalid."""
    return AppError("SESSION_REVOKED", "Sesi berakhir atau dicabut. Silakan masuk kembali.", status=401, persist=True)


_DUMMY_HASH: str | None = None


def _dummy_hash() -> str:
    """
    Menghasilkan (atau mengambil) hash sandi dummy secara lazy untuk mencegah timing attack.
    Jika login menggunakan email yang salah, proses verifikasi argon2 tetap dijalankan
    sehingga durasi proses tetap sama dan tidak memberi petunjuk apakah email ada atau tidak (dok 08).
    """
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = hash_password("vms-login-tiruan")
    return _DUMMY_HASH


def _locked(state: Any, *, persist: bool = False) -> AppError:
    """
    Mengembalikan error ketika sesi login terkunci akibat terlalu banyak kegagalan.

    Args:
        state (Any): State login yang berisi locked_until dan retry_after_seconds.
        persist (bool): Jika True, pesan akan bertahan di UI (persist).
    """
    minutes = max(1, -(-state.retry_after_seconds // 60))
    return AppError(
        "LOCKED",
        f"Terlalu banyak kegagalan login. Coba lagi dalam {minutes} menit.",
        status=403,
        persist=persist,
        details={"retry_after_seconds": state.retry_after_seconds, "locked_until": state.locked_until.isoformat()},
    )


class AuthService:
    """Layanan aturan bisnis untuk autentikasi dan manajemen sesi pengguna."""

    def __init__(self, users: CRUDUser, sessions: CRUDSession) -> None:
        self.users = users
        self.sessions = sessions

    async def _act_as(self, user: Any) -> None:
        """Konteks RLS & audit transaksi ini = pengguna ini, setelah identitasnya pasti (sandi benar / token sah).
        Tanpa ini kueri tabel ber-RLS (mis. `employee`) diam-diam kosong di bawah peran runtime `vms_api` (P9-2)."""
        await set_request_context(
            self.users.db, user_id=str(user.id), organization_id=str(user.organization_id), actor_label=str(user.login)
        )

    async def _user(self, user_id: str) -> Any:
        """Akun pengguna yang sudah terautentikasi + konteks RLS-nya; tidak ada → 404."""
        user = await self.users.find_by_id(user_id)
        if not user:
            raise NotFoundError("Pengguna")
        await self._act_as(user)
        return user

    async def login(self, login: str, password: str, client: ClientInfo, platform: str = "web") -> IssuedTokens:
        """
        Memvalidasi kredensial pengguna dan membuat sesi login jika berhasil.
        Menerapkan pembatasan (rate limiting) berdasarkan kegagalan login untuk mencegah brute-force.
        """
        state = await self.sessions.failed_logins(login)
        if state.locked_until:
            await send_security_alert(
                "Lonjakan Kegagalan Login", f"Sebuah akun terkunci sementara dari IP {client.ip}."
            )
            raise _locked(state)

        user = await self.users.find_by_login(login)
        # Selalu hitung argon2 — tanpa ini login tak terdaftar jauh lebih cepat & bisa ditebak (dok 08).
        # Melakukan hashing buatan (dummy_hash) jika akun tidak ditemukan agar waktu respons seragam.
        # Argon2 CPU-bound: dijalankan di threadpool agar event loop tidak terblokir (F-17).
        stored_hash = user.password_hash if user and user.password_hash else _dummy_hash()
        password_ok = await asyncio.to_thread(verify_password, password, stored_hash)
        if not password_ok or not user or not user.password_hash:
            await self.sessions.record_login_attempt(
                login, client.ip, False, "Invalid credentials",
                user_id=user.id if user else None, role=user.role if user else None, platform=platform,
            )
            # Sisa percobaan & cooldown dihitung sama untuk login terdaftar maupun tidak (tak membocorkan akun).
            after = await self.sessions.failed_logins(login)
            if after.locked_until:
                raise _locked(after, persist=True)
            remaining = MAX_LOGIN_FAILURES - after.failures
            raise AppError(
                "INVALID_CREDENTIALS",
                f"Email atau kata sandi salah. Sisa {remaining} percobaan.",
                status=400,
                persist=True,
                details={"remaining_attempts": remaining},
            )

        if not user.is_active:
            raise _inactive()
        await self._act_as(user)

        # docs/35 §1: web hanya untuk peran kantor, aplikasi HP hanya untuk peran lapangan. Kredensial sudah
        # benar, jadi penolakan platform tidak dihitung sebagai gagal login.
        role = user.role or ""
        if platform == "mobile" and role not in FIELD_ROLES and role != "SUPER_ADMIN":
            raise AppError(
                "NOT_FIELD_STAFF",
                "Akun kantor tidak dapat masuk lewat aplikasi HP. Silakan masuk lewat web.",
                status=403,
            )
        if platform != "mobile" and not await self._has_office_role(user, role):
            raise AppError(
                "NOT_OFFICE_ACCOUNT",
                "Akun lapangan masuk lewat aplikasi HP Visiontech, bukan web.",
                status=403,
            )

        await self._claim_device_slot(user, client)

        await self.sessions.record_login_attempt(
            login, client.ip, True, user_id=user.id, role=user.role, platform=platform
        )
        auth_time = int(utcnow().timestamp())
        tokens = await self._start_session(user, client, auth_time=auth_time, platform=platform)

        # Siarkan peristiwa keamanan ke semua perangkat aktif pengguna
        broker.publish(
            [str(user.id)],
            {
                "topic": "security",
                "data": {
                    "type": "SECURITY_LOGIN",
                    "title": "Masuk dari Perangkat Baru",
                    "body": (
                        f"Akun Anda baru saja masuk dari {client.device_name} "
                        f"(IP: {client.ip or 'tidak diketahui'})."
                    ),
                    "device_label": client.device_name,
                    "ip": client.ip or "-",
                    "time": auth_time,
                },
            },
        )
        return tokens

    async def _has_office_role(self, user: Any, primary_role: str) -> bool:
        """Peran efektif (utama + tambahan aktif, ADR 0002) memuat minimal satu peran kantor. Flag mati = hanya
        peran utama (perilaku lama). Memakai find_identity agar logika union tidak digandakan."""
        if primary_role in OFFICE_ROLES:
            return True
        if not settings.ROLE_ASSIGNMENT_ENABLED:
            return False
        identity = await self.users.find_identity(user.id)
        return identity is not None and any(r in OFFICE_ROLES for r in (identity.roles or []))

    async def _claim_device_slot(self, user: Any, client: ClientInfo) -> None:
        """Satu perangkat = satu rantai sesi (token_family_id) dengan device_name yang sama. Masuk ulang dari
        perangkat yang sama mengganti rantai lamanya; perangkat baru ditolak bila sudah ada MAX_DEVICES aktif."""
        existing_family = await self.sessions.find_active_family_by_device(user.id, client.device_name)
        if existing_family is not None:
            await self.sessions.revoke_family(user.id, existing_family, "Masuk ulang pada perangkat yang sama")
        elif await self.sessions.count_active_devices(user.id) >= MAX_DEVICES:
            raise AppError(
                "MAX_DEVICES_REACHED",
                f"Akun ini sudah aktif di {MAX_DEVICES} perangkat. Keluarkan salah satu perangkat lewat menu "
                "Akun & keamanan (bagian Perangkat yang masuk), lalu coba lagi. "
                "Tidak punya akses? Minta HR atau admin.",
                status=403,
            )

    async def refresh(self, raw_refresh_token: str | None, client: ClientInfo) -> IssuedTokens:
        """
        Melakukan rotasi (perpanjangan) akses menggunakan refresh token.
        Akan mencabut akses jika terdeteksi penggunaan ulang (reuse) token lama (mencegah pencurian sesi).
        """
        if not raw_refresh_token:
            raise AppError("NO_TOKEN", "Sesi tidak ditemukan. Silakan masuk kembali.", status=401)

        rotated = await self.sessions.rotate(raw_refresh_token, client.ip, client.user_agent)
        # Mendeteksi dan menangani jika refresh token yang sudah terpakai dicoba lagi (potensi pencurian/hijack).
        if rotated.reused:
            await send_security_alert(
                "Pencurian Sesi (Reuse Detected)",
                f"Refresh token usang dipakai oleh IP {client.ip}. Seluruh sesi perangkat dicabut.",
            )
            raise _revoked()
        if not rotated.session_id:
            raise AppError(
                "INVALID_TOKEN", "Sesi telah berakhir atau tidak dikenali. Silakan masuk kembali.", status=401
            )

        family_start = getattr(rotated, "family_created_at", None)
        if family_start is not None and (utcnow() - family_start).total_seconds() > 86400:
            # Batas sesi 24 jam dihitung dari login awal, bukan dari rotasi terakhir.
            await self.sessions.revoke_family(rotated.user_id, rotated.family_id, "Batas sesi 24 jam")
            raise AppError("SESSION_EXPIRED", "Sesi sudah 24 jam. Silakan masuk kembali.", status=401)

        user = await self.users.find_by_id(rotated.user_id)
        if not user or not user.is_active:
            # Akun dinonaktifkan: seluruh sesinya berakhir pada permintaan ini juga (DoD fase 1).
            await self.sessions.revoke_all_for_user(rotated.user_id, "Akun dinonaktifkan")
            raise AppError("INACTIVE", "Akun Anda dinonaktifkan. Hubungi HR atau admin.", status=403, persist=True)

        auth_time = int(family_start.timestamp()) if family_start is not None else int(utcnow().timestamp())
        return IssuedTokens(
            access_token=self._access_token(user, rotated.session_id, auth_time=auth_time),
            refresh_token=rotated.refresh_token,
        )

    async def issue_device_credential(self, user_id: str, client: ClientInfo) -> tuple[str, Any, str]:
        """Terbitkan token perangkat (30 hari) untuk masuk dengan sidik jari. Yang lama untuk perangkat ini dicabut.
        Mengembalikan (token mentah, kedaluwarsa, nama perangkat); token mentah hanya ada di respons ini."""
        await self._user(user_id)
        raw = new_token()
        issued = await self.sessions.credentials.issue(user_id, client.device_name, raw, ip=client.ip)
        return raw, issued.expires_at, client.device_name

    async def biometric_login(self, raw_token: str, client: ClientInfo) -> tuple[IssuedTokens, str, Any]:
        """Masuk dengan token perangkat: token dipakai sekali (dirotasi), sesi baru seperti login biasa.
        Mengembalikan (tokens, token perangkat baru, kedaluwarsa token baru)."""
        creds = self.sessions.credentials
        used = await creds.consume(raw_token, ip=client.ip)
        if used is None:
            known = await creds.lookup(raw_token)
            if known is not None and known.revoked_reason == "ROTATED":
                # Token lama dipakai lagi setelah dirotasi: salinan token kemungkinan bocor. Cabut kredensial
                # perangkat itu (harus masuk ulang dengan kata sandi) dan simpan perubahannya (persist).
                await creds.note_reuse(known.credential_id, known.user_id, known.device_name, client.ip)
                await send_security_alert(
                    "Token Sidik Jari Dipakai Ulang", f"Token perangkat usang dipakai oleh IP {client.ip}."
                )
                raise AppError(
                    "BIOMETRIC_REUSED",
                    "Demi keamanan, masuk dengan sidik jari dinonaktifkan. Silakan masuk dengan email dan kata sandi.",
                    status=401,
                    persist=True,
                )
            raise AppError(
                "BIOMETRIC_INVALID",
                "Masuk dengan sidik jari tidak berlaku lagi. Silakan masuk dengan email dan kata sandi.",
                status=401,
            )

        user = await self.users.find_by_id(used.user_id)
        if not user or not user.is_active:
            await self.sessions.revoke_all_for_user(used.user_id, "Akun dinonaktifkan")
            raise AppError("INACTIVE", "Akun Anda dinonaktifkan. Hubungi HR atau admin.", status=403, persist=True)
        await self._act_as(user)
        role = user.role or ""
        if role not in FIELD_ROLES and role != "SUPER_ADMIN":
            raise AppError(
                "NOT_FIELD_STAFF",
                "Akun kantor tidak dapat masuk lewat aplikasi HP. Silakan masuk lewat web.",
                status=403,
            )
        await self._claim_device_slot(user, client)
        auth_time = int(utcnow().timestamp())
        tokens = await self._start_session(user, client, auth_time=auth_time, platform="mobile")
        raw = new_token()
        issued = await creds.issue(user.id, client.device_name, raw, ip=client.ip)
        broker.publish(
            [str(user.id)],
            {
                "topic": "security",
                "data": {
                    "type": "SECURITY_LOGIN",
                    "title": "Masuk dari Perangkat",
                    "body": f"Akun Anda masuk dengan sidik jari dari {client.device_name} "
                            f"(IP: {client.ip or 'tidak diketahui'}).",
                    "device_label": client.device_name,
                    "ip": client.ip or "-",
                    "time": auth_time,
                },
            },
        )
        return tokens, raw, issued.expires_at

    async def logout(self, raw_refresh_token: str | None) -> None:
        """
        Keluar dari sistem dengan mencabut (revoke) refresh token saat ini.
        """
        if raw_refresh_token:
            await self.sessions.revoke_by_refresh_token(raw_refresh_token, "User logged out")

    async def active_sessions(self, user_id: str) -> list[Any]:
        """P1-7: perangkat yang sedang masuk dengan akun ini."""
        await self._user(user_id)
        return await self.sessions.list_active(user_id)

    async def revoke_session(self, user_id: str, session_id: str) -> None:
        """
        Mencabut sesi tunggal secara spesifik (digunakan untuk mengeluarkan perangkat lain).
        """
        await self._user(user_id)
        if not await self.sessions.revoke_session(user_id, session_id, "Dikeluarkan dari perangkat lain"):
            raise NotFoundError("Sesi")

    async def revoke_other_sessions(self, user_id: str, current_session_id: str) -> int:
        """
        Mencabut semua sesi aktif selain sesi saat ini.
        """
        await self._user(user_id)
        return await self.sessions.revoke_other_sessions(user_id, current_session_id, "Keluarkan perangkat lain")

    async def me(self, user_id: str, permissions: list[str]) -> Profile:
        """
        Mengambil data profil pengguna (ME endpoint).
        """
        user = await self._user(user_id)
        managed_divs = await self.users.get_managed_divisions(user_id)
        return Profile(
            user_id=user_id,
            email=user.login,
            role=user.role or DEFAULT_ROLE,
            permissions=permissions,
            employee_id=(str(emp) if (emp := await self.users.get_employee_id(user_id)) else None),
            attendance_mode=await self.users.get_attendance_mode(user_id),
            division_id=await self.users.get_division_id(user_id),
            managed_division_ids=[d["division_id"] for d in managed_divs],
            managed_divisions=managed_divs,
        )

    async def change_password(
        self, user_id: str, current_password: str, new_password: str, client: ClientInfo
    ) -> IssuedTokens:
        """
        Mengubah kata sandi pengguna, mencabut semua sesi lainnya, lalu mengeluarkan sesi baru.
        """
        user = await self._user(user_id)
        if not user.password_hash or not await asyncio.to_thread(
            verify_password, current_password, user.password_hash
        ):
            raise AppError(
                "VALIDATION_ERROR",
                "Kata sandi saat ini salah.",
                status=422,
                details={"fields": {"current_password": "Kata sandi saat ini salah."}},
            )

        new_hash = await asyncio.to_thread(hash_password, new_password)
        await self.users.update_password_hash(user_id, new_hash)
        # Kata sandi berganti → semua perangkat lain keluar; perangkat ini mendapat sesi baru.
        await self.sessions.revoke_all_for_user(user_id, "Kata sandi diganti")
        return await self._start_session(user, client)

    async def _start_session(
        self, user: Any, client: ClientInfo, auth_time: int | None = None, platform: str | None = None
    ) -> IssuedTokens:
        """Membuat sesi baru dalam database dan mengeluarkan sepasang access/refresh token.
        Platform sesi = platform login; tanpa itu (mis. ganti kata sandi) diturunkan dari peran (docs/35 §1)."""
        session = await self.sessions.issue(
            user.organization_id,
            user.id,
            client.device_name,
            client.fingerprint,
            client.ip,
            client.user_agent,
            platform=platform or ("mobile" if (user.role or "") in FIELD_ROLES else "web"),
        )
        return IssuedTokens(
            access_token=self._access_token(user, session.session_id, auth_time=auth_time),
            refresh_token=session.refresh_token,
        )

    @staticmethod
    def _access_token(user: Any, session_id: Any, auth_time: int | None = None) -> str:
        """
        Menghasilkan JWT akses.
        Hanya identitas (dok 05 §4); peran & status akun dibaca dari DB tiap permintaan.
        """
        payload: dict[str, Any] = {"sub": str(user.id), "org": str(user.organization_id), "jti": str(session_id)}
        if auth_time is not None:
            payload["auth_time"] = auth_time
        return create_jwt_token(payload, ACCESS_TOKEN_TTL)
