"""
Penjaga keterlibatan pekerjaan (V-07). Kewenangan mengikuti SK, bukan jabatan (CLAUDE.md aturan 1):
ketua & anggota dibaca dari SK yang berlaku setiap permintaan (`is_plan_leader`/`is_plan_member`).

SK organisasi lain atau yang tidak terlihat oleh pengguna → 404 (keberadaannya tidak dibocorkan);
terlihat tetapi tidak berwenang → 403.
"""
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_db_with_user
from app.core.errors import ForbiddenError, NotFoundError
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
    db: AsyncSession, plan_id: UUID | str, user: CurrentUser, need: PlanNeed
) -> PlanAccess:
    row = await PlanAccessRepo(db).standing(plan_id, user.organization_id, user.user_id)
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


def plan_access(need: PlanNeed) -> Callable[..., Awaitable[PlanAccess]]:
    """Dependency untuk rute ber-`{plan_id}`."""
    async def guard(
        plan_id: UUID,
        current_user: CurrentUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_with_user),
    ) -> PlanAccess:
        return await check_plan_access(db, plan_id, current_user, need)
    return guard


def day_plan_access(need: PlanNeed) -> Callable[..., Awaitable[PlanAccess]]:
    """Dependency untuk rute ber-`{day_id}` (sampai V-16 memindahkannya ke `/work-plans/{id}/days/{day_id}`)."""
    async def guard(
        day_id: UUID,
        current_user: CurrentUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_with_user),
    ) -> PlanAccess:
        plan_id = await PlanAccessRepo(db).plan_of_day(day_id)
        if plan_id is None:
            raise NotFoundError("Hari kerja")
        return await check_plan_access(db, plan_id, current_user, need)
    return guard
