"""
Peran global dan peta izin (dok 03 §1, dok 08; OPS mengikuti prototipe — dok 10 Bagian C).

`RoleCode` adalah satu-satunya daftar peran di Python dan harus identik dengan enum
`vms.role_code` (dijaga `tests/test_permissions.py`). LEADER/MEMBER tidak memberi izin global:
kewenangan ketua/anggota berasal dari SK yang berlaku (`is_plan_leader`/`is_plan_member`).
"""
from collections.abc import Iterable
from enum import StrEnum


class RoleCode(StrEnum):
    """Kode peran pengguna di seluruh organisasi (enum vms.role_code)."""
    ADMIN = "ADMIN"
    OPS = "OPS"
    PM = "PM"
    LEADER = "LEADER"
    HR = "HR"
    MEMBER = "MEMBER"
    FINANCE = "FINANCE"
    ASSET = "ASSET"


class SystemRole(StrEnum):
    """Kode peran pengguna sistem Master Schema V2 (system_role_enum)."""
    SUPER_ADMIN = "SUPER_ADMIN"
    OPERATIONAL_MANAGER = "OPERATIONAL_MANAGER"
    PROJECT_MANAGER = "PROJECT_MANAGER"
    TEAM_LEADER = "TEAM_LEADER"
    ADMIN_HR_GA = "ADMIN_HR_GA"
    EMPLOYEE = "EMPLOYEE"
    FINANCE = "FINANCE"


# Label di token untuk akun tanpa baris user_role — karyawan biasa.
NO_GLOBAL_ROLE = "field"


class Permission(StrEnum):
    """
    Daftar izin (permissions) yang digunakan dalam aplikasi.
    """
    # Hapus permanen apa pun — hanya SUPER_ADMIN (docs/41 §3a)
    DELETE_ANY = "delete:any"

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

    # Master kantor (office) & divisi operasional (division) — Milestone 2 (docs/36)
    MANAGE_SITES = "manage:sites"
    MANAGE_DIVISIONS = "manage:divisions"

    # Aset
    MANAGE_ASSETS = "manage:assets"

    # Tim operasional (Master V2)
    MANAGE_TEAMS = "manage:teams"
    VIEW_TEAMS = "view:teams"

    # Mess karyawan (Master V2)
    MANAGE_MESS = "manage:mess"
    VIEW_MESS = "view:mess"
    REVIEW_MESS = "review:mess"  # memutuskan pengajuan hunian: PM (divisinya), OM, HR/GA

    # Offboarding & clearance aset (Master V2)
    MANAGE_OFFBOARDING = "manage:offboarding"
    VIEW_OFFBOARDING = "view:offboarding"

    # Syarat foto pekerjaan (Master V2)
    MANAGE_IMAGE_REQUIREMENTS = "manage:image_requirements"

    # Registry backup sistem (Master V2)
    MANAGE_BACKUPS = "manage:backups"

    # Linimasa
    VIEW_TIMELINE = "view:timeline"

    # Log audit
    VIEW_AUDIT = "view:audit"

    # Tugas terjadwal (cron) yang memicu peringatan — hanya ADMIN
    RUN_SYSTEM_JOBS = "run:system_jobs"


P = Permission

# Setiap karyawan yang login: direktori, dokumen pribadinya sendiri.
BASE_PERMISSIONS: frozenset[Permission] = frozenset({P.VIEW_USERS, P.VIEW_DOCUMENTS, P.UPLOAD_DOCUMENTS})

# Izin tambahan per peran legacy (vms.role_code) - mematuhi dok 03 & test_permissions.py
_ROLE_EXTRA: dict[RoleCode, frozenset[Permission]] = {
    RoleCode.ADMIN: frozenset(Permission) - {Permission.DELETE_ANY},
    RoleCode.OPS: frozenset({
        P.CREATE_PLAN, P.PUBLISH_PLAN, P.REVIEW_OVERTIME, P.VIEW_TIMELINE, P.VIEW_AUDIT,
        P.VIEW_ALL_ATTENDANCE, P.REVIEW_ATTENDANCE,
    }),
    RoleCode.PM: frozenset({
        P.CREATE_PLAN, P.PUBLISH_PLAN, P.VIEW_TIMELINE, P.REVIEW_ATTENDANCE, P.MANAGE_SITES,
    }),
    RoleCode.HR: frozenset({
        P.MANAGE_USERS, P.VERIFY_DOCUMENTS, P.MANAGE_EMPLOYEE_DOCUMENTS,
    }),
    RoleCode.FINANCE: frozenset({
        P.VIEW_ALL_ATTENDANCE, P.REVIEW_ATTENDANCE, P.EXPORT_ATTENDANCE,
        P.REVIEW_OVERTIME, P.MANAGE_SITES,
    }),
    RoleCode.ASSET: frozenset({P.MANAGE_ASSETS}),
    RoleCode.LEADER: frozenset(),
    RoleCode.MEMBER: frozenset(),
}

# Izin tambahan per peran Master Schema V2 (system_role_enum)
_SYSTEM_ROLE_EXTRA: dict[SystemRole, frozenset[Permission]] = {
    SystemRole.SUPER_ADMIN: frozenset(Permission),
    # OM membawahi divisi & PM (docs/35 §2): kelola master kantor dan divisi.
    SystemRole.OPERATIONAL_MANAGER: frozenset({
        P.CREATE_PLAN, P.PUBLISH_PLAN, P.REVIEW_OVERTIME, P.VIEW_ALL_ATTENDANCE,
        P.REVIEW_ATTENDANCE, P.VIEW_TIMELINE, P.VIEW_AUDIT, P.VIEW_TEAMS,
        P.VIEW_MESS, P.REVIEW_MESS, P.VIEW_OFFBOARDING, P.MANAGE_SITES, P.MANAGE_DIVISIONS,
    }),
    # Lokasi proyek PM ada di work_plan_daily (bukan master kantor) — tanpa MANAGE_SITES di V2.
    SystemRole.PROJECT_MANAGER: frozenset({
        P.CREATE_PLAN, P.PUBLISH_PLAN, P.VIEW_TIMELINE, P.REVIEW_ATTENDANCE,
        P.MANAGE_TEAMS, P.VIEW_TEAMS, P.VIEW_MESS, P.REVIEW_MESS, P.VIEW_OFFBOARDING, P.MANAGE_IMAGE_REQUIREMENTS,
    }),
    SystemRole.ADMIN_HR_GA: frozenset({
        P.MANAGE_USERS, P.VERIFY_DOCUMENTS, P.MANAGE_EMPLOYEE_DOCUMENTS, P.MANAGE_ASSETS,
        P.MANAGE_MESS, P.VIEW_MESS, P.REVIEW_MESS, P.MANAGE_OFFBOARDING, P.VIEW_OFFBOARDING, P.VIEW_TEAMS,
    }),
    # Finance melihat & mengekspor absensi seluruh karyawan dan meninjau lembur (sama seperti FINANCE V1).
    SystemRole.FINANCE: frozenset({
        P.VIEW_ALL_ATTENDANCE, P.REVIEW_ATTENDANCE, P.EXPORT_ATTENDANCE, P.REVIEW_OVERTIME, P.MANAGE_SITES,
    }),
    SystemRole.TEAM_LEADER: frozenset(),
    SystemRole.EMPLOYEE: frozenset(),
}


def permissions_for_roles(roles: Iterable[str]) -> list[str]:
    """Gabungan izin dari beberapa peran global. Peran tak dikenal diabaikan."""
    granted: set[Permission] = set()
    for role in roles:
        if role == NO_GLOBAL_ROLE:
            granted |= BASE_PERMISSIONS
        elif role in RoleCode.__members__:
            granted |= BASE_PERMISSIONS | _ROLE_EXTRA[RoleCode(role)]
        elif role in SystemRole.__members__:
            granted |= BASE_PERMISSIONS | _SYSTEM_ROLE_EXTRA[SystemRole(role)]
    return sorted(p.value for p in granted)


def get_role_permissions(role: str) -> list[str]:
    return permissions_for_roles([role])
