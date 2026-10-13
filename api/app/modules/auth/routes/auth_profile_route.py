"""
app/modules/auth/routes/auth_profile_route.py

Rute endpoint HTTP untuk identitas pengguna (/me) dan penggantian kata sandi.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""
from fastapi import APIRouter, Depends, Request, Response

from app.api.deps import get_current_user
from app.core.security import CurrentUser
from app.modules.auth.controllers.auth_profile_controller import AuthProfileController
from app.modules.auth.schemas.auth_login_response_schema import AuthLoginResponseSchema
from app.modules.auth.schemas.auth_profile_schema import (
    AuthChangePasswordRequestSchema,
    AuthUserMeResponseSchema,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/me", response_model=AuthUserMeResponseSchema)
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    controller: AuthProfileController = Depends(),
) -> AuthUserMeResponseSchema:
    """
    Mendapatkan profil dan detail pengguna yang sedang login.
    """
    return await controller.handle_get_me(current_user)


@router.post("/change-password", response_model=AuthLoginResponseSchema)
async def change_password(
    payload: AuthChangePasswordRequestSchema,
    request: Request,
    response: Response,
    current_user: CurrentUser = Depends(get_current_user),
    controller: AuthProfileController = Depends(),
) -> AuthLoginResponseSchema:
    """
    Mengubah password pengguna saat ini.
    """
    return await controller.handle_change_password(payload, request, response, current_user)

