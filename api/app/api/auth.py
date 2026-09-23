"""
Rute autentikasi. Tipis (dok 12 §2): jalur, status, skema, dependency, dan cookie refresh.
Aturan bisnis ada di services/auth_service.py; transaksi di controllers/auth_controller.py.
"""
import ipaddress

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DB_SCOPE, CurrentUser, get_current_user, get_db
from app.controllers.auth_controller import AuthController
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    MessageResponse,
    TokenResponse,
    UserMeResponse,
)
from app.services.auth_service import ClientInfo, IssuedTokens

router = APIRouter(prefix="/auth", tags=["Authentication"])

REFRESH_COOKIE = "refresh_token"
REFRESH_COOKIE_MAX_AGE = 7 * 24 * 60 * 60


def get_auth_controller(db: AsyncSession = Depends(get_db, scope=DB_SCOPE)) -> AuthController:
    return AuthController(db)


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
        secure=True, samesite="lax", max_age=REFRESH_COOKIE_MAX_AGE,
    )
    return TokenResponse(access_token=tokens.access_token)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest, request: Request, response: Response,
    controller: AuthController = Depends(get_auth_controller),
) -> TokenResponse:
    tokens = await controller.login(payload.email, payload.password, client_info(request))
    return _issue(response, tokens)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request, response: Response,
    controller: AuthController = Depends(get_auth_controller),
) -> TokenResponse:
    tokens = await controller.refresh(request.cookies.get(REFRESH_COOKIE), client_info(request))
    return _issue(response, tokens)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request, response: Response,
    controller: AuthController = Depends(get_auth_controller),
) -> MessageResponse:
    await controller.logout(request.cookies.get(REFRESH_COOKIE))
    response.delete_cookie(REFRESH_COOKIE)
    return MessageResponse(message="Berhasil keluar.")


@router.get("/me", response_model=UserMeResponse)
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    controller: AuthController = Depends(get_auth_controller),
) -> UserMeResponse:
    return await controller.me(current_user.user_id, current_user.permissions)


@router.post("/change-password", response_model=TokenResponse)
async def change_password(
    payload: ChangePasswordRequest, request: Request, response: Response,
    current_user: CurrentUser = Depends(get_current_user),
    controller: AuthController = Depends(get_auth_controller),
) -> TokenResponse:
    tokens = await controller.change_password(
        current_user.user_id, payload.current_password, payload.new_password, client_info(request)
    )
    return _issue(response, tokens)
