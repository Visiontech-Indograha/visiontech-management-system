"""
Kasus pakai autentikasi: membuka transaksi, memanggil AuthService, mengubah hasil ke skema.
Dipindah dari app/controllers/auth_controller.py (R-28 M4) tanpa perubahan perilaku.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import unit_of_work
from app.modules.auth.repositories.auth_session_repository import CRUDSession
from app.modules.auth.repositories.auth_user_repository import CRUDUser
from app.modules.auth.services.auth_service import AuthService, ClientInfo, IssuedTokens
from app.schemas.auth import SessionOut, UserMeResponse


class AuthFlowService:
    """
    Layanan alur autentikasi pengguna yang menggabungkan operasi AuthService dengan unit of work
    dan pemformatan respons Pydantic (schema).
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.service = AuthService(CRUDUser(db), CRUDSession(db))

    async def login(self, login: str, password: str, client: ClientInfo, platform: str = "web") -> IssuedTokens:
        """
        Alur untuk login pengguna. Membuka transaksi dan menerbitkan token akses dan penyegaran.

        Args:
            login (str): Email atau nama pengguna.
            password (str): Kata sandi pengguna.
            client (ClientInfo): Informasi client (IP dan user agent).
            platform (str): Platform yang digunakan untuk login (default: "web").

        Returns:
            IssuedTokens: Token akses dan penyegaran.
        """
        async with unit_of_work(self.db):
            return await self.service.login(login, password, client, platform=platform)

    async def refresh(self, raw_refresh_token: str | None, client: ClientInfo) -> IssuedTokens:
        """
        Alur untuk menyegarkan token (refresh token).

        Args:
            raw_refresh_token (str | None): Token penyegaran mentah.
            client (ClientInfo): Informasi client (IP dan user agent).

        Returns:
            IssuedTokens: Pasangan token baru (akses dan penyegaran).
        """
        async with unit_of_work(self.db):
            return await self.service.refresh(raw_refresh_token, client)

    async def logout(self, raw_refresh_token: str | None) -> None:
        """
        Alur untuk mengeluarkan pengguna (logout) dan mencabut sesi berdasarkan refresh token.

        Args:
            raw_refresh_token (str | None): Token penyegaran untuk sesi yang akan dilogout.
        """
        async with unit_of_work(self.db):
            await self.service.logout(raw_refresh_token)

    async def me(self, user_id: str, permissions: list[str]) -> UserMeResponse:
        """
        Mengambil profil pengguna yang sedang login beserta hak aksesnya.

        Args:
            user_id (str): ID pengguna saat ini.
            permissions (list[str]): Daftar izin akses yang dimiliki.

        Returns:
            UserMeResponse: Objek respons berisi profil pengguna.
        """
        profile = await self.service.me(user_id, permissions)
        return UserMeResponse(
            user_id=profile.user_id,
            email=profile.email,
            role=profile.role,
            permissions=profile.permissions,
            employee_id=profile.employee_id,
            attendance_mode=profile.attendance_mode,
            division_id=profile.division_id,
        )

    async def active_sessions(self, user_id: str, current_session_id: str) -> list[SessionOut]:
        """
        Mendapatkan daftar sesi aktif milik pengguna.

        Args:
            user_id (str): ID pengguna.
            current_session_id (str): ID sesi saat ini (untuk membedakan).

        Returns:
            list[SessionOut]: Daftar sesi yang aktif.
        """
        rows = await self.service.active_sessions(user_id)
        return [SessionOut(**r._mapping, current=str(r.id) == str(current_session_id)) for r in rows]

    async def revoke_session(self, user_id: str, session_id: str) -> None:
        """
        Mencabut/menghentikan satu sesi spesifik pengguna.

        Args:
            user_id (str): ID pengguna.
            session_id (str): ID sesi yang akan dicabut.
        """
        async with unit_of_work(self.db):
            await self.service.revoke_session(user_id, session_id)

    async def revoke_other_sessions(self, user_id: str, current_session_id: str) -> int:
        """
        Mencabut seluruh sesi aktif lainnya selain sesi yang sedang digunakan saat ini.

        Args:
            user_id (str): ID pengguna.
            current_session_id (str): ID sesi saat ini yang dikecualikan.

        Returns:
            int: Jumlah sesi yang berhasil dicabut.
        """
        async with unit_of_work(self.db):
            return await self.service.revoke_other_sessions(user_id, current_session_id)

    async def change_password(
        self, user_id: str, current_password: str, new_password: str, client: ClientInfo
    ) -> IssuedTokens:
        """
        Alur untuk mengganti kata sandi pengguna. Mengganti sandi akan mencabut semua sesi lainnya
        dan menerbitkan token baru untuk sesi saat ini.

        Args:
            user_id (str): ID pengguna.
            current_password (str): Kata sandi saat ini untuk validasi.
            new_password (str): Kata sandi baru yang akan disimpan.
            client (ClientInfo): Informasi klien untuk sesi baru.

        Returns:
            IssuedTokens: Token akses dan penyegaran baru.
        """
        async with unit_of_work(self.db):
            return await self.service.change_password(user_id, current_password, new_password, client)
