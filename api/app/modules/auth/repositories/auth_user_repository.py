"""
app/modules/auth/repositories/auth_user_repository.py
Kueri akun (`users`) beserta karyawan tertautnya (`employee`) — Master Schema V2.
Organisasi pengguna = kantor karyawannya (`employee.office_id`); akun tanpa karyawan memakai kantor utama.
"""

from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository

# Peran kantor (masuk lewat web) vs lapangan (masuk lewat aplikasi HP) — docs/35 §1.
OFFICE_ROLES = ("SUPER_ADMIN", "OPERATIONAL_MANAGER", "PROJECT_MANAGER", "ADMIN_HR_GA")
FIELD_ROLES = ("TEAM_LEADER", "EMPLOYEE")

_MAIN_OFFICE = "(SELECT office_id FROM office WHERE is_main_office AND delete_at IS NULL LIMIT 1)"

_USER_WITH_ROLE = f"""
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
        COALESCE(e.office_id, {_MAIN_OFFICE}) AS organization_id,
        e.full_name,
        e.employee_no
    FROM users u
    LEFT JOIN employee e ON e.employee_id = u.employee_id AND e.delete_at IS NULL
"""


class AuthUserRepository(BaseRepository):
    """Repositori akun pengguna & kredensial (tabel `users`)."""

    async def find_by_login(self, login: str) -> Any:
        """Akun aktif (belum dihapus) berdasarkan email atau username."""
        return await self.fetchone(
            f"{_USER_WITH_ROLE} WHERE (u.email = :login OR u.username = :login) AND u.delete_at IS NULL",
            {"login": login},
        )

    async def find_by_id(self, user_id: UUID | str) -> Any:
        """Akun berdasarkan ID."""
        return await self.fetchone(
            f"{_USER_WITH_ROLE} WHERE u.user_id = CAST(:id AS uuid) AND u.delete_at IS NULL",
            {"id": user_id},
        )

    async def session_alive(self, session_id: UUID | str) -> bool:
        """Keluarga sesi token masih punya refresh aktif (logout/cabut perangkat langsung berlaku)."""
        row = await self.fetchone(
            """
            SELECT 1 AS ok FROM user_sessions s
            WHERE s.token_family_id = (SELECT token_family_id FROM user_sessions WHERE session_id = CAST(:sid AS uuid))
              AND s.is_revoked = FALSE AND s.delete_at IS NULL AND s.expires_at > now()
            LIMIT 1
            """,
            {"sid": str(session_id)},
        )
        return row is not None

    async def find_identity(self, user_id: UUID | str) -> Any:
        """Status aktif & peran akun — dibaca ulang dari DB pada setiap permintaan (bukan dari klaim token)."""
        return await self.fetchone(
            f"""
            SELECT
                u.user_id AS id,
                u.employee_id,
                u.email AS login,
                u.email,
                u.is_active,
                COALESCE(e.office_id, {_MAIN_OFFICE}) AS organization_id,
                ARRAY[u.system_role::text] AS roles
            FROM users u
            LEFT JOIN employee e ON e.employee_id = u.employee_id AND e.delete_at IS NULL
            WHERE u.user_id = CAST(:id AS uuid) AND u.delete_at IS NULL
            """,
            {"id": user_id},
        )

    async def update_password_hash(self, user_id: UUID | str, password_hash: str) -> None:
        await self.execute(
            "UPDATE users SET password_hash = :hash, update_at = now() "
            "WHERE user_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"hash": password_hash, "id": user_id},
        )

    async def get_employee_id(self, user_id: UUID | str) -> UUID | None:
        """Karyawan yang tertaut ke akun ini (users.employee_id → employee)."""
        emp: UUID | None = await self.scalar(
            "SELECT employee_id FROM users WHERE user_id = CAST(:uid AS uuid) AND delete_at IS NULL",
            {"uid": user_id},
        )
        return emp

    async def full_name(self, user_id: UUID | str) -> str | None:
        """Nama lengkap karyawan yang tertaut ke akun ini (untuk sapaan di aplikasi)."""
        name = await self.scalar(
            "SELECT e.full_name FROM users u JOIN employee e ON e.employee_id = u.employee_id "
            "WHERE u.user_id = CAST(:uid AS uuid) AND u.delete_at IS NULL",
            {"uid": user_id},
        )
        return str(name) if name else None

    async def profile_photo_file_id(self, user_id: UUID | str) -> str | None:
        """ID berkas foto profil karyawan yang tertaut ke akun ini (URL bertanda tangan diambil klien terpisah)."""
        photo = await self.scalar(
            """
            SELECT e.profile_photo_path
            FROM users u
            JOIN employee e ON e.employee_id = u.employee_id AND e.delete_at IS NULL
            WHERE u.user_id = CAST(:uid AS uuid) AND u.delete_at IS NULL
            """,
            {"uid": user_id},
        )
        return str(photo) if photo else None

    async def get_division_id(self, user_id: UUID | str) -> str | None:
        """
        Divisi pengguna: `employee.division_id`, atau divisi yang ia pimpin sebagai PM/OM
        (`division.pm_id` / `division.om_id` → employee).
        """
        div_id = await self.scalar(
            """
            SELECT CAST(COALESCE(e.division_id, d_pm.division_id, d_om.division_id) AS text)
            FROM users u
            LEFT JOIN employee e ON e.employee_id = u.employee_id AND e.delete_at IS NULL
            LEFT JOIN division d_pm ON d_pm.pm_id = u.employee_id AND d_pm.delete_at IS NULL
            LEFT JOIN division d_om ON d_om.om_id = u.employee_id AND d_om.delete_at IS NULL
            WHERE u.user_id = CAST(:uid AS uuid) AND u.delete_at IS NULL
            LIMIT 1
            """,
            {"uid": user_id},
        )
        return str(div_id) if div_id else None

    async def get_attendance_mode(self, user_id: UUID | str) -> str | None:
        """OFFICE untuk peran kantor (web), FIELD untuk peran lapangan (aplikasi HP) — docs/35 §1."""
        role = await self.scalar(
            "SELECT system_role::text FROM users WHERE user_id = CAST(:uid AS uuid) AND delete_at IS NULL",
            {"uid": user_id},
        )
        if not role:
            return None
        return "OFFICE" if role in OFFICE_ROLES else "FIELD"

    async def account_of_employee(self, employee_id: UUID | str) -> Any:
        """Akun milik seorang karyawan (relasi 1–1 employee → users)."""
        return await self.fetchone(
            """
            SELECT
                u.user_id AS id,
                u.employee_id,
                u.email AS login,
                u.username,
                u.system_role::text AS role,
                u.is_active,
                u.update_at AS last_login_at
            FROM users u
            WHERE u.employee_id = CAST(:emp AS uuid) AND u.delete_at IS NULL
            """,
            {"emp": employee_id},
        )

    async def login_taken(self, org_id: UUID | str, login: str) -> bool:
        """Email/username sudah dipakai akun aktif lain (email unik secara global, uq_users_email_active)."""
        return bool(
            await self.scalar(
                "SELECT EXISTS (SELECT 1 FROM users WHERE (email = :login OR username = :login) AND delete_at IS NULL)",
                {"login": login},
            )
        )

    async def create_for_employee(
        self, org_id: UUID | str, employee_id: UUID | str, login: str, password_hash: str, system_role: str = "EMPLOYEE"
    ) -> Any:
        """Akun baru untuk seorang karyawan."""
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
        await self.execute(
            "UPDATE users SET is_active = :a, update_at = now() "
            "WHERE user_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"a": active, "id": user_id},
        )


CRUDUser = AuthUserRepository
