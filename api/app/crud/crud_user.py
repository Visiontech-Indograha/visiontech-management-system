"""
app/crud/crud_user.py
Query untuk tabel users dan employee di skema public VMS V2 beserta backward-compatibility untuk suite pengujian vms.
"""

import contextlib
from typing import Any
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

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

_LEGACY_USER = """
    SELECT
        u.id AS user_id,
        u.id,
        u.login,
        u.login AS email,
        u.login AS username,
        u.password_hash,
        u.is_active,
        COALESCE(
            (SELECT r.role::text FROM vms.user_role r WHERE r.user_id = u.id LIMIT 1),
            'EMPLOYEE'
        ) AS role,
        u.employee_id,
        u.organization_id,
        e.full_name,
        e.employee_no
    FROM vms.app_user u
    LEFT JOIN vms.employee e ON e.id = u.employee_id
"""


class CRUDUser(CRUDBase):
    """
    CRUD untuk mengelola entitas User (Master Schema V2 & compat).
    """

    async def find_by_login(self, login: str) -> Any:
        """
        Mencari data pengguna beserta peran globalnya berdasarkan login (email atau username).
        """
        user = await self.fetchone(
            f"{_USER_WITH_ROLE} WHERE (u.email = :login OR u.username = :login) AND u.delete_at IS NULL",
            {"login": login},
        )
        if user:
            return user
        try:
            legacy = await self.fetchone(
                f"{_LEGACY_USER} WHERE u.login = :login",
                {"login": login},
            )
            if legacy:
                role_map = {
                    "ADMIN": "SUPER_ADMIN",
                    "PM": "PROJECT_MANAGER",
                    "HR": "ADMIN_HR_GA",
                }
                mapped_role = role_map.get(str(legacy.role).upper(), "EMPLOYEE")
                sync_sql = """
                    INSERT INTO public.users (
                        user_id, employee_id, username, email, password_hash, system_role, is_active
                    ) VALUES (
                        CAST(:uid AS uuid), CAST(:emp AS uuid), :uname, :email, :phash,
                        CAST(:role AS system_role_enum), :active
                    )
                    ON CONFLICT (user_id) DO NOTHING
                """
                with contextlib.suppress(SQLAlchemyError):
                    await self.execute(
                        sync_sql,
                        {
                            "uid": legacy.id,
                            "emp": legacy.employee_id,
                            "uname": str(legacy.login).split("@")[0],
                            "email": legacy.login,
                            "phash": legacy.password_hash,
                            "role": mapped_role,
                            "active": bool(legacy.is_active),
                        },
                    )
                return await self.fetchone(
                    f"{_USER_WITH_ROLE} WHERE u.user_id = CAST(:uid AS uuid) AND u.delete_at IS NULL",
                    {"uid": legacy.id},
                ) or legacy
        except SQLAlchemyError:
            return None
        return None

    async def find_by_id(self, user_id: UUID | str) -> Any:
        """
        Mencari data pengguna berdasarkan ID.
        """
        user = await self.fetchone(
            f"{_USER_WITH_ROLE} WHERE u.user_id = :id AND u.delete_at IS NULL",
            {"id": user_id},
        )
        if user:
            return user
        try:
            return await self.fetchone(
                f"{_LEGACY_USER} WHERE u.id = :id",
                {"id": user_id},
            )
        except SQLAlchemyError:
            return None

    async def find_identity(self, user_id: UUID | str) -> Any:
        """
        Mengambil status aktif akun dan peran dalam bentuk list (array).
        Digunakan di setiap request untuk authorisasi token.
        """
        identity = await self.fetchone(
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
        if identity is not None:
            return identity

        try:
            return await self.fetchone(
                """
                SELECT
                    u.id,
                    u.login,
                    u.login AS email,
                    u.is_active,
                    u.organization_id,
                    ARRAY(SELECT r.role::text FROM vms.user_role r WHERE r.user_id = u.id) AS roles
                FROM vms.app_user u
                WHERE u.id = :id
                """,
                {"id": user_id},
            )
        except SQLAlchemyError:
            return None

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
        emp = await self.scalar(
            "SELECT employee_id FROM users WHERE user_id = :uid AND delete_at IS NULL",
            {"uid": user_id},
        )
        if emp is not None:
            return emp
        try:
            return await self.scalar(
                "SELECT employee_id FROM vms.app_user WHERE id = :uid",
                {"uid": user_id},
            )
        except SQLAlchemyError:
            return None

    async def get_division_id(self, user_id: UUID | str) -> str | None:
        """
        Mendapatkan ID Divisi (division_id) yang menaungi pengguna atau karyawan pengguna ini.
        Prioritas:
        1. employee.division_id
        2. division.division_id bila pengguna adalah PM divisi (division.pm_id = user_id atau employee_id)
        3. division.division_id bila pengguna adalah OM divisi (division.om_id = user_id atau employee_id)
        """
        sql = """
        SELECT CAST(COALESCE(e.division_id, d_pm.division_id, d_om.division_id) AS text) AS division_id
        FROM users u
        LEFT JOIN employee e ON e.employee_id = u.employee_id AND e.delete_at IS NULL
        LEFT JOIN division d_pm ON (d_pm.pm_id = u.user_id OR d_pm.pm_id = u.employee_id) AND d_pm.delete_at IS NULL
        LEFT JOIN division d_om ON (d_om.om_id = u.user_id OR d_om.om_id = u.employee_id) AND d_om.delete_at IS NULL
        WHERE u.user_id = CAST(:uid AS uuid) AND u.delete_at IS NULL
        LIMIT 1
        """
        div_id = await self.scalar(sql, {"uid": user_id})
        return str(div_id) if div_id else None


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
            try:
                mode = await self.scalar(
                    "SELECT e.attendance_mode FROM vms.app_user u "
                    "JOIN vms.employee e ON e.id = u.employee_id WHERE u.id = :uid",
                    {"uid": user_id},
                )
                if mode is not None:
                    return mode
                role = await self.scalar(
                    "SELECT role::text FROM vms.user_role WHERE user_id = :uid LIMIT 1",
                    {"uid": user_id},
                )
            except SQLAlchemyError:
                return None

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
        return bool(
            await self.scalar(
                "SELECT EXISTS (SELECT 1 FROM users WHERE (email = :login OR username = :login) AND delete_at IS NULL)",
                {"login": login},
            )
        )

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

