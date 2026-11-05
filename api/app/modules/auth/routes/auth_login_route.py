"""
app/modules/auth/routes/auth_login_route.py

Rute endpoint HTTP untuk login, refresh token, dan logout.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from fastapi import APIRouter, Depends, Request, Response

from app.core.rate_limit import GROUP_AUTH, rate_limit
from app.modules.auth.controllers.auth_login_controller import AuthLoginController
from app.modules.auth.schemas.auth_login_request_schema import AuthLoginRequestSchema
from app.modules.auth.schemas.auth_login_response_schema import AuthLoginResponseSchema
from app.modules.auth.schemas.auth_profile_schema import AuthMessageResponseSchema

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=AuthLoginResponseSchema, dependencies=[Depends(rate_limit(GROUP_AUTH))])
async def login(
    payload: AuthLoginRequestSchema,
    request: Request,
    response: Response,
    controller: AuthLoginController = Depends(),
) -> AuthLoginResponseSchema:
    """
    Memproses login pengguna dengan email dan password.
    """
    return await controller.handle_login(payload, request, response)


@router.post("/refresh", response_model=AuthLoginResponseSchema, dependencies=[Depends(rate_limit(GROUP_AUTH))])
async def refresh_token(
    request: Request,
    response: Response,
    controller: AuthLoginController = Depends(),
) -> AuthLoginResponseSchema:
    """
    Memperbarui access_token menggunakan refresh_token yang ada di cookie.
    """
    return await controller.handle_refresh(request, response)


@router.post("/logout", response_model=AuthMessageResponseSchema)
async def logout(
    request: Request,
    response: Response,
    controller: AuthLoginController = Depends(),
) -> AuthMessageResponseSchema:
    """
    Mengakhiri sesi pengguna saat ini dan mencabut cookie refresh_token.
    """
    return await controller.handle_logout(request, response)
