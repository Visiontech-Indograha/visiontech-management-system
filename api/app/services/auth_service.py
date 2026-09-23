"""
app/services/auth_service.py
Aturan bisnis autentikasi — login, refresh, logout.
Router hanya memanggil ini. Tidak ada SQL di router.
"""
from __future__ import annotations

import hashlib
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, ForbiddenError, NotFoundError
from app.core.permissions import get_role_permissions
from app.core.security import verify_jwt_token, create_jwt_token
from app.repositories.user_repo import UserRepo


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = UserRepo(db)

    async def login(
        self,
        email: str,
        password: str,
        ip: str,
        user_agent: str,
    ) -> dict:
        """
        Login karyawan:
        1. Cek lockout — kalau terkunci, lempar error (tidak bocorkan alasan).
        2. Verifikasi email + password via DB.
        3. Cek is_active — akun nonaktif tidak bisa login.
        4. Buat sesi via vms.issue_session.
        5. Kembalikan access_token + refresh_token.
        """
        if await self.repo.login_is_locked(email):
            raise AppError(
                "ACCOUNT_LOCKED",
                "Akun terkunci sementara karena terlalu banyak percobaan gagal. "
                "Coba lagi dalam beberapa menit.",
                status=429,
            )

        user = await self.repo.get_user_by_email(email)
        if not user:
            raise AppError("INVALID_CREDENTIALS", "Email atau kata sandi salah.", status=401)

        # Verifikasi password melalui DB function pgcrypto
        valid = await self.repo.scalar(
            "SELECT crypt(:pwd, password_hash) = password_hash FROM vms.app_user WHERE id = :id",
            {"pwd": password, "id": user.id},
        ) if hasattr(self.repo, 'scalar') else False

        # Fallback: python-bcrypt bila DB function tidak tersedia
        if not valid:
            try:
                import bcrypt
                valid = bcrypt.checkpw(password.encode(), user.password_hash.encode())
            except Exception:
                valid = False

        if not valid:
            raise AppError("INVALID_CREDENTIALS", "Email atau kata sandi salah.", status=401)

        if not user.is_active:
            raise ForbiddenError("Akun Anda telah dinonaktifkan. Hubungi HR untuk informasi lebih lanjut.")

        session = await self.repo.issue_session(user.id, ip, user_agent, user.organization_id)
        if not session:
            raise AppError("SESSION_ERROR", "Gagal membuat sesi. Coba beberapa saat lagi.", status=500)

        return {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "token_type": "bearer",
        }

    async def refresh(self, raw_refresh_token: str) -> dict:
        """
        Rotasi refresh token via vms.rotate_session.
        Token lama langsung dicabut setelah rotasi.
        """
        token_hash = hashlib.sha256(raw_refresh_token.encode()).hexdigest()
        new_tokens = await self.repo.rotate_session(token_hash)
        if not new_tokens:
            raise AppError(
                "INVALID_REFRESH_TOKEN",
                "Token tidak valid atau sudah kedaluwarsa. Silakan login ulang.",
                status=401,
            )
        return {
            "access_token": new_tokens.access_token,
            "refresh_token": new_tokens.refresh_token,
            "token_type": "bearer",
        }

    async def logout(self, session_id: UUID) -> None:
        """Cabut sesi aktif. Idempotent — tidak error bila session sudah tidak ada."""
        await self.repo.revoke_session(session_id)

    async def get_me(self, user_id: UUID) -> dict:
        user = await self.repo.get_user_by_id(user_id)
        if not user:
            raise NotFoundError("Pengguna")
        permissions = get_role_permissions(user.role)
        return {
            "user_id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "organization_id": str(user.organization_id),
            "permissions": permissions,
            "must_change_password": getattr(user, "must_change_password", False),
        }
