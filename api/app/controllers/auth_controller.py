"""
app/controllers/auth_controller.py
Kasus pakai autentikasi: membuka transaksi, memanggil AuthService, mengubah hasil ke skema.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.transaction import unit_of_work
from app.repositories.session_repo import SessionRepo
from app.repositories.user_repo import UserRepo
from app.schemas.auth import UserMeResponse
from app.services.auth_service import AuthService, ClientInfo, IssuedTokens


class AuthController:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.service = AuthService(UserRepo(db), SessionRepo(db))

    async def login(self, login: str, password: str, client: ClientInfo) -> IssuedTokens:
        async with unit_of_work(self.db):
            return await self.service.login(login, password, client)

    async def refresh(self, raw_refresh_token: str | None, client: ClientInfo) -> IssuedTokens:
        async with unit_of_work(self.db):
            return await self.service.refresh(raw_refresh_token, client)

    async def logout(self, raw_refresh_token: str | None) -> None:
        async with unit_of_work(self.db):
            await self.service.logout(raw_refresh_token)

    async def me(self, user_id: str, permissions: list[str]) -> UserMeResponse:
        profile = await self.service.me(user_id, permissions)
        return UserMeResponse(
            user_id=profile.user_id, email=profile.email,
            role=profile.role, permissions=profile.permissions,
        )

    async def change_password(
        self, user_id: str, current_password: str, new_password: str, client: ClientInfo
    ) -> IssuedTokens:
        async with unit_of_work(self.db):
            return await self.service.change_password(user_id, current_password, new_password, client)
