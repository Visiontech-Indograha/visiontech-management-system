"""
app/modules/auth/routes/auth_session_route.py

Rute endpoint HTTP untuk manajemen sesi perangkat aktif.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.security import CurrentUser
from app.modules.auth.controllers.auth_session_controller import AuthSessionController
from app.modules.auth.schemas.auth_profile_schema import AuthMessageResponseSchema
from app.modules.auth.schemas.auth_session_schema import (
    AuthRevokeOthersResponseSchema,
    AuthSessionResponseSchema,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/sessions", response_model=list[AuthSessionResponseSchema])
async def list_sessions(
    current_user: CurrentUser = Depends(get_current_user),
    controller: AuthSessionController = Depends(),
) -> list[AuthSessionResponseSchema]:
    """
    Mengambil daftar sesi aktif dari perangkat yang sedang masuk dengan akun ini.
    """
    return await controller.handle_list_sessions(current_user)


@router.post("/sessions/revoke-others", response_model=AuthRevokeOthersResponseSchema)
async def revoke_other_sessions(
    current_user: CurrentUser = Depends(get_current_user),
    controller: AuthSessionController = Depends(),
) -> AuthRevokeOthersResponseSchema:
    """
    Mencabut seluruh sesi perangkat lain.
    """
    return await controller.handle_revoke_other_sessions(current_user)


@router.post("/sessions/{session_id}/revoke", response_model=AuthMessageResponseSchema)
async def revoke_session(
    session_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: AuthSessionController = Depends(),
) -> AuthMessageResponseSchema:
    """
    Mencabut satu sesi perangkat tertentu milik sendiri.
    """
    return await controller.handle_revoke_session(session_id, current_user)
