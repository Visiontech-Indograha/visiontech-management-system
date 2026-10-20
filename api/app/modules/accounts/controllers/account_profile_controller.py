"""
app/modules/accounts/controllers/account_profile_controller.py

Controller orkestrasi operasi akun karyawan (lihat akun, buat akun, reset sandi, aktivasi/deaktivasi).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import Depends

from app.modules.accounts.dependencies import get_account_service
from app.modules.accounts.schemas.account_schema import AccountCreate, AccountOut, AccountWithPassword
from app.modules.accounts.services.account_service import AccountService


class AccountProfileController:
    """
    Controller use case manajemen akun login karyawan.
    """

    def __init__(self, account_service: AccountService = Depends(get_account_service)) -> None:
        self.account_service = account_service

    @staticmethod
    def map_row_to_out(row: Any) -> AccountOut:
        """Memetakan baris record database ke schema AccountOut."""
        if row is None:
            return AccountOut(exists=False)
        return AccountOut(
            exists=True,
            user_id=row.id,
            login=str(row.login),
            is_active=row.is_active,
            last_login_at=row.last_login_at,
            failed_logins=getattr(row, "failures", None) or 0,
            locked_until=getattr(row, "locked_until", None),
        )

    async def handle_get_account(self, emp_id: UUID, organization_id: str) -> AccountOut:
        """Mengambil data akun karyawan berdasarkan ID."""
        row = await self.account_service.account(emp_id, organization_id)
        return self.map_row_to_out(row)

    async def handle_create_account(
        self, emp_id: UUID, organization_id: str, data: AccountCreate
    ) -> AccountWithPassword:
        """Membuat akun login baru untuk karyawan."""
        row, password = await self.account_service.create(emp_id, organization_id, data.login.strip().lower())
        return AccountWithPassword(
            **self.map_row_to_out(row).model_dump(),
            temporary_password=password,
        )

    async def handle_reset_password(self, emp_id: UUID, organization_id: str) -> AccountWithPassword:
        """Mereset kata sandi akun karyawan ke sandi sementara baru."""
        row, password = await self.account_service.reset_password(emp_id, organization_id)
        return AccountWithPassword(
            **self.map_row_to_out(row).model_dump(),
            temporary_password=password,
        )

    async def handle_deactivate(self, emp_id: UUID, organization_id: str) -> AccountOut:
        """Menonaktifkan akun karyawan."""
        row = await self.account_service.set_active(emp_id, organization_id, False)
        return self.map_row_to_out(row)

    async def handle_activate(self, emp_id: UUID, organization_id: str) -> AccountOut:
        """Mengaktifkan kembali akun karyawan."""
        row = await self.account_service.set_active(emp_id, organization_id, True)
        return self.map_row_to_out(row)
