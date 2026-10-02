"""
Rute autentikasi. Tipis (dok 12 §2): jalur, status, skema, dependency, dan cookie refresh.
Aturan bisnis ada di services/auth_service.py; transaksi di services/auth_flow.py.
"""
import ipaddress
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response

from app.api.deps import get_auth_flow_service, get_current_user
from app.core.security import CurrentUser
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    MessageResponse,
    RevokeOthersResponse,
    SessionOut,
    TokenResponse,
    UserMeResponse,
)
from app.services.auth_flow import AuthFlowService
from app.services.auth_service import ClientInfo, IssuedTokens

router = APIRouter(prefix="/auth", tags=["Authentication"])

REFRESH_COOKIE = "refresh_token"
REFRESH_COOKIE_MAX_AGE = 7 * 24 * 60 * 60
# Dok 02 A-11: cookie hanya dikirim ke rute auth, tidak pernah lintas situs.
REFRESH_COOKIE_PATH = "/api/v1/auth"



def client_info(request: Request) -> ClientInfo:
    host = request.client.host if request.client else None
    try:
        ip = str(ipaddress.ip_address(host)) if host else None
    except ValueError:
        ip = None  # kolom inet hanya menerima alamat IP yang sah
    return ClientInfo(ip=ip, user_agent=request.headers.get("user-agent", "Unknown"))


def _issue(response: Response, tokens: IssuedTokens) -> TokenResponse:
    response.set_cookie(
        key=REFRESH_COOKIE, value=tokens.refresh_token, httponly=True,
        secure=True, samesite="strict", max_age=REFRESH_COOKIE_MAX_AGE, path=REFRESH_COOKIE_PATH,
    )
    return TokenResponse(access_token=tokens.access_token)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest, request: Request, response: Response,
    flow: AuthFlowService = Depends(get_auth_flow_service),
) -> TokenResponse:
    tokens = await flow.login(payload.email, payload.password, client_info(request),
                              platform=payload.platform or "web")
    return _issue(response, tokens)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request, response: Response,
    flow: AuthFlowService = Depends(get_auth_flow_service),
) -> TokenResponse:
    tokens = await flow.refresh(request.cookies.get(REFRESH_COOKIE), client_info(request))
    return _issue(response, tokens)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request, response: Response,
    flow: AuthFlowService = Depends(get_auth_flow_service),
) -> MessageResponse:
    await flow.logout(request.cookies.get(REFRESH_COOKIE))
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH, secure=True, httponly=True, samesite="strict")
    return MessageResponse(message="Berhasil keluar.")


@router.get("/me", response_model=UserMeResponse)
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    flow: AuthFlowService = Depends(get_auth_flow_service),
) -> UserMeResponse:
    return await flow.me(current_user.user_id, current_user.permissions)


@router.get("/sessions", response_model=list[SessionOut])
async def list_sessions(
    current_user: CurrentUser = Depends(get_current_user),
    flow: AuthFlowService = Depends(get_auth_flow_service),
) -> list[SessionOut]:
    """P1-7: perangkat yang sedang masuk dengan akun ini; yang sedang dipakai ditandai `current`."""
    return await flow.active_sessions(current_user.user_id, current_user.session_id)


@router.post("/sessions/revoke-others", response_model=RevokeOthersResponse)
async def revoke_other_sessions(
    current_user: CurrentUser = Depends(get_current_user),
    flow: AuthFlowService = Depends(get_auth_flow_service),
) -> RevokeOthersResponse:
    """Keluarkan semua perangkat lain. Token akses mereka habis paling lama 15 menit; refresh langsung ditolak."""
    revoked = await flow.revoke_other_sessions(current_user.user_id, current_user.session_id)
    return RevokeOthersResponse(revoked=revoked, message="Perangkat lain dikeluarkan (paling lambat 15 menit).")


@router.post("/sessions/{session_id}/revoke", response_model=MessageResponse)
async def revoke_session(
    session_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    flow: AuthFlowService = Depends(get_auth_flow_service),
) -> MessageResponse:
    """Keluarkan satu perangkat milik sendiri. Sesi orang lain → 404."""
    await flow.revoke_session(current_user.user_id, str(session_id))
    return MessageResponse(message="Perangkat dikeluarkan (paling lambat 15 menit).")


@router.post("/change-password", response_model=TokenResponse)
async def change_password(
    payload: ChangePasswordRequest, request: Request, response: Response,
    current_user: CurrentUser = Depends(get_current_user),
    flow: AuthFlowService = Depends(get_auth_flow_service),
) -> TokenResponse:
    tokens = await flow.change_password(
        current_user.user_id, payload.current_password, payload.new_password, client_info(request)
    )
    return _issue(response, tokens)
