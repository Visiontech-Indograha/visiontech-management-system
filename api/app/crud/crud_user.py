"""
app/crud/crud_user.py
Query untuk vms.app_user dan peran globalnya.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base import CRUDBase
from .crud_session import FAILED_LOGINS_SQL

# Peran global pertama; peran per pekerjaan (LEADER/MEMBER) berasal dari SK, bukan dari sini.
_USER_WITH_ROLE = """
    SELECT u.id, u.login, u.password_hash, u.is_active, u.organization_id, r.role
    FROM vms.app_user u
    LEFT JOIN vms.user_role r ON r.user_id = u.id
"""


class CRUDUser(CRUDBase):

    async def find_by_login(self, login: str) -> Any:
        return await self.fetchone(f"{_USER_WITH_ROLE} WHERE u.login = :login", {"login": login})

    async def find_by_id(self, user_id: UUID | str) -> Any:
        return await self.fetchone(f"{_USER_WITH_ROLE} WHERE u.id = :id", {"id": user_id})

    async def find_identity(self, user_id: UUID | str) -> Any:
        """Status akun + SEMUA peran global — dibaca pada setiap permintaan (dok 05 §4)."""
        return await self.fetchone(
            """
            SELECT u.login, u.is_active, u.organization_id,
                   COALESCE(array_agg(r.role::text ORDER BY r.role) FILTER (WHERE r.role IS NOT NULL),
                            '{}') AS roles
            FROM vms.app_user u
            LEFT JOIN vms.user_role r ON r.user_id = u.id
            WHERE u.id = :id
            GROUP BY u.id
            """,
            {"id": user_id},
        )

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

    async def get_attendance_mode(self, user_id: UUID | str) -> str | None:
        mode: str | None = await self.scalar(
            """
            SELECT e.attendance_mode FROM vms.app_user u JOIN vms.employee e ON e.id = u.employee_id
            WHERE u.id = :uid
            """,
            {"uid": user_id},
        )
        return mode

    # ── Akun karyawan (M1-01, R-20) ─────────────────────────────────────────────────────────────
    async def account_of_employee(self, employee_id: UUID | str) -> Any:
        return await self.fetchone(
            f"""
            SELECT u.id, u.login, u.is_active, u.last_login_at, f.failures, f.locked_until
            FROM vms.app_user u
            LEFT JOIN LATERAL ({FAILED_LOGINS_SQL.format(login="u.login")}) f ON true
            WHERE u.employee_id = CAST(:emp AS uuid)
            """,
            {"emp": employee_id})

    async def login_taken(self, org_id: UUID | str, login: str) -> bool:
        return bool(await self.scalar(
            "SELECT EXISTS (SELECT 1 FROM vms.app_user WHERE organization_id = :org AND login = :login)",
            {"org": org_id, "login": login}))

    async def create_for_employee(self, org_id: UUID | str, employee_id: UUID | str, login: str,
                                  password_hash: str) -> Any:
        return await self.fetchone(
            """
            INSERT INTO vms.app_user (organization_id, employee_id, login, password_hash, is_active)
            VALUES (:org, CAST(:emp AS uuid), :login, :hash, true)
            RETURNING id, login, is_active, last_login_at
            """,
            {"org": org_id, "emp": employee_id, "login": login, "hash": password_hash})

    async def set_active(self, user_id: UUID | str, active: bool) -> None:
        await self.execute("UPDATE vms.app_user SET is_active = :a, updated_at = now() WHERE id = :id",
                           {"a": active, "id": user_id})
