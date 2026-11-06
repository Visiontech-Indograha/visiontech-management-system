"""
app/modules/auth/controllers/auth_device_controller.py

Controller kredensial perangkat (masuk dengan sidik jari).
"""

from __future__ import annotations

from fastapi import Depends, Request, Response

from app.core.security import CurrentUser
from app.modules.auth.controllers.auth_login_controller import AuthLoginController
from app.modules.auth.dependencies import get_auth_flow_service
from app.modules.auth.schemas.auth_device_schema import (
    BiometricLoginRequestSchema,
    BiometricLoginResponseSchema,
    DeviceCredentialResponseSchema,
)
from app.modules.auth.services.auth_flow_service import AuthFlowService


class AuthDeviceController:
    def __init__(self, flow_service: AuthFlowService = Depends(get_auth_flow_service)) -> None:
        self.flow_service = flow_service

    async def handle_issue(self, current_user: CurrentUser, request: Request) -> DeviceCredentialResponseSchema:
        client = AuthLoginController.extract_client_info(request)
        token, expires_at, label = await self.flow_service.issue_device_credential(current_user.user_id, client)
        return DeviceCredentialResponseSchema(device_token=token, expires_at=expires_at, device_label=label)

    async def handle_biometric_login(
        self, payload: BiometricLoginRequestSchema, request: Request, response: Response
    ) -> BiometricLoginResponseSchema:
        client = AuthLoginController.extract_client_info(request)
        tokens, device_token, expires_at = await self.flow_service.biometric_login(payload.device_token, client)
        base = AuthLoginController.issue_token_response(response, tokens, request)
        return BiometricLoginResponseSchema(
            access_token=base.access_token, device_token=device_token, device_token_expires_at=expires_at
        )
