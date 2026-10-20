"""
Modul dependensi (dependencies) FastAPI untuk VMS.

Berisi fungsi-fungsi dependency injection (DI) untuk mendapatkan sesi database,
pengguna saat ini (current user), otorisasi peran/akses, dan pembuatan service.
"""
import logging
from collections.abc import AsyncIterator, Awaitable, Callable, Coroutine
from typing import Any, Literal
from uuid import UUID

import jwt
from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.alerts import send_security_alert
from app.core.errors import AppError, NotFoundError
from app.core.permissions import NO_GLOBAL_ROLE, Permission, RoleCode, permissions_for_roles
from app.core.security import CurrentUser, verify_file_access_ticket, verify_jwt_token
from app.core.time import utcnow
from app.database.session import AsyncSessionLocal, set_request_context, unit_of_work
from app.modules.auth.repositories.auth_user_repository import CRUDUser
from app.shared.access.access_service import PlanAccess, PlanNeed, check_plan_access
from app.shared.access.plan_access_repository import CRUDPlanAccess

logger = logging.getLogger(__name__)
# Keamanan dengan skema Bearer token
security = HTTPBearer(auto_error=False)  # token hilang → 401 UNAUTHENTICATED kita sendiri

# "function": commit/rollback terjadi SEBELUM respons dikirim, jadi commit yang gagal
# sampai ke klien sebagai 500 — bukan 200 untuk data yang ternyata tidak tersimpan.
DB_SCOPE: Literal["function", "request"] = "function"


async def get_db() -> AsyncIterator[AsyncSession]:
    """
    Menyediakan sesi database asinkron (AsyncSession) untuk satu siklus permintaan.
    Satu permintaan = satu transaksi: commit bila handler sukses, rollback bila galat (T-02).
    """
    async with AsyncSessionLocal() as session, unit_of_work(session):
        yield session


def _unauthenticated() -> AppError:
    """Mengembalikan objek AppError standar untuk otentikasi gagal (401)."""
    return AppError("UNAUTHENTICATED", "Sesi berakhir. Silakan masuk kembali.", status=401)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db, scope=DB_SCOPE),
) -> CurrentUser:
    """
    Mendapatkan pengguna saat ini yang sedang login berdasarkan token JWT.
    Token hanya membawa identitas (`sub`, `org`, `jti`). Status akun dan peran dibaca dari
    basis data pada setiap permintaan (dok 05 §4): mencabut peran atau menonaktifkan akun
    berlaku pada permintaan berikutnya.
    """
    if credentials is None:
        raise _unauthenticated()
    try:
        payload = verify_jwt_token(credentials.credentials)
    except jwt.PyJWTError:
        raise _unauthenticated() from None

    user_id, session_id = payload.get("sub"), payload.get("jti")
    if not user_id or not session_id:
        raise _unauthenticated()

    auth_time = payload.get("auth_time")
    if auth_time is not None:
        try:
            # Sesi berakhir otomatis jika umur login awal sudah melewati 24 jam (86400 detik)
            if int(utcnow().timestamp()) - int(auth_time) > 86400:
                raise _unauthenticated()
        except (ValueError, TypeError):
            pass

    # Memuat identitas dan peran terbaru dari database
    identity = await CRUDUser(db).find_identity(user_id)
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
        employee_id=str(identity.employee_id) if getattr(identity, "employee_id", None) else None,
    )


async def get_file_viewer(
    file_id: UUID,
    token: str | None = Query(None, alias="token"),
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db, scope=DB_SCOPE),
) -> CurrentUser:
    """
    Mendapatkan pengguna yang meminta isi berkas (GET /files/{file_id}).
    Mendukung dua kanal autentikasi yang aman:
    1. Header standar `Authorization: Bearer <access_token>`
    2. Tiket akses berkas `?token=<ticket>` yang diterbitkan /files/{file_id}/url
       (untuk tag <img> atau viewer dokumen yang tidak dapat menyertakan header Bearer).
    """
    if credentials is not None:
        try:
            payload = verify_jwt_token(credentials.credentials)
            user_id, session_id = payload.get("sub"), payload.get("jti")
            if not user_id or not session_id:
                raise _unauthenticated()

            auth_time = payload.get("auth_time")
            if auth_time is not None:
                try:
                    if int(utcnow().timestamp()) - int(auth_time) > 86400:
                        raise _unauthenticated()
                except (ValueError, TypeError):
                    pass
        except jwt.PyJWTError:
            # Jika header Authorization gagal diverifikasi, coba tiket akses berkas dari query parameter.
            if token is None:
                raise _unauthenticated() from None
            claims = verify_file_access_ticket(token, str(file_id))
            if claims is None:
                raise _unauthenticated() from None
            user_id = claims.get("sub")
            session_id = str(claims.get("jti") or "file-ticket")
            if not user_id:
                raise _unauthenticated() from None
    elif token is not None:
        claims = verify_file_access_ticket(token, str(file_id))
        if claims is None:
            raise _unauthenticated()
        user_id = claims.get("sub")
        session_id = str(claims.get("jti") or "file-ticket")
        if not user_id:
            raise _unauthenticated()
    else:
        raise _unauthenticated()

    identity = await CRUDUser(db).find_identity(user_id)
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
    """
    Memastikan pengguna saat ini memiliki izin (Permission) tertentu.
    Jika tidak, akan memunculkan galat 403 Forbidden.
    """
    async def permission_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if "ADMIN" in current_user.roles or RoleCode.ADMIN in current_user.roles:
            return current_user
        if required_permission.value not in current_user.permissions:
            raise AppError("FORBIDDEN", "Anda tidak memiliki akses untuk tindakan ini.", status=403)
        return current_user
    return permission_checker


def require_any_permission(
    *required: Permission,
) -> Callable[[CurrentUser], Coroutine[Any, Any, CurrentUser]]:
    """Lolos bila pengguna punya SALAH SATU izin yang disebut (mis. cari alamat: pengelola SK atau pengelola lokasi)."""
    async def permission_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if "ADMIN" in current_user.roles or RoleCode.ADMIN in current_user.roles:
            return current_user
        if not any(p.value in current_user.permissions for p in required):
            raise AppError("FORBIDDEN", "Anda tidak memiliki akses untuk tindakan ini.", status=403)
        return current_user
    return permission_checker


async def get_db_with_user(
    db: AsyncSession = Depends(get_db, scope=DB_SCOPE),
    current_user: CurrentUser = Depends(get_current_user),
) -> AsyncSession:
    """
    Menyediakan sesi database asinkron dengan konteks pengguna untuk RLS (Row-Level Security).
    Konteks mencakup ID pengguna, organisasi, dan email untuk keperluan audit.
    """
    # Konteks RLS & audit untuk transaksi permintaan ini (app/db/session.py).
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
        raise AppError("INTERNAL_ERROR", "Terjadi gangguan pada sistem. Coba lagi beberapa saat; bila berulang, hubungi admin.", status=500) from None
    return db


def plan_access(need: PlanNeed, archived: bool | None = False) -> Callable[..., Awaitable[PlanAccess]]:
    """Dependency untuk rute ber-`{plan_id}`. `archived=None`: SK aktif maupun draf terarsip
    (pemulihan) — terarsip tetap hanya terlihat oleh pengelola."""
    async def guard(
        plan_id: UUID,
        current_user: CurrentUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_with_user),
    ) -> PlanAccess:
        return await check_plan_access(db, plan_id, current_user, need, archived)
    return guard


def allocation_plan_access(need: PlanNeed) -> Callable[..., Awaitable[PlanAccess]]:
    """Dependency untuk rute ber-`{alloc_id}` — kewenangan mengikuti SK peminjam aset."""
    async def guard(
        alloc_id: UUID,
        current_user: CurrentUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_with_user),
    ) -> PlanAccess:
        plan_id = await CRUDPlanAccess(db).plan_of_allocation(alloc_id)
        if plan_id is None:
            raise NotFoundError("Alokasi aset")
        return await check_plan_access(db, plan_id, current_user, need)
    return guard


def incident_plan_access(need: PlanNeed) -> Callable[..., Awaitable[PlanAccess]]:
    """Dependency untuk rute ber-`{inc_id}` — kewenangan mengikuti SK tempat insiden terjadi."""
    async def guard(
        inc_id: UUID,
        current_user: CurrentUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_with_user),
    ) -> PlanAccess:
        plan_id = await CRUDPlanAccess(db).plan_of_incident(inc_id, current_user.organization_id)
        if plan_id is None:
            raise NotFoundError("Insiden")
        return await check_plan_access(db, plan_id, current_user, need)
    return guard


def plan_day_access(need: PlanNeed) -> Callable[..., Awaitable[PlanAccess]]:
    """Dependency untuk rute `/work-plans/{plan_id}/days/{day_id}` (V-16, dok 05 §3.6): kewenangan
    atas SK, dan hari harus milik SK itu — hari SK lain → 404."""
    async def guard(
        plan_id: UUID,
        day_id: UUID,
        current_user: CurrentUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_with_user),
    ) -> PlanAccess:
        access = await check_plan_access(db, plan_id, current_user, need)
        if str(await CRUDPlanAccess(db).plan_of_day(day_id)) != str(plan_id):
            raise NotFoundError("Hari kerja")
        return access
    return guard


# ── Perakitan service (R-28 M5) ─────────────────────────────────────────────
# Getter memakai dependency sesi yang SAMA dengan handler (`get_db_with_user`; `get_db` untuk rute publik;
# `get_db` + `DB_SCOPE` untuk auth), sehingga FastAPI memakai ulang satu sesi = satu transaksi per permintaan.


async def get_file_viewer_db(
    db: AsyncSession = Depends(get_db, scope=DB_SCOPE),
    current_user: CurrentUser = Depends(get_file_viewer),
) -> AsyncSession:
    """Pasang konteks RLS untuk route konten berkas, yang juga mengizinkan tiket URL."""
    try:
        await set_request_context(
            db,
            user_id=current_user.user_id,
            organization_id=current_user.organization_id,
            actor_label=current_user.email,
        )
    except SQLAlchemyError as exc:
        logger.exception("Konteks RLS gagal disetel untuk akses berkas")
        await send_security_alert(
            "Konteks RLS Gagal Disetel", f"Gagal menetapkan konteks RLS ({type(exc).__name__})."
        )
        raise AppError(
            "INTERNAL_ERROR",
            "Terjadi gangguan pada sistem. Coba lagi beberapa saat; bila berulang, hubungi admin.",
            status=500,
        ) from None
    return db
