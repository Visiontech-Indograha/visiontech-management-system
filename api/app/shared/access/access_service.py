"""
Penjaga keterlibatan pekerjaan daily-first (docs/35 §3, keputusan pemilik 2026-10-20).

Kedudukan pada jadwal harian dibaca dari relasi setiap permintaan:
- MANAGE: PM/OM divisi jadwal (division.pm_id / om_id) atau SUPER_ADMIN;
- LEADER: ketua tim jadwal (team.leader_employee_id);
- TEAM:   ketua atau anggota aktif tim jadwal;
- VIEW:   salah satu di atas (detail rencana, item, BOM, revisi, survei: HR TIDAK termasuk);
- LOGISTICS: sama dengan VIEW, ditambah ADMIN_HR_GA (hanya untuk logistik aset & lembur pada jadwal).
Pekerja lapangan hanya melihat jadwal yang sudah disetujui.

Tidak terlihat → 404 (keberadaannya tidak dibocorkan); terlihat tetapi tidak berwenang → 403.
Service tidak mengimpor `app.api` (docs/12 §1); dependency FastAPI-nya (`daily_access`) ada di api/deps.py.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, ForbiddenError, NotFoundError
from app.core.permissions import Permission, SystemRole
from app.core.security import CurrentUser
from app.shared.access.daily_access_repository import DailyAccessRepository
from app.shared.access.file_access_repository import FileAccessRepository
from app.shared.access.org_ref_repository import CRUDOrgRef
from app.shared.access.scope_rules import asset_file_visible, employee_directory_visible

# Jadwal yang sudah boleh dilihat & dikerjakan tim lapangan.
RELEASED = ("APPROVED", "ONGOING", "COMPLETED")


class DailyNeed(StrEnum):
    VIEW = "VIEW"
    LOGISTICS = "LOGISTICS"
    TEAM = "TEAM"
    LEADER = "LEADER"
    MANAGE = "MANAGE"


_REFUSAL = {
    DailyNeed.MANAGE: "Hanya PM/OM divisi jadwal ini yang dapat melakukan tindakan ini.",
    DailyNeed.LEADER: "Hanya ketua tim jadwal ini yang dapat melakukan tindakan ini.",
    DailyNeed.TEAM: "Hanya ketua atau anggota tim jadwal ini yang dapat melakukan tindakan ini.",
}


@dataclass(frozen=True)
class DailyAccess:
    """Kedudukan pengguna pada satu jadwal harian."""

    plan: Any  # baris standing (status, work_date, division_id, team_id, pm_id, om_id, leader_employee_id)
    user: CurrentUser
    manages: bool
    is_leader: bool
    is_member: bool


STAGE_MISMATCH = "Status jadwal harian belum sesuai untuk tindakan ini. Muat ulang halaman."


def require_daily_status(access: DailyAccess, *allowed: str) -> None:
    if access.plan.status not in allowed:
        raise AppError("INVALID_STATE", STAGE_MISMATCH, status=409)


def is_admin(user: CurrentUser) -> bool:
    return user.has_role(SystemRole.SUPER_ADMIN)


async def check_daily_access(
    db: AsyncSession, daily_plan_id: UUID | str, user: CurrentUser, need: DailyNeed
) -> DailyAccess:
    row = await DailyAccessRepository(db).standing(daily_plan_id, user.employee_id)
    if row is None:
        raise NotFoundError("Jadwal harian")
    manages = is_admin(user) or bool(row.manages)
    is_leader, is_member = bool(row.is_leader), bool(row.is_member) or bool(row.is_leader)
    # HR/GA hanya melihat jadwal untuk logistik (aset & lembur), bukan detail rencana kerja.
    office_logistics = need == DailyNeed.LOGISTICS and user.has_role(SystemRole.ADMIN_HR_GA)
    visible = manages or office_logistics or ((is_leader or is_member) and row.status in RELEASED)
    if not visible:
        raise NotFoundError("Jadwal harian")
    allowed = {
        DailyNeed.VIEW: True,
        DailyNeed.LOGISTICS: True,
        DailyNeed.TEAM: is_member,
        DailyNeed.LEADER: is_leader,
        DailyNeed.MANAGE: manages,
    }[need]
    if not allowed:
        raise ForbiddenError(_REFUSAL[need])
    return DailyAccess(row, user, manages, is_leader, is_member)


async def check_division_manager(db: AsyncSession, division_id: UUID | str, user: CurrentUser) -> None:
    """Membuat jadwal untuk divisi: PM/OM divisi itu atau SUPER_ADMIN."""
    row = await DailyAccessRepository(db).division_managers(division_id)
    if row is None:
        raise AppError("VALIDATION_ERROR", "Divisi tidak ditemukan atau sudah nonaktif.", status=422)
    if not is_admin(user) and user.employee_id not in (str(row.pm_id), str(row.om_id)):
        raise ForbiddenError("Hanya PM/OM divisi ini yang dapat mengelola jadwalnya.")


async def check_file_access(db: AsyncSession, file_id: UUID, user: CurrentUser) -> Any:
    """Siapa boleh membuka berkas (dok 08). Tidak boleh → 404, bukan 403. Tautan berkas dibaca dari tabel
    pemakainya (kolom *_path = file_object.storage_key):
    - pengunggahnya sendiri;
    - contoh foto template (petunjuk kerja): semua pengguna yang login;
    - foto/berkas aset (alat, kendaraan, inspeksi, serah terima): cakupan aset (`asset_file_visible`);
    - foto profil: pemiliknya & karyawan yang terlihat di direktori pengguna (`employee_directory_visible`);
    - dokumen karyawan: pemilik & pengelola dokumen (manage:employee_documents);
    - swafoto absensi: pemilik & peninjau absensi (review/view all attendance);
    - lampiran jadwal harian / bukti item: siapa pun yang boleh melihat jadwal itu."""
    row = await FileAccessRepository(db).links(file_id, user.employee_id)
    if row is None:
        raise NotFoundError("Berkas")
    perms = set(user.permissions)
    if is_admin(user) or str(row.uploaded_by) == user.user_id or row.public_in_org:
        return row
    if row.profile_photo and (row.own_profile or await employee_directory_visible(db, user, row.profile_owner)):
        return row
    if row.asset_file and await asset_file_visible(db, row.storage_key, user):
        return row
    if row.personal_document and (row.own_document or Permission.MANAGE_EMPLOYEE_DOCUMENTS.value in perms):
        return row
    # Swafoto: pemilik; pemegang VIEW_ALL (OM, Finance, OPS); atau PM yang memimpin divisi karyawan itu.
    if row.selfie and (row.own_selfie or Permission.VIEW_ALL_ATTENDANCE.value in perms
                       or (Permission.REVIEW_ATTENDANCE.value in perms and row.selfie_pm)):
        return row
    for daily_plan_id in row.daily_plan_ids or []:
        try:
            await check_daily_access(db, daily_plan_id, user, DailyNeed.VIEW)
            return row
        except (NotFoundError, ForbiddenError):
            continue
    raise NotFoundError("Berkas")


_REF_LABELS = (
    ("work_plans", "Jadwal harian"),
    ("sites", "Lokasi"),
    ("assets", "Aset"),
    ("files", "Berkas"),
    ("employees", "Karyawan"),
    ("units", "Divisi"),
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
    """V-08: setiap id di badan permintaan ada & milik organisasi pengguna; bila tidak → 404.
    Dipanggil SEBELUM menulis apa pun."""
    refs = {
        kind: sorted({str(i) for i in ids if i is not None})
        for kind, ids in (
            ("work_plans", work_plans),
            ("sites", sites),
            ("assets", assets),
            ("files", files),
            ("employees", employees),
            ("units", units),
        )
    }
    if not any(refs.values()):
        return
    owned = await CRUDOrgRef(db).owned_counts(org_id, **refs)
    for kind, label in _REF_LABELS:
        if getattr(owned, kind) != len(refs[kind]):
            raise NotFoundError(label)
