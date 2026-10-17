"""
app/crud/crud_user.py
Query untuk tabel users dan employee di skema public VMS V2.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base import CRUDBase

_USER_WITH_ROLE = """
    SELECT 
        u.user_id AS id,
        u.user_id,
        u.email AS login,
        u.email,
        u.username,
        u.password_hash,
        u.is_active,
        u.system_role::text AS role,
        u.employee_id,
        COALESCE(e.office_id, '11111111-0000-4000-a000-000000000001'::uuid) AS organization_id,
        e.full_name,
        e.employee_no
    FROM users u
    LEFT JOIN employee e ON e.employee_id = u.employee_id AND e.delete_at IS NULL
"""


class CRUDUser(CRUDBase):
    """
    CRUD untuk mengelola entitas User (Master Schema V2).
    """

    async def find_by_login(self, login: str) -> Any:
        """
        Mencari data pengguna beserta peran globalnya berdasarkan login (email atau username).
        """
        return await self.fetchone(
            f"{_USER_WITH_ROLE} WHERE (u.email = :login OR u.username = :login) AND u.delete_at IS NULL",
            {"login": login},
        )

    async def find_by_id(self, user_id: UUID | str) -> Any:
        """
        Mencari data pengguna berdasarkan ID.
        """
        return await self.fetchone(
            f"{_USER_WITH_ROLE} WHERE u.user_id = :id AND u.delete_at IS NULL",
            {"id": user_id},
        )

    async def find_identity(self, user_id: UUID | str) -> Any:
        """
        Mengambil status aktif akun dan peran dalam bentuk list (array).
        Digunakan di setiap request untuk authorisasi token.
        """
        return await self.fetchone(
            """
            SELECT 
                u.user_id AS id,
                u.email AS login,
                u.email,
                u.is_active,
                COALESCE(e.office_id, '11111111-0000-4000-a000-000000000001'::uuid) AS organization_id,
                ARRAY[u.system_role::text] AS roles
            FROM users u
            LEFT JOIN employee e ON e.employee_id = u.employee_id AND e.delete_at IS NULL
            WHERE u.user_id = :id AND u.delete_at IS NULL
            """,
            {"id": user_id},
        )

    async def update_password_hash(self, user_id: UUID | str, password_hash: str) -> None:
        """
        Memperbarui hash password pengguna.
        """
        await self.execute(
            "UPDATE users SET password_hash = :hash, update_at = now() WHERE user_id = :id AND delete_at IS NULL",
            {"hash": password_hash, "id": user_id},
        )

    async def get_employee_id(self, user_id: UUID | str) -> UUID | None:
        """
        Mendapatkan ID Karyawan (employee_id) yang tertaut ke akun pengguna ini.
        """
        return await self.scalar(
            "SELECT employee_id FROM users WHERE user_id = :uid AND delete_at IS NULL",
            {"uid": user_id},
        )

    async def get_attendance_mode(self, user_id: UUID | str) -> str | None:
        """
        Mendapatkan mode absensi yang diberlakukan kepada pengguna:
        - SUPER_ADMIN, OPERATIONAL_MANAGER, ADMIN_HR_GA: OFFICE
        - PROJECT_MANAGER, TEAM_LEADER, EMPLOYEE: BOTH (dapat di mobile/web)
        """
        role = await self.scalar(
            "SELECT system_role::text FROM users WHERE user_id = :uid AND delete_at IS NULL",
            {"uid": user_id},
        )
        if not role:
            return None
        if role in ("SUPER_ADMIN", "ADMIN", "OPERATIONAL_MANAGER", "ADMIN_HR_GA"):
            return "OFFICE"
        return "BOTH"

    async def account_of_employee(self, employee_id: UUID | str) -> Any:
        """
        Mengambil profil akun dari karyawan tertentu.
        """
        return await self.fetchone(
            """
            SELECT 
                u.user_id AS id, 
                u.email AS login, 
                u.username,
                u.system_role::text AS role,
                u.is_active, 
                u.update_at AS last_login_at, 
                0::int AS failures, 
                NULL::timestamptz AS locked_until
            FROM users u
            WHERE u.employee_id = CAST(:emp AS uuid) AND u.delete_at IS NULL
            """,
            {"emp": employee_id},
        )

    async def login_taken(self, org_id: UUID | str, login: str) -> bool:
        """
        Mengecek apakah email/username sudah dipakai.
        """
        return bool(await self.scalar(
            "SELECT EXISTS (SELECT 1 FROM users WHERE (email = :login OR username = :login) AND delete_at IS NULL)",
            {"login": login},
        ))

    async def create_for_employee(
        self, org_id: UUID | str, employee_id: UUID | str, login: str, password_hash: str, system_role: str = "EMPLOYEE"
    ) -> Any:
        """
        Membuat akun pengguna baru untuk seorang karyawan.
        """
        return await self.fetchone(
            """
            INSERT INTO users (employee_id, username, email, password_hash, system_role, is_active)
            VALUES (CAST(:emp AS uuid), :username, :email, :hash, CAST(:role AS system_role_enum), true)
            RETURNING user_id AS id, email AS login, is_active, update_at AS last_login_at
            """,
            {
                "emp": employee_id,
                "username": login.split("@")[0],
                "email": login,
                "hash": password_hash,
                "role": system_role,
            },
        )

    async def set_active(self, user_id: UUID | str, active: bool) -> None:
        """
        Mengubah status aktif/non-aktif akun.
        """
        await self.execute(
            "UPDATE users SET is_active = :a, update_at = now() WHERE user_id = :id AND delete_at IS NULL",
            {"a": active, "id": user_id},
        )
