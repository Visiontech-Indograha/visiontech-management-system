"""
Peran global dan peta izin (dok 03 §1, dok 08; OPS mengikuti prototipe — dok 10 Bagian C).

`RoleCode` adalah satu-satunya daftar peran di Python dan harus identik dengan enum
`vms.role_code` (dijaga `tests/test_permissions.py`). LEADER/MEMBER tidak memberi izin global:
kewenangan ketua/anggota berasal dari SK yang berlaku (`is_plan_leader`/`is_plan_member`).
"""
from collections.abc import Iterable
from enum import StrEnum


class RoleCode(StrEnum):
    """
    Kode peran pengguna di seluruh sistem (global roles).
    Mendukung Master DDL V2 (system_role_enum) dan kompatibilitas mundur.
    """
    # VMS Master V2 Roles
    SUPER_ADMIN = "SUPER_ADMIN"
    OPERATIONAL_MANAGER = "OPERATIONAL_MANAGER"
    PROJECT_MANAGER = "PROJECT_MANAGER"
    TEAM_LEADER = "TEAM_LEADER"
    ADMIN_HR_GA = "ADMIN_HR_GA"
    EMPLOYEE = "EMPLOYEE"

    # Legacy Aliases
    ADMIN = "ADMIN"
    OPS = "OPS"
    PM = "PM"
    LEADER = "LEADER"
    HR = "HR"
    MEMBER = "MEMBER"
    FINANCE = "FINANCE"
    ASSET = "ASSET"


# Label di token untuk akun tanpa baris user_role — karyawan biasa.
NO_GLOBAL_ROLE = "field"


class Permission(StrEnum):
    """
    Daftar izin (permissions) yang digunakan dalam aplikasi.
    """
    # Pengguna & direktori karyawan
    MANAGE_USERS = "manage:users"
    VIEW_USERS = "view:users"

    # Dokumen pribadi: milik sendiri (dasar) vs milik siapa pun (HR)
    UPLOAD_DOCUMENTS = "upload:documents"
    VIEW_DOCUMENTS = "view:documents"
    MANAGE_EMPLOYEE_DOCUMENTS = "manage:employee_documents"
    VERIFY_DOCUMENTS = "verify:documents"

    # SK & pekerjaan
    CREATE_PLAN = "create:plan"
    PUBLISH_PLAN = "publish:plan"

    # Absensi & lembur — cakupan per absen dicek di service/CRUD (R-33, menggantikan R-10)
    VIEW_ALL_ATTENDANCE = "view:all_attendance"  # Finance & OPS melihat semua absensi
    REVIEW_ATTENDANCE = "review:attendance"  # PM → bawahan lapangan, Finance → kantor non-Finance, OPS → Finance
    EXPORT_ATTENDANCE = "export:attendance"  # ekspor CSV — Finance
    REVIEW_OVERTIME = "review:overtime"

    # Lokasi kerja: PM → lokasi proyek unitnya, Finance → lokasi kantor (R-33)
    MANAGE_SITES = "manage:sites"

    # Aset
    MANAGE_ASSETS = "manage:assets"

    # Pemantauan
    VIEW_TIMELINE = "view:timeline"
    VIEW_AUDIT = "view:audit"

    # Tugas terjadwal (cron) yang memicu peringatan — hanya ADMIN
    RUN_SYSTEM_JOBS = "run:system_jobs"


P = Permission

# Setiap karyawan yang login: direktori, dokumen pribadinya sendiri.
BASE_PERMISSIONS: frozenset[Permission] = frozenset({P.VIEW_USERS, P.VIEW_DOCUMENTS, P.UPLOAD_DOCUMENTS})

# Admin memiliki kuasa penuh atas seluruh perizinan sistem.
_ROLE_EXTRA: dict[RoleCode, frozenset[Permission]] = {
    RoleCode.SUPER_ADMIN: frozenset(Permission),
    RoleCode.ADMIN: frozenset(Permission),
    RoleCode.OPERATIONAL_MANAGER: frozenset({
        P.CREATE_PLAN, P.PUBLISH_PLAN, P.REVIEW_OVERTIME, P.VIEW_ALL_ATTENDANCE,
        P.REVIEW_ATTENDANCE, P.VIEW_TIMELINE, P.VIEW_AUDIT
    }),
    RoleCode.OPS: frozenset({
        P.CREATE_PLAN, P.PUBLISH_PLAN, P.REVIEW_OVERTIME, P.VIEW_ALL_ATTENDANCE,
        P.REVIEW_ATTENDANCE, P.VIEW_TIMELINE, P.VIEW_AUDIT
    }),
    RoleCode.PROJECT_MANAGER: frozenset({
        P.CREATE_PLAN, P.PUBLISH_PLAN, P.VIEW_TIMELINE, P.REVIEW_ATTENDANCE, P.MANAGE_SITES
    }),
    RoleCode.PM: frozenset({
        P.CREATE_PLAN, P.PUBLISH_PLAN, P.VIEW_TIMELINE, P.REVIEW_ATTENDANCE, P.MANAGE_SITES
    }),
    RoleCode.ADMIN_HR_GA: frozenset({
        P.MANAGE_USERS, P.VERIFY_DOCUMENTS, P.MANAGE_EMPLOYEE_DOCUMENTS, P.MANAGE_ASSETS
    }),
    RoleCode.HR: frozenset({
        P.MANAGE_USERS, P.VERIFY_DOCUMENTS, P.MANAGE_EMPLOYEE_DOCUMENTS
    }),
    RoleCode.FINANCE: frozenset({
        P.VIEW_ALL_ATTENDANCE, P.REVIEW_ATTENDANCE, P.EXPORT_ATTENDANCE,
        P.REVIEW_OVERTIME, P.MANAGE_SITES
    }),
    RoleCode.ASSET: frozenset({P.MANAGE_ASSETS}),
    RoleCode.TEAM_LEADER: frozenset(),
    RoleCode.LEADER: frozenset(),
    RoleCode.EMPLOYEE: frozenset(),
    RoleCode.MEMBER: frozenset(),
}


def permissions_for_roles(roles: Iterable[str]) -> list[str]:
    """Gabungan izin dari beberapa peran global. Peran tak dikenal diabaikan."""
    granted: set[Permission] = set()
    for role in roles:
        if role == NO_GLOBAL_ROLE:
            granted |= BASE_PERMISSIONS
        elif role in RoleCode.__members__:
            granted |= BASE_PERMISSIONS | _ROLE_EXTRA[RoleCode(role)]
    return sorted(p.value for p in granted)


def get_role_permissions(role: str) -> list[str]:
    return permissions_for_roles([role])
