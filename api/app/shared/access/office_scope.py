"""
Cakupan kantor untuk data absensi (keputusan pemilik 2026-11-05; peran ganda: ADR 0002).

Pemegang `view:all_attendance` tidak otomatis melihat semua kantor:
- SUPER_ADMIN dan OPERATIONAL_MANAGER (peran sistem, atau penjabat OM sebuah divisi `division.om_id`)
  melihat SEMUA kantor;
- peran lain (ADMIN_HR_GA, FINANCE) hanya kantor tempat karyawannya terdaftar (`employee.office_id`).

Cakupan adalah gabungan (union) semua jabatan orang itu: HR kantor A yang juga OM divisi melihat semua kantor.
Dengan `ROLE_ASSIGNMENT_ENABLED` (ADR 0002) jabatan tambahan juga datang dari tabel `user_role_assignment`:
- penugasan OPERATIONAL_MANAGER aktif = semua kantor (OM membawa izin absensi, cakupannya semua kantor);
- penugasan ADMIN_HR_GA / FINANCE = kantor yang ditugaskan saja. Cakupan dihitung per peran pembawa izin:
  izin yang hanya dibawa HR/Finance tidak ikut melebar walau orangnya juga OM (izin absensi dibawa OM,
  sehingga di sini OM menang; izin khusus HR dibatasi di endpoint HR, bukan di cakupan absensi).
Flag mati: ekspresi SQL persis seperti sebelum peran ganda. Dihitung di SQL (satu sumber untuk daftar,
rekap, ekspor, uang makan, dan akses swafoto).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import NotFoundError
from app.core.permissions import Permission, permissions_for_roles
from app.core.repository import BaseRepository
from app.core.security import CurrentUser


def attendance_office_scope(viewer_emp: str, emp_office: str) -> str:
    """Ekspresi boolean SQL: peninjau (`viewer_emp` = ekspresi employee_id) boleh melihat absensi karyawan yang
    kantornya `emp_office` (ekspresi office_id). Kedua argumen adalah ekspresi SQL internal, bukan input pengguna."""
    if not settings.ROLE_ASSIGNMENT_ENABLED:
        return f"""(
        EXISTS (SELECT 1 FROM users os WHERE os.employee_id = {viewer_emp} AND os.delete_at IS NULL
                AND os.system_role IN ('SUPER_ADMIN', 'OPERATIONAL_MANAGER'))
        OR EXISTS (SELECT 1 FROM division od WHERE od.om_id = {viewer_emp} AND od.delete_at IS NULL)
        OR {emp_office} = (SELECT ov.office_id FROM employee ov WHERE ov.employee_id = {viewer_emp})
    )"""
    return f"""(
        EXISTS (SELECT 1 FROM users os WHERE os.employee_id = {viewer_emp} AND os.delete_at IS NULL
                AND (os.system_role IN ('SUPER_ADMIN', 'OPERATIONAL_MANAGER')
                     OR EXISTS (SELECT 1 FROM user_role_assignment oa
                                WHERE oa.user_id = os.user_id AND oa.delete_at IS NULL
                                  AND oa.role = 'OPERATIONAL_MANAGER')))
        OR EXISTS (SELECT 1 FROM division od WHERE od.om_id = {viewer_emp} AND od.delete_at IS NULL)
        OR {emp_office} = (SELECT ov.office_id FROM employee ov WHERE ov.employee_id = {viewer_emp})
        OR EXISTS (SELECT 1 FROM users hu
                   JOIN user_role_assignment ha ON ha.user_id = hu.user_id AND ha.delete_at IS NULL
                        AND ha.role IN ('ADMIN_HR_GA', 'FINANCE') AND ha.office_id = {emp_office}
                   JOIN office ho ON ho.office_id = ha.office_id AND ho.delete_at IS NULL
                   WHERE hu.employee_id = {viewer_emp} AND hu.delete_at IS NULL)
    )"""


# ── Izin khusus HR/Finance di luar absensi (ADR 0002 bagian 5; docs/audit-izin-hr-finance-per-kantor.md) ──────
# Peran yang cakupan datanya dibatasi ke kantor tugasnya. Peran lain (SA, OM, ADMIN lama, ...) tidak dibatasi.
OFFICE_BOUND_ROLES: frozenset[str] = frozenset({"ADMIN_HR_GA", "FINANCE"})
# Fase 2 (ADR 0002): PM dan HSE terikat kantor penugasan HANYA sebagai peran tambahan. Sebagai peran utama
# perilakunya tetap lama (PM per divisi lewat data, HSE tanpa batas kantor).
EXTRA_ONLY_BOUND_ROLES: frozenset[str] = frozenset({"PROJECT_MANAGER", "HSE"})


def carrier_roles(user: CurrentUser, perm: Permission) -> frozenset[str]:
    """Peran pemegang yang MEMBAWA izin `perm` (peran utama + tambahan). Per peran pembawa izin, bukan per orang:
    OM yang juga HR tetap tidak melebar pada izin yang hanya dibawa HR."""
    return frozenset(r for r in user.roles if perm.value in permissions_for_roles([r]))


async def office_restriction(db: AsyncSession, user: CurrentUser, perm: Permission,
                             wide_roles: tuple[str, ...] = (),
                             division_roles: tuple[str, ...] = ()) -> frozenset[str] | None:
    """Kantor yang boleh dijangkau pengguna lewat izin `perm`.

    None = tanpa batas kantor: flag `ROLE_ASSIGNMENT_ENABLED` mati (perilaku lama PERSIS), pengguna tidak memegang
    izin itu, atau ada peran pembawa izin di luar HR/Finance (SA, OM, ADMIN lama).
    `division_roles`: peran yang ikut membawa izin tetapi cakupannya diatur sendiri (mis. PM per divisi); tidak
    dihitung sebagai pembawa pelebar, jadi HR yang juga PM tetap dibatasi kantor pada alur HR.
    Selain itu: kantor sendiri (`employee.office_id`) + kantor penugasan aktif untuk peran HR/Finance pembawa izin.
    """
    if not settings.ROLE_ASSIGNMENT_ENABLED or perm.value not in user.permissions or user.has_role(*wide_roles):
        return None
    extra_bound = EXTRA_ONLY_BOUND_ROLES - {user.role}  # peran utama PM/HSE tidak dibatasi
    # PM tambahan tidak ikut "per divisi": ia tak punya jalur data (pm_id), jadi dibatasi kantor penugasan.
    carriers = carrier_roles(user, perm) - (frozenset(division_roles) - extra_bound)
    if not carriers or not carriers <= (OFFICE_BOUND_ROLES | extra_bound):
        return None
    own_office = "TRUE" if carriers & OFFICE_BOUND_ROLES else "FALSE"  # PM/HSE tambahan: kantor penugasan saja
    rows = await BaseRepository(db).fetchall(
        f"""
        SELECT e.office_id::text AS office_id FROM users u
        JOIN employee e ON e.employee_id = u.employee_id AND e.delete_at IS NULL
        WHERE u.user_id = CAST(:uid AS uuid) AND e.office_id IS NOT NULL AND {own_office}
        UNION
        SELECT a.office_id::text FROM user_role_assignment a
        JOIN office o ON o.office_id = a.office_id AND o.delete_at IS NULL
        WHERE a.user_id = CAST(:uid AS uuid) AND a.delete_at IS NULL AND a.role::text = ANY(:roles)
        """,
        {"uid": user.user_id, "roles": sorted(carriers)},
    )
    return frozenset(r.office_id for r in rows)


def offices_param(restriction: frozenset[str] | None) -> list[str]:
    """Nilai untuk parameter SQL `CAST(:offices AS uuid[])` (kosong bila tanpa batas)."""
    return sorted(restriction) if restriction else []


async def ensure_office_in_scope(db: AsyncSession, user: CurrentUser, perm: Permission,
                                 office_id: UUID | str | None, resource: str = "Data") -> None:
    """404 bila kantor `office_id` di luar jangkauan izin `perm` (keberadaan data tidak dibocorkan)."""
    restriction = await office_restriction(db, user, perm)
    if restriction is not None and (office_id is None or str(office_id) not in restriction):
        raise NotFoundError(resource)


async def ensure_employee_in_scope(db: AsyncSession, user: CurrentUser, perm: Permission,
                                   employee_id: UUID | str | None, resource: str = "Karyawan") -> None:
    """404 bila karyawan target berkantor di luar jangkauan izin `perm`. Karyawan tak dikenal dibiarkan lolos
    agar galat 404 asli layanan tetap muncul."""
    if employee_id is None:
        return
    restriction = await office_restriction(db, user, perm)
    if restriction is None:
        return
    row = await BaseRepository(db).fetchone(
        "SELECT office_id::text AS office_id FROM employee WHERE employee_id = CAST(:id AS uuid)",
        {"id": str(employee_id)})
    if row is not None and (row.office_id is None or row.office_id not in restriction):
        raise NotFoundError(resource)
