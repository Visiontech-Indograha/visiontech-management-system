"""
app/modules/auth/routes/auth_device_route.py

Rute kredensial perangkat: terbitkan token perangkat (butuh login) dan masuk dengan token itu (tanpa token akses).
Kedua rute dibatasi per IP lewat rate limiter grup auth (log-only sesuai kebijakan).
"""

from fastapi import APIRouter, Depends, Request, Response

from app.api.deps import get_current_user
from app.core.rate_limit import GROUP_AUTH, rate_limit
from app.core.security import CurrentUser
from app.modules.auth.controllers.auth_device_controller import AuthDeviceController
from app.modules.auth.schemas.auth_device_schema import (
    BiometricLoginRequestSchema,
    BiometricLoginResponseSchema,
    DeviceCredentialResponseSchema,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/device-credential",
    response_model=DeviceCredentialResponseSchema,
    dependencies=[Depends(rate_limit(GROUP_AUTH))],
)
async def issue_device_credential(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    controller: AuthDeviceController = Depends(),
) -> DeviceCredentialResponseSchema:
    """Menerbitkan token perangkat (30 hari) untuk masuk dengan sidik jari. Token lama perangkat ini dicabut.
    Token hanya dikembalikan sekali."""
    return await controller.handle_issue(current_user, request)


@router.post(
    "/biometric-login",
    response_model=BiometricLoginResponseSchema,
    dependencies=[Depends(rate_limit(GROUP_AUTH))],
)
async def biometric_login(
    payload: BiometricLoginRequestSchema,
    request: Request,
    response: Response,
    controller: AuthDeviceController = Depends(),
) -> BiometricLoginResponseSchema:
    """Masuk dengan token perangkat. Token dipakai sekali lalu diganti token baru di respons."""
    return await controller.handle_biometric_login(payload, request, response)
