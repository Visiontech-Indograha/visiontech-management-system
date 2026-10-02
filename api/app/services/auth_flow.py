"""
Kasus pakai autentikasi: membuka transaksi, memanggil AuthService, mengubah hasil ke skema.
Dipindah dari app/controllers/auth_controller.py (R-28 M4) tanpa perubahan perilaku.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.crud_session import CRUDSession
from app.crud.crud_user import CRUDUser
from app.db.session import unit_of_work
from app.schemas.auth import SessionOut, UserMeResponse
from app.services.auth_service import AuthService, ClientInfo, IssuedTokens


class AuthFlowService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.service = AuthService(CRUDUser(db), CRUDSession(db))

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
            role=profile.role, permissions=profile.permissions, employee_id=profile.employee_id,
        )

    async def active_sessions(self, user_id: str, current_session_id: str) -> list[SessionOut]:
        rows = await self.service.active_sessions(user_id)
        return [SessionOut(**r._mapping, current=r.id == current_session_id) for r in rows]

    async def revoke_session(self, user_id: str, session_id: str) -> None:
        async with unit_of_work(self.db):
            await self.service.revoke_session(user_id, session_id)

    async def revoke_other_sessions(self, user_id: str, current_session_id: str) -> int:
        async with unit_of_work(self.db):
            return await self.service.revoke_other_sessions(user_id, current_session_id)

    async def change_password(
        self, user_id: str, current_password: str, new_password: str, client: ClientInfo
    ) -> IssuedTokens:
        async with unit_of_work(self.db):
            return await self.service.change_password(user_id, current_password, new_password, client)
