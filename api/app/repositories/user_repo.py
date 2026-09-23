"""
app/repositories/user_repo.py
Query untuk vms.app_user dan peran globalnya.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base_repo import BaseRepo

# Peran global pertama; peran per pekerjaan (LEADER/MEMBER) berasal dari SK, bukan dari sini.
_USER_WITH_ROLE = """
    SELECT u.id, u.login, u.password_hash, u.is_active, u.organization_id, r.role
    FROM vms.app_user u
    LEFT JOIN vms.user_role r ON r.user_id = u.id
"""


class UserRepo(BaseRepo):

    async def find_by_login(self, login: str) -> Any:
        return await self.fetchone(f"{_USER_WITH_ROLE} WHERE u.login = :login", {"login": login})

    async def find_by_id(self, user_id: UUID | str) -> Any:
        return await self.fetchone(f"{_USER_WITH_ROLE} WHERE u.id = :id", {"id": user_id})

    async def update_password_hash(self, user_id: UUID | str, password_hash: str) -> None:
        await self.execute(
            "UPDATE vms.app_user SET password_hash = :hash WHERE id = :id",
            {"hash": password_hash, "id": user_id},
        )

    async def get_employee_id(self, user_id: UUID | str) -> UUID | None:
        employee_id: UUID | None = await self.scalar(
            "SELECT employee_id FROM vms.app_user WHERE id = :uid",
            {"uid": user_id},
        )
        return employee_id
