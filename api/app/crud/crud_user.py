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
    """
    CRUD untuk mengelola entitas AppUser (pengguna aplikasi).
    Mendukung pencarian pengguna, peran, serta pembuatan akun untuk karyawan.
    """

    async def find_by_login(self, login: str) -> Any:
        """
        Mencari data pengguna beserta peran globalnya berdasarkan login (username/email).

        Args:
            login (str): Identifier login pengguna.

        Returns:
            Any: Record pengguna jika ditemukan, None jika tidak.
        """
        # Melakukan pencarian menggunakan query dasar _USER_WITH_ROLE yang menggabungkan
        # app_user dan user_role.
        return await self.fetchone(f"{_USER_WITH_ROLE} WHERE u.login = :login", {"login": login})

    async def find_by_id(self, user_id: UUID | str) -> Any:
        """
        Mencari data pengguna berdasarkan ID.

        Args:
            user_id (UUID | str): ID pengguna.

        Returns:
            Any: Record pengguna.
        """
        # Mengambil informasi profil lengkap user berdasarkan primary key.
        return await self.fetchone(f"{_USER_WITH_ROLE} WHERE u.id = :id", {"id": user_id})

    async def find_identity(self, user_id: UUID | str) -> Any:
        """
        Mengambil status aktif akun dan seluruh peran global dalam bentuk list (array).
        Digunakan di setiap request untuk authorisasi token.

        Args:
            user_id (UUID | str): ID pengguna.

        Returns:
            Any: Record berisi status aktif dan list peran.
        """
        # Menggabungkan role menjadi sebuah array (menggunakan array_agg di PostgreSQL)
        # sehingga semua hak akses pengguna bisa diambil dalam 1 query.
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
        """
        Memperbarui hash password pengguna.

        Args:
            user_id (UUID | str): ID pengguna.
            password_hash (str): Hash password baru.
        """
        # Memperbarui nilai hash password di tabel app_user.
        await self.execute(
            "UPDATE vms.app_user SET password_hash = :hash WHERE id = :id",
            {"hash": password_hash, "id": user_id},
        )

    async def get_employee_id(self, user_id: UUID | str) -> UUID | None:
        """
        Mendapatkan ID Karyawan (employee_id) yang tertaut ke akun pengguna ini.

        Args:
            user_id (UUID | str): ID pengguna aplikasi.

        Returns:
            UUID | None: ID karyawan jika tertaut, atau None.
        """
        # Mengambil mapping employee_id dari entitas user.
        employee_id: UUID | None = await self.scalar(
            "SELECT employee_id FROM vms.app_user WHERE id = :uid",
            {"uid": user_id},
        )
        return employee_id

    async def get_attendance_mode(self, user_id: UUID | str) -> str | None:
        """
        Mendapatkan mode absensi yang diberlakukan kepada karyawan terkait.

        Args:
            user_id (UUID | str): ID pengguna.

        Returns:
            str | None: Mode absensi (misal: 'FIELD', 'OFFICE').
        """
        # Menggabungkan app_user dengan tabel employee untuk mengekstrak attendance_mode.
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
        """
        Mengambil profil akun dari karyawan tertentu.
        Mencakup histori login gagal dan kapan status lock berakhir.

        Args:
            employee_id (UUID | str): ID karyawan.

        Returns:
            Any: Record akun dengan metrik kegagalan login.
        """
        # Menggunakan fungsi JOIN LATERAL untuk mengalkulasi jumlah kegagalan login
        # (mengacu ke query di _USER_WITH_ROLE dan FAILED_LOGINS_SQL) secara real-time.
        return await self.fetchone(
            f"""
            SELECT u.id, u.login, u.is_active, u.last_login_at, f.failures, f.locked_until
            FROM vms.app_user u
            LEFT JOIN LATERAL ({FAILED_LOGINS_SQL.format(login="u.login")}) f ON true
            WHERE u.employee_id = CAST(:emp AS uuid)
            """,
            {"emp": employee_id})

    async def login_taken(self, org_id: UUID | str, login: str) -> bool:
        """
        Mengecek apakah nama login tertentu sudah dipakai di organisasi.

        Args:
            org_id (UUID | str): ID organisasi.
            login (str): Nama login (username/email) yang akan dicek.

        Returns:
            bool: True jika sudah dipakai, False jika tersedia.
        """
        # Menggunakan klausa EXISTS untuk performa pengecekan ketersediaan yang cepat.
        return bool(await self.scalar(
            "SELECT EXISTS (SELECT 1 FROM vms.app_user WHERE organization_id = :org AND login = :login)",
            {"org": org_id, "login": login}))

    async def create_for_employee(self, org_id: UUID | str, employee_id: UUID | str, login: str,
                                  password_hash: str) -> Any:
        """
        Membuat akun pengguna baru untuk seorang karyawan.

        Args:
            org_id (UUID | str): ID organisasi.
            employee_id (UUID | str): ID karyawan yang akan dikaitkan.
            login (str): Nama login.
            password_hash (str): Hash kata sandi.

        Returns:
            Any: Detail singkat akun yang baru dibuat.
        """
        # Menyisipkan record app_user dan segera mengaktifkannya (is_active = true).
        return await self.fetchone(
            """
            INSERT INTO vms.app_user (organization_id, employee_id, login, password_hash, is_active)
            VALUES (:org, CAST(:emp AS uuid), :login, :hash, true)
            RETURNING id, login, is_active, last_login_at
            """,
            {"org": org_id, "emp": employee_id, "login": login, "hash": password_hash})

    async def set_active(self, user_id: UUID | str, active: bool) -> None:
        """
        Mengubah status aktif/non-aktif akun.

        Args:
            user_id (UUID | str): ID pengguna.
            active (bool): Status aktif yang baru.
        """
        # Memperbarui nilai is_active dan mengganti updated_at menjadi waktu saat ini.
        await self.execute("UPDATE vms.app_user SET is_active = :a, updated_at = now() WHERE id = :id",
                           {"a": active, "id": user_id})
