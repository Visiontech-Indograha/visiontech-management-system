"""
Penjaga keterlibatan pekerjaan (V-07). Kewenangan mengikuti SK, bukan jabatan (CLAUDE.md aturan 1):
ketua & anggota dibaca dari SK yang berlaku setiap permintaan (`is_plan_leader`/`is_plan_member`).

SK organisasi lain atau yang tidak terlihat oleh pengguna → 404 (keberadaannya tidak dibocorkan);
terlihat tetapi tidak berwenang → 403.

Dipindah dari api/deps.py (R-28 M5): service tidak mengimpor `app.api` (docs/12 §1).
Dependency FastAPI-nya (`plan_access`, `plan_day_access`, …) tetap di api/deps.py.
"""
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, ForbiddenError, NotFoundError
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.crud.crud_file_access import CRUDFileAccess
from app.crud.crud_org_ref import CRUDOrgRef
from app.crud.crud_plan_access import CRUDPlanAccess


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
    - swafoto absensi: karyawan pemilik & siapa pun yang boleh melihat absensi itu (R-33: PM bawahannya,
      Finance & OPS semua);
    - bukti laporan/insiden/laporan akhir: siapa pun yang melihat SK-nya (V-07);
    - selain itu (belum dilampirkan, QR, wajah): hanya pengunggah."""
    row = await CRUDFileAccess(db).links(file_id, user.organization_id, user.user_id,
                                         Permission.VIEW_ALL_ATTENDANCE.value in user.permissions)
    if row is None:
        raise NotFoundError("Berkas")
    if row.is_uploader:
        return row
    if row.personal_document:
        if row.own_document or Permission.MANAGE_EMPLOYEE_DOCUMENTS.value in user.permissions:
            return row
        raise NotFoundError("Berkas")
    if row.selfie:
        if row.own_selfie or row.selfie_viewable:
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
