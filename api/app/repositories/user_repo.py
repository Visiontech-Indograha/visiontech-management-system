"""
app/repositories/user_repo.py
Query untuk app_user, employee, sesi.
"""
from __future__ import annotations

from uuid import UUID
from typing import Any

from .base_repo import BaseRepo


class UserRepo(BaseRepo):

    async def get_user_by_email(self, email: str) -> Any:
        return await self.fetchone(
            "SELECT * FROM vms.app_user WHERE email = :email AND deleted_at IS NULL",
            {"email": email},
        )

    async def get_user_by_id(self, user_id: UUID) -> Any:
        return await self.fetchone(
            "SELECT * FROM vms.app_user WHERE id = :id",
            {"id": user_id},
        )

    async def get_employee_id(self, user_id: UUID) -> UUID | None:
        return await self.scalar(
            "SELECT employee_id FROM vms.app_user WHERE id = :uid",
            {"uid": user_id},
        )

    async def issue_session(
        self,
        user_id: UUID,
        ip: str,
        user_agent: str,
        org_id: UUID,
    ) -> Any:
        """Panggil DB function vms.issue_session — buat sesi baru, kembalikan token pair."""
        return await self.fetchone(
            """
            SELECT access_token, refresh_token, session_id
            FROM vms.issue_session(:uid, :ip, :ua, :org)
            """,
            {"uid": user_id, "ip": ip, "ua": user_agent, "org": org_id},
        )

    async def rotate_session(self, refresh_token_hash: str) -> Any:
        """Rotasi refresh token. Kembalikan token pair baru atau NULL bila tidak valid."""
        return await self.fetchone(
            "SELECT access_token, refresh_token FROM vms.rotate_session(:hash)",
            {"hash": refresh_token_hash},
        )

    async def revoke_session(self, session_id: UUID) -> None:
        await self.execute(
            "SELECT vms.revoke_sessions(:sid)",
            {"sid": session_id},
        )

    async def login_is_locked(self, email: str) -> bool:
        result = await self.scalar(
            "SELECT vms.login_is_locked(:email)",
            {"email": email},
        )
        return bool(result)

    async def deactivate_user(self, user_id: UUID) -> None:
        await self.execute(
            "UPDATE vms.app_user SET is_active = false WHERE id = :id",
            {"id": user_id},
        )
