"""
app/modules/auth/controllers/auth_profile_controller.py

Controller untuk identitas pengguna (/me) dan penggantian kata sandi.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""
from __future__ import annotations

from fastapi import Depends, Request, Response

from app.api.deps import get_auth_flow_service
from app.core.security import CurrentUser
from app.modules.auth.controllers.auth_login_controller import AuthLoginController
from app.modules.auth.schemas.auth_login_response_schema import AuthLoginResponseSchema
from app.modules.auth.schemas.auth_profile_schema import (
    AuthChangePasswordRequestSchema,
    AuthUserMeResponseSchema,
)
from app.modules.auth.services.auth_flow_service import AuthFlowService


class AuthProfileController:
    """
    Controller use case profil dan penggantian password pengguna.
    """

    def __init__(self, flow_service: AuthFlowService = Depends(get_auth_flow_service)) -> None:
        self.flow_service = flow_service

    async def handle_get_me(self, current_user: CurrentUser) -> AuthUserMeResponseSchema:
        """Mengambil profil lengkap pengguna aktif."""
        res = await self.flow_service.me(current_user.user_id, current_user.permissions)
        return AuthUserMeResponseSchema(
            user_id=res.user_id,
            email=res.email,
            role=res.role,
            permissions=res.permissions,
            employee_id=res.employee_id,
            attendance_mode=res.attendance_mode,
        )

    async def handle_change_password(
        self,
        payload: AuthChangePasswordRequestSchema,
        request: Request,
        response: Response,
        current_user: CurrentUser,
    ) -> AuthLoginResponseSchema:
        """Menangani penggantian kata sandi akun aktif."""
        client_info = AuthLoginController.extract_client_info(request)
        tokens = await self.flow_service.change_password(
            current_user.user_id,
            payload.current_password,
            payload.new_password,
            client_info,
        )
        return AuthLoginController.issue_token_response(response, tokens)

