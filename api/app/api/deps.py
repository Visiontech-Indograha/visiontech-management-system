"""
Modul dependensi (dependencies) FastAPI untuk VMS.

Berisi fungsi-fungsi dependency injection (DI) untuk mendapatkan sesi database,
pengguna saat ini (current user), otorisasi peran/akses, dan pembuatan service.
"""
import hashlib
import json
import logging
import re
from collections.abc import AsyncIterator, Awaitable, Callable, Coroutine
from typing import Any, Literal, TypeVar
from uuid import UUID

import jwt
from fastapi import Depends, Header, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.alerts import send_security_alert
from app.core.errors import AppError
from app.core.permissions import NO_GLOBAL_ROLE, Permission, RoleCode, permissions_for_roles
from app.core.security import CurrentUser, verify_file_access_ticket, verify_jwt_token
from app.core.time import utcnow
from app.database.session import AsyncSessionLocal, set_request_context, unit_of_work
from app.modules.auth.repositories.auth_user_repository import CRUDUser
from app.shared import idempotency_repository as repo
from app.shared.access.access_service import DailyAccess, DailyNeed, check_daily_access
from app.shared.access.office_scope import ensure_employee_in_scope, ensure_office_in_scope

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
    users = CRUDUser(db)
    identity = await users.find_identity(user_id)
    if not identity or not identity.is_active:
        raise _unauthenticated()
    try:
        alive = await users.session_alive(UUID(str(session_id)))
    except ValueError:
        alive = False
    if not alive:
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
        # Tanpa ini pemeriksaan "boleh melihat jadwal" (foto bukti/survei) selalu gagal untuk <img>/tiket berkas.
        employee_id=str(identity.employee_id) if getattr(identity, "employee_id", None) else None,
    )


def _is_legacy_admin(current_user: CurrentUser) -> bool:
    return "ADMIN" in current_user.roles or RoleCode.ADMIN in current_user.roles


def require_permission(
    required_permission: Permission,
) -> Callable[[CurrentUser], Coroutine[Any, Any, CurrentUser]]:
    """
    Memastikan pengguna saat ini memiliki izin (Permission) tertentu.
    Jika tidak, akan memunculkan galat 403 Forbidden.
    """
    async def permission_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        # ADMIN lama lolos semua izin KECUALI hapus permanen (DELETE_ANY khusus SUPER_ADMIN, lihat core/permissions.py).
        if _is_legacy_admin(current_user) and required_permission is not Permission.DELETE_ANY:
            return current_user
        if required_permission.value not in current_user.permissions:
            raise AppError("FORBIDDEN", "Anda tidak memiliki akses untuk tindakan ini.", status=403)
        return current_user
    return permission_checker


def require_permission_for_employee(
    required_permission: Permission, param: str = "employee_id",
) -> Callable[..., Coroutine[Any, Any, CurrentUser]]:
    """`require_permission` + pembatasan kantor HR/Finance (ADR 0002): karyawan target pada parameter jalur `param`
    harus berkantor di jangkauan izin; di luar itu 404. Flag peran-ganda mati = sama persis dengan require_permission."""
    guard = require_permission(required_permission)

    async def permission_checker(
        request: Request,
        current_user: CurrentUser = Depends(guard),
        db: AsyncSession = Depends(get_db_with_user),
    ) -> CurrentUser:
        raw = request.path_params.get(param)
        try:
            target = UUID(str(raw)) if raw else None
        except ValueError:
            target = None
        await ensure_employee_in_scope(db, current_user, required_permission, target)
        return current_user
    return permission_checker


def require_permission_for_office(
    required_permission: Permission, param: str = "office_id",
) -> Callable[..., Coroutine[Any, Any, CurrentUser]]:
    """Seperti `require_permission_for_employee`, untuk kantor pada parameter jalur `param` (404 di luar jangkauan)."""
    guard = require_permission(required_permission)

    async def permission_checker(
        request: Request,
        current_user: CurrentUser = Depends(guard),
        db: AsyncSession = Depends(get_db_with_user),
    ) -> CurrentUser:
        raw = request.path_params.get(param)
        try:
            target = UUID(str(raw)) if raw else None
        except ValueError:
            target = None
        if target is not None:
            await ensure_office_in_scope(db, current_user, required_permission, target, "Kantor")
        return current_user
    return permission_checker


def require_any_permission(
    *required: Permission,
) -> Callable[[CurrentUser], Coroutine[Any, Any, CurrentUser]]:
    """Lolos bila pengguna punya SALAH SATU izin yang disebut (mis. cari alamat: pengelola SK atau pengelola lokasi)."""
    async def permission_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if _is_legacy_admin(current_user) and Permission.DELETE_ANY not in required:
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


def daily_access(need: DailyNeed) -> Callable[..., Awaitable[DailyAccess]]:
    """Dependency untuk rute ber-`{daily_plan_id}`: kedudukan pada jadwal harian (docs/35 §3).
    Tidak terlihat → 404, terlihat tetapi tidak berwenang → 403."""
    async def guard(
        daily_plan_id: UUID,
        current_user: CurrentUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_with_user),
    ) -> DailyAccess:
        return await check_daily_access(db, daily_plan_id, current_user, need)
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


# ── Idempotency-Key opsional (F-03, docs/06 Idempotensi) ─────────────────────────
# Tanpa header: tidak ada yang disimpan atau diperiksa (perilaku lama, APK lama tetap jalan).
# Dengan header, kunci disimpan per (organisasi, pengguna, kunci):
#   * kunci dipakai permintaan lain yang sedang berjalan → 409 (kunci advisory transaksi);
#   * kunci sudah selesai dan hash permintaan sama → respons tersimpan (status dan badan asli);
#   * kunci sudah selesai dan hash berbeda → 422;
#   * kunci baru → aksi dijalankan; respons disimpan dalam transaksi yang sama (commit bersama aksi).
#     Bila aksi gagal dan transaksi di-rollback, kunci tidak tersimpan sehingga klien boleh mencoba lagi.
#
# Pemakaian di route (dependency paling akhir, setelah dependency izin):
#     idem: IdempotencyGuard = Depends(idempotency_guard)
#     tersimpan = idem.tersimpan()
#     if tersimpan is not None:
#         return tersimpan
#     hasil = await controller.handle_x(current_user, data)
#     return await idem.simpan(hasil, status.HTTP_201_CREATED)

IDEMPOTENCY_HEADER = "Idempotency-Key"
_POLA_KUNCI_IDEMPOTEN = re.compile(r"[A-Za-z0-9._:-]{8,128}")
_T = TypeVar("_T")


def hash_permintaan(method: str, path: str, body: bytes) -> str:
    """SHA-256 atas metode, path, dan badan. Badan JSON dinormalkan (kunci terurut, tanpa spasi)
    agar urutan kunci atau spasi tidak membuat hash berbeda untuk isi yang sama."""
    try:
        isi = json.dumps(json.loads(body), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    except ValueError:
        isi = body
    return hashlib.sha256(method.encode() + b"\n" + path.encode() + b"\n" + isi).hexdigest()


class IdempotencyGuard:
    """Status Idempotency-Key untuk satu permintaan. Tanpa header, semua metodenya no-op."""

    def __init__(
        self,
        db: AsyncSession | None = None,
        *,
        org: str = "",
        user: str = "",
        key: str | None = None,
        request_hash: str = "",
        tersimpan: repo.Respons | None = None,
    ) -> None:
        self._db = db
        self._org = org
        self._user = user
        self._key = key
        self._hash = request_hash
        self._tersimpan = tersimpan

    def tersimpan(self) -> JSONResponse | None:
        """Respons yang sudah tersimpan untuk kunci ini (replay), atau None bila aksi harus dijalankan."""
        if self._tersimpan is None:
            return None
        return JSONResponse(status_code=self._tersimpan.status_code, content=self._tersimpan.body)

    async def simpan(self, hasil: _T, status_code: int) -> _T:
        """Simpan respons aksi yang baru selesai (dalam transaksi permintaan). Tanpa kunci: no-op."""
        if self._key is None or self._db is None:
            return hasil
        body_json = json.dumps(jsonable_encoder(hasil), ensure_ascii=False, separators=(",", ":"))
        tersimpan = await repo.simpan(
            self._db,
            org=self._org,
            user=self._user,
            key=self._key,
            request_hash=self._hash,
            status_code=status_code,
            body_json=body_json,
        )
        if not tersimpan:
            raise AppError(
                "IDEMPOTENCY_SEDANG_DIPROSES",
                "Permintaan dengan kunci ini sedang diproses. Tunggu sebentar lalu coba lagi.",
                status=409,
            )
        return hasil


async def idempotency_guard(
    request: Request,
    db: AsyncSession = Depends(get_db_with_user),
    current_user: CurrentUser = Depends(get_current_user),
    idempotency_key: str | None = Header(
        None, alias=IDEMPOTENCY_HEADER, description="Kunci unik per aksi (UUID v4 disarankan)."
    ),
) -> IdempotencyGuard:
    if idempotency_key is None:
        return IdempotencyGuard()
    if _POLA_KUNCI_IDEMPOTEN.fullmatch(idempotency_key) is None:
        raise AppError(
            "IDEMPOTENCY_KUNCI_TIDAK_VALID",
            "Idempotency-Key harus 8 sampai 128 karakter: huruf, angka, titik, garis bawah, titik dua, atau strip.",
            status=422,
        )
    body = await request.body()
    request_hash = hash_permintaan(request.method, request.url.path, body)
    org, user = current_user.organization_id, current_user.user_id

    if not await repo.kunci_operasi(db, f"idempotency:{org}:{user}:{idempotency_key}"):
        raise AppError(
            "IDEMPOTENCY_SEDANG_DIPROSES",
            "Permintaan dengan kunci ini sedang diproses. Tunggu sebentar lalu coba lagi.",
            status=409,
        )
    tersimpan = await repo.ambil(db, org, user, idempotency_key)
    if tersimpan is not None and tersimpan.request_hash != request_hash:
        raise AppError(
            "IDEMPOTENCY_KUNCI_DIPAKAI",
            "Idempotency-Key ini sudah dipakai untuk permintaan lain.",
            status=422,
        )
    return IdempotencyGuard(
        db,
        org=org,
        user=user,
        key=idempotency_key,
        request_hash=request_hash,
        tersimpan=tersimpan,
    )
