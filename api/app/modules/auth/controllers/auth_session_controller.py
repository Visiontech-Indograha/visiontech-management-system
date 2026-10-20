"""
app/modules/auth/controllers/auth_session_controller.py

Controller untuk manajemen sesi perangkat pengguna aktif.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends

from app.core.security import CurrentUser
from app.modules.auth.dependencies import get_auth_flow_service
from app.modules.auth.schemas.auth_profile_schema import AuthMessageResponseSchema
from app.modules.auth.schemas.auth_session_schema import (
    AuthRevokeOthersResponseSchema,
    AuthSessionResponseSchema,
)
from app.modules.auth.services.auth_flow_service import AuthFlowService


class AuthSessionController:
    """
    Controller use case manajemen sesi perangkat aktif pengguna.
    """

    def __init__(self, flow_service: AuthFlowService = Depends(get_auth_flow_service)) -> None:
        self.flow_service = flow_service

    async def handle_list_sessions(self, current_user: CurrentUser) -> list[AuthSessionResponseSchema]:
        """Mengambil seluruh sesi perangkat aktif untuk akun ini."""
        sessions = await self.flow_service.active_sessions(current_user.user_id, current_user.session_id)
        return [
            AuthSessionResponseSchema(
                id=s.id,
                device_label=s.device_label,
                ip_address=s.ip_address,
                user_agent=s.user_agent,
                issued_at=s.issued_at,
                last_used_at=s.last_used_at,
                current=s.current,
            )
            for s in sessions
        ]

    async def handle_revoke_other_sessions(self, current_user: CurrentUser) -> AuthRevokeOthersResponseSchema:
        """Mencabut seluruh sesi perangkat lain kecuali sesi saat ini."""
        revoked = await self.flow_service.revoke_other_sessions(current_user.user_id, current_user.session_id)
        return AuthRevokeOthersResponseSchema(
            revoked=revoked,
            message="Perangkat lain dikeluarkan (paling lambat 15 menit).",
        )

    async def handle_revoke_session(self, session_id: UUID, current_user: CurrentUser) -> AuthMessageResponseSchema:
        """Mencabut satu sesi perangkat tertentu milik pengguna."""
        if str(session_id) == str(current_user.session_id):
            from app.core.errors import AppError

            raise AppError(
                "CANNOT_REVOKE_CURRENT_SESSION",
                "Tidak dapat mencabut sesi perangkat saat ini. Gunakan menu Keluar (Logout) untuk keluar.",
                status=400,
            )
        await self.flow_service.revoke_session(current_user.user_id, str(session_id))
        return AuthMessageResponseSchema(message="Perangkat dikeluarkan (paling lambat 15 menit).")
