import logging
from collections.abc import AsyncIterator, Awaitable, Callable, Coroutine, Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.alerts import send_security_alert
from app.core.database import AsyncSessionLocal, set_request_context, unit_of_work
from app.core.errors import AppError, ForbiddenError, NotFoundError
from app.core.permissions import NO_GLOBAL_ROLE, Permission, permissions_for_roles
from app.core.security import verify_jwt_token
from app.crud.crud_file_access import CRUDFileAccess
from app.crud.crud_org_ref import CRUDOrgRef
from app.crud.crud_plan_access import CRUDPlanAccess
from app.crud.crud_user import CRUDUser

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)  # token hilang → 401 UNAUTHENTICATED kita sendiri

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
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db, scope=DB_SCOPE),
) -> CurrentUser:
    """
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
    async def permission_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if required_permission.value not in current_user.permissions:
            raise AppError("FORBIDDEN", "Anda tidak memiliki akses untuk tindakan ini.", status=403)
        return current_user
    return permission_checker


async def get_db_with_user(
    db: AsyncSession = Depends(get_db, scope=DB_SCOPE),
    current_user: CurrentUser = Depends(get_current_user),
) -> AsyncSession:
    # Konteks RLS & audit untuk transaksi permintaan ini (app/core/database.py).
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


# ── Penjaga akses (dipindah dari api/guards.py, R-28 M2) ─────────────────────
# Penjaga keterlibatan pekerjaan (V-07). Kewenangan mengikuti SK, bukan jabatan (CLAUDE.md aturan 1):
# ketua & anggota dibaca dari SK yang berlaku setiap permintaan (`is_plan_leader`/`is_plan_member`).
#
# SK organisasi lain atau yang tidak terlihat oleh pengguna → 404 (keberadaannya tidak dibocorkan);
# terlihat tetapi tidak berwenang → 403.


class PlanNeed(StrEnum):
    PM_UNIT = "PM_UNIT"                    # PM unit SK, OPS, ADMIN
    LEADER = "LEADER"                      # ketua menurut SK yang berlaku
    MEMBER = "MEMBER"                      # anggota aktif (termasuk ketua)
    LEADER_OR_MEMBER = "LEADER_OR_MEMBER"
    VIEW = "VIEW"


_REFUSAL = {
    PlanNeed.PM_UNIT: "Hanya PM unit pekerjaan ini yang dapat melakukan tindakan ini.",
    PlanNeed.LEADER: "Hanya ketua tim menurut SK yang berlaku yang dapat melakukan tindakan ini.",
    PlanNeed.MEMBER: "Hanya anggota tim pekerjaan ini yang dapat melakukan tindakan ini.",
    PlanNeed.LEADER_OR_MEMBER: "Hanya ketua atau anggota tim pekerjaan ini yang dapat melakukan tindakan ini.",
}


@dataclass(frozen=True)
class PlanAccess:
    plan: Any               # baris SK (kolom WorkPlanResponse + kedudukan)
    user: CurrentUser
    manages: bool
    is_leader: bool
    is_member: bool


STAGE_MISMATCH = "Tahap work plan belum sesuai untuk tindakan ini."  # domain.js requireStatus


def require_plan_status(access: PlanAccess, *allowed: str) -> None:
    """`domain.js` requireStatus — tindakan hanya pada tahap SK tertentu (V-11). → 409 INVALID_STATE."""
    if access.plan.status not in allowed:
        raise AppError("INVALID_STATE", STAGE_MISMATCH, status=409)


def satisfies(need: PlanNeed, *, manages: bool, is_leader: bool, is_member: bool) -> bool:
    """Apakah kedudukan pengguna (yang sudah terlihat) memenuhi kebutuhan tindakan."""
    return {
        PlanNeed.VIEW: True,
        PlanNeed.PM_UNIT: manages,
        PlanNeed.LEADER: is_leader,
        PlanNeed.MEMBER: is_member,
        PlanNeed.LEADER_OR_MEMBER: is_leader or is_member,
    }[need]


async def check_plan_access(
    db: AsyncSession, plan_id: UUID | str, user: CurrentUser, need: PlanNeed, archived: bool | None = False
) -> PlanAccess:
    row = await CRUDPlanAccess(db).standing(plan_id, user.organization_id, user.user_id, archived)
    if row is None:
        raise NotFoundError("SK")
    if not satisfies(need, manages=row.manages, is_leader=row.is_leader, is_member=row.is_member):
        raise ForbiddenError(_REFUSAL[need])
    return PlanAccess(plan=row, user=user, manages=row.manages, is_leader=row.is_leader, is_member=row.is_member)


async def check_unit_manager(db: AsyncSession, unit_id: UUID | str, user: CurrentUser) -> None:
    """Membuat SK di sebuah unit: PM unit itu, OPS, atau ADMIN. Unit organisasi lain → 404."""
    row = await CRUDPlanAccess(db).unit_standing(unit_id, user.organization_id, user.user_id)
    if row is None:
        raise NotFoundError("Unit bisnis")
    if not row.manages:
        raise ForbiddenError("Hanya PM unit ini yang dapat membuat SK untuk unit tersebut.")


async def check_file_access(db: AsyncSession, file_id: UUID, user: CurrentUser) -> Any:
    """V-17 — siapa boleh membuka berkas (dok 08, dok 13 §7). Tidak boleh → 404, bukan 403.
    - pengunggahnya sendiri;
    - dokumen pribadi: karyawan pemilik & pemegang `manage:employee_documents` (HR);
    - swafoto absensi: karyawan pemilik & peninjau absensi (`review:attendance`);
    - bukti laporan/insiden/laporan akhir: siapa pun yang melihat SK-nya (V-07);
    - selain itu (belum dilampirkan, QR, wajah): hanya pengunggah."""
    row = await CRUDFileAccess(db).links(file_id, user.organization_id, user.user_id)
    if row is None:
        raise NotFoundError("Berkas")
    if row.is_uploader:
        return row
    if row.personal_document:
        if row.own_document or Permission.MANAGE_EMPLOYEE_DOCUMENTS.value in user.permissions:
            return row
        raise NotFoundError("Berkas")
    if row.selfie:
        if row.own_selfie or Permission.REVIEW_ATTENDANCE.value in user.permissions:
            return row
        raise NotFoundError("Berkas")
    plans = CRUDPlanAccess(db)
    for plan_id in row.plan_ids:
        if await plans.standing(plan_id, user.organization_id, user.user_id) is not None:
            return row
    raise NotFoundError("Berkas")


_REF_LABELS = (
    ("work_plans", "SK"), ("sites", "Lokasi"), ("assets", "Aset"),
    ("files", "Berkas"), ("employees", "Karyawan"), ("units", "Unit bisnis"),
)


async def ensure_same_org(
    db: AsyncSession,
    org_id: str,
    *,
    work_plans: Iterable[UUID | str | None] = (),
    sites: Iterable[UUID | str | None] = (),
    assets: Iterable[UUID | str | None] = (),
    files: Iterable[UUID | str | None] = (),
    employees: Iterable[UUID | str | None] = (),
    units: Iterable[UUID | str | None] = (),
) -> None:
    """V-08: setiap id di badan permintaan milik organisasi pengguna; bila tidak → 404 (bukan 403,
    agar keberadaan data organisasi lain tidak bocor). Dipanggil SEBELUM menulis apa pun."""
    refs = {
        kind: sorted({str(i) for i in ids if i is not None})
        for kind, ids in (("work_plans", work_plans), ("sites", sites), ("assets", assets),
                          ("files", files), ("employees", employees), ("units", units))
    }
    if not any(refs.values()):
        return
    owned = await CRUDOrgRef(db).owned_counts(org_id, **refs)
    for kind, label in _REF_LABELS:
        if getattr(owned, kind) != len(refs[kind]):
            raise NotFoundError(label)


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
