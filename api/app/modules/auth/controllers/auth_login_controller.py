"""
app/modules/auth/controllers/auth_login_controller.py

Controller untuk mengoordinasikan alur login, refresh token, dan logout.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""
from __future__ import annotations

import ipaddress

from fastapi import Depends, Request, Response

from app.api.deps import get_auth_flow_service
from app.modules.auth.schemas.auth_login_request_schema import AuthLoginRequestSchema
from app.modules.auth.schemas.auth_login_response_schema import AuthLoginResponseSchema
from app.modules.auth.schemas.auth_profile_schema import AuthMessageResponseSchema
from app.modules.auth.services.auth_flow_service import AuthFlowService
from app.modules.auth.services.auth_service import ClientInfo, IssuedTokens

REFRESH_COOKIE = "refresh_token"
REFRESH_COOKIE_MAX_AGE = 7 * 24 * 60 * 60
REFRESH_COOKIE_PATH = "/api/v1/auth"


class AuthLoginController:
    """
    Controller orkestrasi alur login dan siklus refresh token.
    """

    def __init__(self, flow_service: AuthFlowService = Depends(get_auth_flow_service)) -> None:
        self.flow_service = flow_service

    @staticmethod
    def extract_client_info(request: Request) -> ClientInfo:
        """Mengambil IP dan User-Agent dari permintaan HTTP."""
        host = request.client.host if request.client else None
        try:
            ip = str(ipaddress.ip_address(host)) if host else None
        except ValueError:
            ip = None
        return ClientInfo(ip=ip, user_agent=request.headers.get("user-agent", "Unknown"))

    @staticmethod
    def issue_token_response(response: Response, tokens: IssuedTokens) -> AuthLoginResponseSchema:
        """Menyematkan cookie HttpOnly dan mengembalikan schema respons token."""
        response.set_cookie(
            key=REFRESH_COOKIE,
            value=tokens.refresh_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=REFRESH_COOKIE_MAX_AGE,
            path=REFRESH_COOKIE_PATH,
        )
        return AuthLoginResponseSchema(access_token=tokens.access_token)

    async def handle_login(
        self, payload: AuthLoginRequestSchema, request: Request, response: Response
    ) -> AuthLoginResponseSchema:
        """Menangani use case login pengguna."""
        tokens = await self.flow_service.login(
            payload.email,
            payload.password,
            self.extract_client_info(request),
            platform=payload.platform or "web",
        )
        return self.issue_token_response(response, tokens)

    async def handle_refresh(self, request: Request, response: Response) -> AuthLoginResponseSchema:
        """Menangani use case perpanjangan token akses."""
        refresh_token = request.cookies.get(REFRESH_COOKIE)
        tokens = await self.flow_service.refresh(refresh_token, self.extract_client_info(request))
        return self.issue_token_response(response, tokens)

    async def handle_logout(self, request: Request, response: Response) -> AuthMessageResponseSchema:
        """Menangani use case logout pengguna."""
        refresh_token = request.cookies.get(REFRESH_COOKIE)
        await self.flow_service.logout(refresh_token)
        response.delete_cookie(
            REFRESH_COOKIE,
            path=REFRESH_COOKIE_PATH,
            secure=True,
            httponly=True,
            samesite="strict",
        )
        return AuthMessageResponseSchema(message="Berhasil keluar.")

