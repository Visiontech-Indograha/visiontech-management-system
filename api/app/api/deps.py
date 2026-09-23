import logging
from collections.abc import AsyncIterator, Callable, Coroutine
from typing import Any, Literal

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.alerts import send_security_alert
from app.core.errors import AppError
from app.core.permissions import NO_GLOBAL_ROLE, Permission, permissions_for_roles
from app.core.security import verify_jwt_token
from app.db.context import set_request_context
from app.db.session import AsyncSessionLocal
from app.db.transaction import unit_of_work
from app.repositories.user_repo import UserRepo

logger = logging.getLogger(__name__)
security = HTTPBearer()

# "function": commit/rollback terjadi SEBELUM respons dikirim, jadi commit yang gagal
# sampai ke klien sebagai 500 — bukan 200 untuk data yang ternyata tidak tersimpan.
DB_SCOPE: Literal["function", "request"] = "function"


async def get_db() -> AsyncIterator[AsyncSession]:
    """Satu permintaan = satu transaksi: commit bila handler sukses, rollback bila galat (T-02)."""
    async with AsyncSessionLocal() as session, unit_of_work(session):
        yield session


class CurrentUser(BaseModel):
    user_id: str
    organization_id: str
    email: str
    role: str
    roles: list[str]
    session_id: str
    permissions: list[str]


def _unauthenticated() -> AppError:
    return AppError("UNAUTHENTICATED", "Sesi berakhir. Silakan masuk kembali.", status=401)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db, scope=DB_SCOPE),
) -> CurrentUser:
    """
    Token hanya membawa identitas (`sub`, `org`, `jti`). Status akun dan peran dibaca dari
    basis data pada setiap permintaan (dok 05 §4): mencabut peran atau menonaktifkan akun
    berlaku pada permintaan berikutnya.
    """
    try:
        payload = verify_jwt_token(credentials.credentials)
    except jwt.PyJWTError:
        raise _unauthenticated() from None
    user_id, session_id = payload.get("sub"), payload.get("jti")
    if not user_id or not session_id:
        raise _unauthenticated()

    identity = await UserRepo(db).find_identity(user_id)
    if not identity or not identity.is_active:
        raise _unauthenticated()

    roles = list(identity.roles)
    return CurrentUser(
        user_id=user_id,
        organization_id=str(identity.organization_id),
        email=identity.login,
        role=roles[0] if roles else NO_GLOBAL_ROLE,
        roles=roles,
        session_id=session_id,
        permissions=permissions_for_roles(roles or [NO_GLOBAL_ROLE]),
    )


def require_permission(
    required_permission: Permission,
) -> Callable[[CurrentUser], Coroutine[Any, Any, CurrentUser]]:
    async def permission_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if required_permission.value not in current_user.permissions:
            raise AppError("FORBIDDEN", "Anda tidak memiliki akses untuk tindakan ini.", status=403)
        return current_user
    return permission_checker


async def get_db_with_user(
    db: AsyncSession = Depends(get_db, scope=DB_SCOPE),
    current_user: CurrentUser = Depends(get_current_user),
) -> AsyncSession:
    # Konteks RLS & audit untuk transaksi permintaan ini (app/db/context.py).
    try:
        await set_request_context(
            db,
            user_id=current_user.user_id,
            organization_id=current_user.organization_id,
            actor_label=current_user.email,
        )
    except SQLAlchemyError as exc:
        # Dok 17: tanpa data pribadi & tanpa isi galat DB ke Discord; detail lengkap ada di log.
        logger.exception("Konteks RLS gagal disetel")
        await send_security_alert(
            "Konteks RLS Gagal Disetel", f"Gagal menetapkan konteks RLS ({type(exc).__name__})."
        )
        raise AppError("INTERNAL_ERROR", "Terjadi kesalahan internal pada server.", status=500) from None
    return db

