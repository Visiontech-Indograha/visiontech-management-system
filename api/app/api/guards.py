"""
Penjaga keterlibatan pekerjaan (V-07). Kewenangan mengikuti SK, bukan jabatan (CLAUDE.md aturan 1):
ketua & anggota dibaca dari SK yang berlaku setiap permintaan (`is_plan_leader`/`is_plan_member`).

SK organisasi lain atau yang tidak terlihat oleh pengguna → 404 (keberadaannya tidak dibocorkan);
terlihat tetapi tidak berwenang → 403.
"""
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_db_with_user
from app.core.errors import AppError, ForbiddenError, NotFoundError
from app.core.permissions import Permission
from app.repositories.file_access_repo import FileAccessRepo
from app.repositories.org_ref_repo import OrgRefRepo
from app.repositories.plan_access_repo import PlanAccessRepo


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
    row = await PlanAccessRepo(db).standing(plan_id, user.organization_id, user.user_id, archived)
    if row is None:
        raise NotFoundError("SK")
    if not satisfies(need, manages=row.manages, is_leader=row.is_leader, is_member=row.is_member):
        raise ForbiddenError(_REFUSAL[need])
    return PlanAccess(plan=row, user=user, manages=row.manages, is_leader=row.is_leader, is_member=row.is_member)


async def check_unit_manager(db: AsyncSession, unit_id: UUID | str, user: CurrentUser) -> None:
    """Membuat SK di sebuah unit: PM unit itu, OPS, atau ADMIN. Unit organisasi lain → 404."""
    row = await PlanAccessRepo(db).unit_standing(unit_id, user.organization_id, user.user_id)
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
    row = await FileAccessRepo(db).links(file_id, user.organization_id, user.user_id)
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
    plans = PlanAccessRepo(db)
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
    owned = await OrgRefRepo(db).owned_counts(org_id, **refs)
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
        plan_id = await PlanAccessRepo(db).plan_of_allocation(alloc_id)
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
        plan_id = await PlanAccessRepo(db).plan_of_incident(inc_id, current_user.organization_id)
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
        if str(await PlanAccessRepo(db).plan_of_day(day_id)) != str(plan_id):
            raise NotFoundError("Hari kerja")
        return access
    return guard


