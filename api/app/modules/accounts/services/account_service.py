"""
app/services/account_service.py
Akun login karyawan (M1-01, R-20): HR/admin membuat akun, mereset password, menonaktifkan & mengaktifkan.
Izin manage:users dijaga router; batas organisasi & aturan di sini. Password sementara hanya dikembalikan
sekali dan tidak pernah disimpan selain hash argon2.
"""

from __future__ import annotations

import secrets
import string
from typing import Any

from app.core.errors import AppError, NotFoundError
from app.core.security import hash_password
from app.modules.auth.repositories.auth_session_repository import CRUDSession
from app.modules.auth.repositories.auth_user_repository import CRUDUser
from app.modules.employees.repositories.employee_repository import CRUDEmployee

_ALPHABET = string.ascii_letters + string.digits


def temporary_password() -> str:
    """12 karakter acak + jaminan huruf & angka (kebijakan password web: min 8, huruf + angka)."""
    return (
        "".join(secrets.choice(_ALPHABET) for _ in range(10))
        + secrets.choice(string.ascii_lowercase)
        + secrets.choice(string.digits)
    )


class AccountService:
    """Layanan untuk mengelola akun autentikasi karyawan, termasuk pembuatan akun dan reset kata sandi."""

    def __init__(self, users: CRUDUser, employees: CRUDEmployee, sessions: CRUDSession) -> None:
        self.users, self.employees, self.sessions = users, employees, sessions

    async def _employee(self, employee_id: Any, org_id: str) -> Any:
        # Mengunci data karyawan untuk mencegah perubahan berbarengan (race conditions) saat mutasi akun.
        emp = await self.employees.lock(employee_id, org_id)
        if emp is None or emp.deleted:
            raise NotFoundError("Karyawan")
        return emp

    async def _account(self, employee_id: Any, org_id: str) -> Any:
        await self._employee(employee_id, org_id)
        # Memastikan karyawan telah memiliki akun sebelum melakukan tindakan yang membutuhkan akun eksisting.
        account = await self.users.account_of_employee(employee_id)
        if account is None:
            raise NotFoundError("Akun")
        return account

    async def account(self, employee_id: Any, org_id: str) -> Any:
        """
        Mengambil detail akun dari karyawan.

        Args:
            employee_id: ID karyawan.
            org_id: ID organisasi (untuk pengecekan izin).

        Returns:
            Data akun karyawan terkait jika ada.
        """
        await self._employee(employee_id, org_id)
        return await self.users.account_of_employee(employee_id)

    async def create(self, employee_id: Any, org_id: str, login: str) -> tuple[Any, str]:
        """
        Membuat akun login baru untuk karyawan yang ada.

        Args:
            employee_id: ID karyawan.
            org_id: ID organisasi.
            login: Alamat email login.

        Returns:
            Tuple dari (Data akun, password sementara).
        """
        emp = await self._employee(employee_id, org_id)
        # Aturan bisnis: Karyawan yang nonaktif tidak boleh mendapatkan akses.
        if not emp.is_active:
            raise AppError("EMPLOYEE_INACTIVE", "Karyawan sudah nonaktif; akun tidak dapat dibuat.", status=409)
        if await self.users.account_of_employee(employee_id) is not None:
            raise AppError("ACCOUNT_EXISTS", "Karyawan ini sudah punya akun.", status=409)

        # Pengecekan keunikan email secara global untuk mencegah tabrakan kredensial.
        if await self.users.login_taken(org_id, login):
            raise AppError("LOGIN_TAKEN", "Email login sudah dipakai akun lain.", status=409)

        password = temporary_password()
        row = await self.users.create_for_employee(org_id, employee_id, login, hash_password(password))
        return row, password

    async def reset_password(self, employee_id: Any, org_id: str) -> tuple[Any, str]:
        """
        Mereset password akun menjadi password sementara dan mencabut semua sesi aktif.

        Args:
            employee_id: ID karyawan.
            org_id: ID organisasi.

        Returns:
            Tuple dari (Data akun, password sementara yang baru).
        """
        account = await self._account(employee_id, org_id)
        password = temporary_password()
        await self.users.update_password_hash(account.id, hash_password(password))
        # Menghentikan paksa (revoke) semua sesi terbuka agar pemilik tidak menggunakan sesi yang rentan (compromised).
        await self.sessions.revoke_all_for_user(account.id, "PASSWORD_RESET")
        return account, password

    async def set_active(self, employee_id: Any, org_id: str, active: bool) -> Any:
        """
        Mengaktifkan atau menonaktifkan akun login karyawan.

        Args:
            employee_id: ID karyawan.
            org_id: ID organisasi.
            active: Flag True/False status.

        Returns:
            Data akun setelah diperbarui.
        """
        account = await self._account(employee_id, org_id)
        if active:
            emp = await self._employee(employee_id, org_id)
            # Menjaga konsistensi bisnis: Akun tidak boleh aktif jika status pekerjanya sudah nonaktif.
            if not emp.is_active:
                raise AppError("EMPLOYEE_INACTIVE", "Karyawan sudah nonaktif; akun tidak dapat diaktifkan.", status=409)
        await self.users.set_active(account.id, active)
        if not active:
            # Mencabut semua sesi terbuka sebagai konsekuensi keamanan penonaktifan akun.
            await self.sessions.revoke_all_for_user(account.id, "ACCOUNT_DEACTIVATED")
        return await self.users.account_of_employee(employee_id)
