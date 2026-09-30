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
from app.crud.crud_employee import CRUDEmployee
from app.crud.crud_session import CRUDSession
from app.crud.crud_user import CRUDUser

_ALPHABET = string.ascii_letters + string.digits


def temporary_password() -> str:
    """12 karakter acak + jaminan huruf & angka (kebijakan password web: min 8, huruf + angka)."""
    return "".join(secrets.choice(_ALPHABET) for _ in range(10)) + secrets.choice(string.ascii_lowercase) \
        + secrets.choice(string.digits)


class AccountService:
    def __init__(self, users: CRUDUser, employees: CRUDEmployee, sessions: CRUDSession) -> None:
        self.users, self.employees, self.sessions = users, employees, sessions

    async def _employee(self, employee_id: Any, org_id: str) -> Any:
        emp = await self.employees.lock(employee_id, org_id)
        if emp is None or emp.deleted:
            raise NotFoundError("Karyawan")
        return emp

    async def _account(self, employee_id: Any, org_id: str) -> Any:
        await self._employee(employee_id, org_id)
        account = await self.users.account_of_employee(employee_id)
        if account is None:
            raise NotFoundError("Akun")
        return account

    async def account(self, employee_id: Any, org_id: str) -> Any:
        await self._employee(employee_id, org_id)
        return await self.users.account_of_employee(employee_id)

    async def create(self, employee_id: Any, org_id: str, login: str) -> tuple[Any, str]:
        emp = await self._employee(employee_id, org_id)
        if not emp.is_active:
            raise AppError("EMPLOYEE_INACTIVE", "Karyawan sudah nonaktif; akun tidak dapat dibuat.", status=409)
        if await self.users.account_of_employee(employee_id) is not None:
            raise AppError("ACCOUNT_EXISTS", "Karyawan ini sudah punya akun.", status=409)
        if await self.users.login_taken(org_id, login):
            raise AppError("LOGIN_TAKEN", "Email login sudah dipakai akun lain.", status=409)
        password = temporary_password()
        row = await self.users.create_for_employee(org_id, employee_id, login, hash_password(password))
        return row, password

    async def reset_password(self, employee_id: Any, org_id: str) -> tuple[Any, str]:
        account = await self._account(employee_id, org_id)
        password = temporary_password()
        await self.users.update_password_hash(account.id, hash_password(password))
        await self.sessions.revoke_all_for_user(account.id, "PASSWORD_RESET")
        return account, password

    async def set_active(self, employee_id: Any, org_id: str, active: bool) -> Any:
        account = await self._account(employee_id, org_id)
        if active:
            emp = await self._employee(employee_id, org_id)
            if not emp.is_active:
                raise AppError("EMPLOYEE_INACTIVE", "Karyawan sudah nonaktif; akun tidak dapat diaktifkan.",
                               status=409)
        await self.users.set_active(account.id, active)
        if not active:
            await self.sessions.revoke_all_for_user(account.id, "ACCOUNT_DEACTIVATED")
        return await self.users.account_of_employee(employee_id)
