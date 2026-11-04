"""
app/modules/accounts/controllers/account_profile_controller.py

Controller orkestrasi operasi akun karyawan (lihat akun, buat akun, reset sandi, aktivasi/deaktivasi).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import Depends

from app.core.security import CurrentUser
from app.modules.accounts.dependencies import get_account_service
from app.modules.accounts.schemas.account_schema import (
    AccountCreate,
    AccountLoginUpdate,
    AccountOut,
    AccountRoleUpdate,
    AccountSessionsRevoked,
    AccountWithPassword,
)
from app.modules.accounts.services.account_service import AccountService
from app.modules.auth.schemas.auth_session_schema import AuthSessionResponseSchema


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
            system_role=getattr(row, "role", None),
        )

    async def handle_get_account(self, emp_id: UUID, organization_id: str) -> AccountOut:
        """Mengambil data akun karyawan berdasarkan ID."""
        row = await self.account_service.account(emp_id, organization_id)
        return self.map_row_to_out(row)

    async def handle_create_account(
        self, emp_id: UUID, actor: CurrentUser, data: AccountCreate
    ) -> AccountWithPassword:
        """Membuat akun login baru untuk karyawan (peran lapangan; default EMPLOYEE)."""
        row, password = await self.account_service.create(
            emp_id, actor, data.login.strip().lower(), data.system_role
        )
        return AccountWithPassword(
            **self.map_row_to_out(row).model_dump(),
            temporary_password=password,
        )

    async def handle_set_role(self, emp_id: UUID, actor: CurrentUser, data: AccountRoleUpdate) -> AccountOut:
        """Mengubah peran lapangan akun karyawan."""
        row = await self.account_service.set_field_role(emp_id, actor, data.system_role)
        return self.map_row_to_out(row)

    async def handle_reset_password(self, emp_id: UUID, organization_id: str) -> AccountWithPassword:
        """Mereset kata sandi akun karyawan ke sandi sementara baru."""
        row, password = await self.account_service.reset_password(emp_id, organization_id)
        return AccountWithPassword(
            **self.map_row_to_out(row).model_dump(),
            temporary_password=password,
        )

    async def handle_delete_account(self, emp_id: UUID, actor: CurrentUser) -> dict[str, str]:
        """Hapus permanen akun login karyawan."""
        await self.account_service.delete_account(emp_id, actor)
        return {"status": "deleted"}

    async def handle_deactivate(self, emp_id: UUID, organization_id: str) -> AccountOut:
        """Menonaktifkan akun karyawan."""
        row = await self.account_service.set_active(emp_id, organization_id, False)
        return self.map_row_to_out(row)

    async def handle_activate(self, emp_id: UUID, organization_id: str) -> AccountOut:
        """Mengaktifkan kembali akun karyawan."""
        row = await self.account_service.set_active(emp_id, organization_id, True)
        return self.map_row_to_out(row)

    async def handle_list_sessions(self, emp_id: UUID, organization_id: str) -> list[AuthSessionResponseSchema]:
        """Perangkat yang sedang masuk dengan akun karyawan ini."""
        rows = await self.account_service.sessions_of(emp_id, organization_id)
        return [
            AuthSessionResponseSchema(
                id=str(r.id),
                device_label=r.device_label,
                ip_address=r.ip_address,
                user_agent=r.user_agent,
                issued_at=r.issued_at,
                last_used_at=r.last_used_at,
                current=False,  # HR/admin tidak punya sesi di perangkat akun ini
            )
            for r in rows
        ]

    async def handle_revoke_session(self, emp_id: UUID, session_id: UUID, actor: CurrentUser) -> AccountSessionsRevoked:
        await self.account_service.revoke_session(emp_id, actor, session_id)
        return AccountSessionsRevoked(revoked=1)

    async def handle_revoke_all_sessions(self, emp_id: UUID, actor: CurrentUser) -> AccountSessionsRevoked:
        revoked = await self.account_service.revoke_all_sessions(emp_id, actor, "SESSIONS_REVOKE_ALL")
        return AccountSessionsRevoked(revoked=revoked)

    async def handle_reset_device_slots(self, emp_id: UUID, actor: CurrentUser) -> AccountSessionsRevoked:
        revoked = await self.account_service.revoke_all_sessions(emp_id, actor, "DEVICE_SLOTS_RESET")
        return AccountSessionsRevoked(revoked=revoked)

    async def handle_unlock(self, emp_id: UUID, actor: CurrentUser) -> AccountOut:
        row = await self.account_service.unlock(emp_id, actor)
        return self.map_row_to_out(row)

    async def handle_change_login(self, emp_id: UUID, actor: CurrentUser, data: AccountLoginUpdate) -> AccountOut:
        row = await self.account_service.change_login(emp_id, actor, data.login.strip().lower())
        return self.map_row_to_out(row)
