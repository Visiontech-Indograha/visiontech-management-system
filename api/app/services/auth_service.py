"""
app/services/auth_service.py
Aturan bisnis autentikasi: login, rotasi refresh token, logout, ganti kata sandi.
Tidak menulis SQL (lewat crud) dan tidak tahu HTTP (cookie diurus router).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from app.core.alerts import send_security_alert
from app.core.errors import AppError, NotFoundError
from app.core.security import create_jwt_token, hash_password, verify_password
from app.crud.crud_session import MAX_LOGIN_FAILURES, CRUDSession
from app.crud.crud_user import CRUDUser

ACCESS_TOKEN_TTL = timedelta(minutes=15)
DEFAULT_ROLE = "field"


@dataclass(frozen=True)
class ClientInfo:
    ip: str | None
    user_agent: str
    device_label: str = "Web Login"
    fingerprint: str | None = "fingerprint"


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
    employee_id: str | None = None   # karyawan milik akun ("Berkas saya"); None = akun tanpa karyawan
    attendance_mode: str | None = None  # FIELD = absen di HP, OFFICE = absen di web; None = tanpa karyawan


def _inactive() -> AppError:
    """Mengembalikan error ketika akun tidak aktif."""
    return AppError("INACTIVE", "Akun dinonaktifkan", status=403)


def _revoked() -> AppError:
    """Mengembalikan error ketika token/sesi telah dicabut atau invalid."""
    return AppError("SESSION_REVOKED", "Sesi tidak valid atau telah dicabut", status=401, persist=True)


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
        "LOCKED", f"Terlalu banyak kegagalan login. Coba lagi dalam {minutes} menit.", status=403,
        persist=persist,
        details={"retry_after_seconds": state.retry_after_seconds, "locked_until": state.locked_until.isoformat()},
    )


class AuthService:
    """Layanan aturan bisnis untuk autentikasi dan manajemen sesi pengguna."""
    def __init__(self, users: CRUDUser, sessions: CRUDSession) -> None:
        self.users = users
        self.sessions = sessions

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
        stored_hash = user.password_hash if user and user.password_hash else _dummy_hash()
        if not verify_password(password, stored_hash) or not user or not user.password_hash:
            await self.sessions.record_login_attempt(login, client.ip, False, "Invalid credentials")
            # Sisa percobaan & cooldown dihitung sama untuk login terdaftar maupun tidak (tak membocorkan akun).
            after = await self.sessions.failed_logins(login)
            if after.locked_until:
                raise _locked(after, persist=True)
            remaining = MAX_LOGIN_FAILURES - after.failures
            raise AppError("INVALID_CREDENTIALS", f"Email atau kata sandi salah. Sisa {remaining} percobaan.",
                           status=400, persist=True, details={"remaining_attempts": remaining})

        if not user.is_active:
            raise _inactive()

        # R-33: aplikasi HP hanya untuk staf lapangan, web hanya untuk akun kantor (attendance_mode).
        # Pengecualian (keputusan pemilik 2026-10-06): ADMINISTRATOR boleh masuk dari web DAN HP, baik tanpa karyawan
        # maupun yang tertaut ke data karyawan (jenis absennya tidak membatasi login). Akun tanpa karyawan (mode None)
        # juga boleh keduanya. Kredensial sudah benar, jadi penolakan tidak dihitung sebagai gagal login.
        mode = await self.users.get_attendance_mode(user.id)
        if (user.role or "") != "ADMIN":
            if platform == "mobile" and mode not in ("FIELD", None):
                raise AppError("NOT_FIELD_STAFF", "Akun Anda tidak termasuk kategori staf lapangan. "
                               "Silakan masuk lewat web.", status=403)
            if platform != "mobile" and mode == "FIELD":
                raise AppError("NOT_OFFICE_ACCOUNT", "Akun Anda bukan kategori akun kantor. "
                               "Silakan gunakan aplikasi HP Visiontech.", status=403)

        await self.sessions.record_login_attempt(login, client.ip, True)
        return await self._start_session(user, client)

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
            raise AppError("INVALID_TOKEN", "Token tidak valid", status=401)

        user = await self.users.find_by_id(rotated.user_id)
        if not user or not user.is_active:
            # Akun dinonaktifkan: seluruh sesinya berakhir pada permintaan ini juga (DoD fase 1).
            await self.sessions.revoke_all_for_user(rotated.user_id, "Akun dinonaktifkan")
            raise AppError("INACTIVE", "Akun dinonaktifkan", status=403, persist=True)

        return IssuedTokens(
            access_token=self._access_token(user, rotated.session_id),
            refresh_token=rotated.refresh_token,
        )

    async def logout(self, raw_refresh_token: str | None) -> None:
        """
        Keluar dari sistem dengan mencabut (revoke) refresh token saat ini.
        """
        if raw_refresh_token:
            await self.sessions.revoke_by_refresh_token(raw_refresh_token, "User logged out")

    async def active_sessions(self, user_id: str) -> list[Any]:
        """P1-7: perangkat yang sedang masuk dengan akun ini."""
        return await self.sessions.list_active(user_id)

    async def revoke_session(self, user_id: str, session_id: str) -> None:
        """
        Mencabut sesi tunggal secara spesifik (digunakan untuk mengeluarkan perangkat lain).
        """
        if not await self.sessions.revoke_session(user_id, session_id, "Dikeluarkan dari perangkat lain"):
            raise NotFoundError("Sesi")

    async def revoke_other_sessions(self, user_id: str, current_session_id: str) -> int:
        """
        Mencabut semua sesi aktif selain sesi saat ini.
        """
        return await self.sessions.revoke_other_sessions(user_id, current_session_id, "Keluarkan perangkat lain")

    async def me(self, user_id: str, permissions: list[str]) -> Profile:
        """
        Mengambil data profil pengguna (ME endpoint).
        """
        user = await self.users.find_by_id(user_id)
        if not user:
            raise NotFoundError("Pengguna")
        return Profile(
            user_id=user_id,
            email=user.login,
            role=user.role or DEFAULT_ROLE,
            permissions=permissions,
            employee_id=(str(emp) if (emp := await self.users.get_employee_id(user_id)) else None),
            attendance_mode=await self.users.get_attendance_mode(user_id),
        )

    async def change_password(
        self, user_id: str, current_password: str, new_password: str, client: ClientInfo
    ) -> IssuedTokens:
        """
        Mengubah kata sandi pengguna, mencabut semua sesi lainnya, lalu mengeluarkan sesi baru.
        """
        user = await self.users.find_by_id(user_id)
        if not user:
            raise NotFoundError("Pengguna")
        if not user.password_hash or not verify_password(current_password, user.password_hash):
            raise AppError(
                "VALIDATION_ERROR",
                "Data yang dikirim tidak valid.",
                status=422,
                details={"fields": {"current_password": "Password saat ini salah."}},
            )

        await self.users.update_password_hash(user_id, hash_password(new_password))
        # Kata sandi berganti → semua perangkat lain keluar; perangkat ini mendapat sesi baru.
        await self.sessions.revoke_all_for_user(user_id, "Kata sandi diganti")
        return await self._start_session(user, client)

    async def _start_session(self, user: Any, client: ClientInfo) -> IssuedTokens:
        """Membuat sesi baru dalam database dan mengeluarkan sepasang access/refresh token."""
        session = await self.sessions.issue(
            user.organization_id, user.id, client.device_label, client.fingerprint,
            client.ip, client.user_agent,
        )
        return IssuedTokens(
            access_token=self._access_token(user, session.session_id),
            refresh_token=session.refresh_token,
        )

    @staticmethod
    def _access_token(user: Any, session_id: Any) -> str:
        """
        Menghasilkan JWT akses.
        Hanya identitas (dok 05 §4); peran & status akun dibaca dari DB tiap permintaan.
        """
        return create_jwt_token(
            {"sub": str(user.id), "org": str(user.organization_id), "jti": str(session_id)},
            ACCESS_TOKEN_TTL,
        )
