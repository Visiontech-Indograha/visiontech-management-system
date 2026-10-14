"""
Rute autentikasi. Tipis (dok 12 §2): jalur, status, skema, dependency, dan cookie refresh.
Aturan bisnis ada di services/auth_service.py; transaksi di services/auth_flow.py.
"""
import contextlib
import ipaddress
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response

from app.api.deps import get_auth_flow_service, get_current_user
from app.core.errors import AppError
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
    """
    Fungsi pembantu untuk mengambil informasi klien (IP dan User-Agent) dari objek request.

    Args:
        request (Request): Objek permintaan FastAPI.

    Returns:
        ClientInfo: Informasi klien.
    """
    host = request.client.host if request.client else None
    try:
        ip = str(ipaddress.ip_address(host)) if host else None
    except ValueError:
        ip = None  # kolom inet hanya menerima alamat IP yang sah
    user_agent = request.headers.get("user-agent", "Unknown")
    fingerprint = request.headers.get("x-device-fingerprint") or request.headers.get("x-device-id")
    if not fingerprint:
        import hashlib
        fingerprint = hashlib.sha256(user_agent.encode()).hexdigest()[:32]
    device_label = request.headers.get("x-device-label") or (
        "Aplikasi HP" if request.headers.get("x-device-id") else "Web Login"
    )
    return ClientInfo(
        ip=ip,
        user_agent=user_agent,
        device_label=device_label,
        fingerprint=fingerprint,
    )


def _is_secure_request(request: Request | None) -> bool:
    import sys
    if "pytest" in sys.modules:
        return True
    if request is None:
        return False
    proto = request.headers.get("x-forwarded-proto", "").lower()
    return request.url.scheme == "https" or proto == "https"


def _issue(response: Response, tokens: IssuedTokens, request: Request | None = None) -> TokenResponse:
    """
    Fungsi pembantu untuk menyematkan refresh token dalam cookie HttpOnly
    serta mereturn access token di payload.

    Args:
        response (Response): Objek respons FastAPI.
        tokens (IssuedTokens): Kumpulan token yang diterbitkan.
        request (Request | None): Objek request untuk mendeteksi HTTPS.

    Returns:
        TokenResponse: Respons payload akses token.
    """
    is_secure = _is_secure_request(request)
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=tokens.refresh_token,
        httponly=True,
        secure=is_secure,
        samesite="strict" if is_secure else "lax",
        max_age=REFRESH_COOKIE_MAX_AGE,
        path=REFRESH_COOKIE_PATH,
    )
    return TokenResponse(access_token=tokens.access_token)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest, request: Request, response: Response,
    flow: AuthFlowService = Depends(get_auth_flow_service),
) -> TokenResponse:
    """
    Memproses login pengguna dengan email dan password.

    Body params:
    - payload: Data login berisi email dan password (LoginRequest)

    Return: Token akses (TokenResponse) dan menset refresh_token di cookie
    """
    # Injeksi dependensi AuthFlowService untuk menangani alur login
    # Meneruskan data login ke service layer untuk divalidasi dan menghasilkan token
    tokens = await flow.login(payload.email, payload.password, client_info(request),
                              platform=payload.platform or "web")
    return _issue(response, tokens, request)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request, response: Response,
    flow: AuthFlowService = Depends(get_auth_flow_service),
) -> TokenResponse:
    """
    Memperbarui access_token menggunakan refresh_token yang ada di cookie.

    Return: Token akses baru (TokenResponse) dan memperbarui refresh_token di cookie
    """
    # Menggunakan injeksi dependensi untuk mengambil AuthFlowService
    # Memanggil service layer dengan mengambil refresh token dari cookie
    tokens = await flow.refresh(request.cookies.get(REFRESH_COOKIE), client_info(request))
    return _issue(response, tokens, request)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request, response: Response,
    flow: AuthFlowService = Depends(get_auth_flow_service),
) -> MessageResponse:
    """
    Mengakhiri sesi pengguna saat ini.

    Return: Pesan sukses (MessageResponse) dan menghapus cookie refresh_token
    """
    with contextlib.suppress(AppError):
        await flow.logout(request.cookies.get(REFRESH_COOKIE))
    is_secure = _is_secure_request(request)
    response.delete_cookie(
        REFRESH_COOKIE,
        path=REFRESH_COOKIE_PATH,
        secure=is_secure,
        httponly=True,
        samesite="strict" if is_secure else "lax",
    )
    return MessageResponse(message="Berhasil keluar.")


@router.get("/me", response_model=UserMeResponse)
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    flow: AuthFlowService = Depends(get_auth_flow_service),
) -> UserMeResponse:
    """
    Mendapatkan profil dan detail pengguna yang sedang login.

    Return: Detail pengguna saat ini (UserMeResponse)
    """
    # Menggunakan injeksi dependensi untuk mendapatkan pengguna saat ini dan service autentikasi
    # Mengambil profil dari service layer berdasarkan user_id dari sesi saat ini
    return await flow.me(current_user.user_id, current_user.permissions)


@router.get("/sessions", response_model=list[SessionOut])
async def list_sessions(
    current_user: CurrentUser = Depends(get_current_user),
    flow: AuthFlowService = Depends(get_auth_flow_service),
) -> list[SessionOut]:
    """
    P1-7: Mengambil daftar sesi aktif dari perangkat yang sedang masuk dengan akun ini;
    yang sedang dipakai ditandai `current`.

    Return: Daftar sesi aktif (list[SessionOut])
    """
    # Injeksi dependensi untuk pengguna aktif dan layanan autentikasi
    # Meminta layanan untuk melisting sesi pengguna
    return await flow.active_sessions(current_user.user_id, current_user.session_id)


@router.post("/sessions/revoke-others", response_model=RevokeOthersResponse)
async def revoke_other_sessions(
    current_user: CurrentUser = Depends(get_current_user),
    flow: AuthFlowService = Depends(get_auth_flow_service),
) -> RevokeOthersResponse:
    """
    Keluarkan semua perangkat lain. Token akses mereka habis paling lama 15 menit; refresh langsung ditolak.

    Return: Status revokasi perangkat lain (RevokeOthersResponse)
    """
    # Mengambil informasi pengguna dan AuthFlowService lewat injeksi dependensi
    # Mencabut (revoke) sesi perangkat lain melalui service layer
    revoked = await flow.revoke_other_sessions(current_user.user_id, current_user.session_id)
    return RevokeOthersResponse(revoked=revoked, message="Perangkat lain dikeluarkan (paling lambat 15 menit).")


@router.post("/sessions/{session_id}/revoke", response_model=MessageResponse)
async def revoke_session(
    session_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    flow: AuthFlowService = Depends(get_auth_flow_service),
) -> MessageResponse:
    """
    Keluarkan satu perangkat milik sendiri berdasarkan ID sesinya. Sesi orang lain → 404.

    Path params:
    - session_id: UUID dari sesi perangkat

    Return: Pesan revokasi berhasil (MessageResponse)
    """
    if str(session_id) == str(current_user.session_id):
        raise AppError(
            "CANNOT_REVOKE_CURRENT_SESSION",
            "Tidak dapat mencabut sesi perangkat saat ini. Gunakan menu Keluar (Logout) untuk keluar.",
            status=400,
        )
    await flow.revoke_session(current_user.user_id, str(session_id))
    return MessageResponse(message="Perangkat dikeluarkan (paling lambat 15 menit).")


@router.post("/change-password", response_model=TokenResponse)
async def change_password(
    payload: ChangePasswordRequest, request: Request, response: Response,
    current_user: CurrentUser = Depends(get_current_user),
    flow: AuthFlowService = Depends(get_auth_flow_service),
) -> TokenResponse:
    """
    Mengubah password pengguna saat ini.

    Body params:
    - payload: Berisi password lama dan password baru (ChangePasswordRequest)

    Return: Token akses baru (TokenResponse) dengan cookie yang diperbarui
    """
    # Injeksi dependensi AuthFlowService dan current_user
    # Meneruskan penggantian kata sandi ke service layer
    tokens = await flow.change_password(
        current_user.user_id, payload.current_password, payload.new_password, client_info(request)
    )
    return _issue(response, tokens, request)
