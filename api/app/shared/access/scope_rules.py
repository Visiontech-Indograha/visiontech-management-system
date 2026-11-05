"""
app/shared/access/scope_rules.py
Cakupan data per peran untuk daftar & detail (kebocoran akses, audit 2026-11).

Dua lapis:
- keputusan Python (`sees_all_*`, `is_pm`): siapa yang melihat seluruh data;
- predikat SQL (`*_visible_sql`): baris yang boleh dilihat pengguna lain, dengan pola yang sama seperti
  `access_service` (divisi PM/OM, ketua/anggota tim) dan `pm_reach` (jangkauan PM atas karyawan).

Yang tak terlihat → 404 pada detail dan dikeluarkan dari daftar (keberadaannya tidak dibocorkan).
Semua nilai pengguna masuk sebagai parameter terikat (`:viewer_emp`, `:pm`); fragmen SQL di sini konstan.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Permission, SystemRole
from app.core.repository import BaseRepository
from app.core.security import CurrentUser
from app.shared.access.office_scope import office_restriction, offices_param
from app.shared.access.pm_reach import pm_reaches_employee

_VIEWER = "CAST(:viewer_emp AS uuid)"

# Izin yang memberi pandangan direktori karyawan seluruh organisasi (tanpa kolom sensitif kecuali di bawah).
# Finance (VIEW_ALL_ATTENDANCE) dan HSE (VIEW_HSE_CAMPAIGNS) sengaja tidak termasuk: data uang makan/lembur dan
# absensi mereka dibaca lewat endpoint absensi/lembur sendiri yang memakai cakupannya masing-masing.
_DIRECTORY_ALL_PERMS = (
    Permission.MANAGE_USERS,
    Permission.MANAGE_ASSETS,
    Permission.MANAGE_DIVISIONS,
)


def _has_perm(user: CurrentUser, perm: Permission) -> bool:
    return perm.value in user.permissions


def is_pm(user: CurrentUser) -> bool:
    """PM (peran sistem V2 atau kode peran V1 `PM`)."""
    return user.has_role(SystemRole.PROJECT_MANAGER, "PM")


def sees_all_employees(user: CurrentUser) -> bool:
    """Direktori karyawan seluruh organisasi: SA, OM (dan V1 OPS), HR, serta pengelola aset dan divisi."""
    return user.has_role(SystemRole.SUPER_ADMIN, SystemRole.OPERATIONAL_MANAGER, "OPS") or any(
        _has_perm(user, p) for p in _DIRECTORY_ALL_PERMS
    )


def sees_sensitive_employee_fields(user: CurrentUser) -> bool:
    """Kolom sensitif karyawan lain (kontak, alamat, PKWT, peran sistem): HR/OM/SA."""
    return user.has_role(SystemRole.SUPER_ADMIN, SystemRole.OPERATIONAL_MANAGER) or _has_perm(
        user, Permission.MANAGE_USERS
    )


def sees_all_assets(user: CurrentUser) -> bool:
    """Inventaris aset seluruh kantor: SA, OM, dan pengelola aset (MANAGE_ASSETS: ASSET, HR/GA)."""
    return user.has_role(SystemRole.SUPER_ADMIN, SystemRole.OPERATIONAL_MANAGER) or _has_perm(
        user, Permission.MANAGE_ASSETS
    )


def sees_all_work_orders(user: CurrentUser) -> bool:
    """Work order seluruh organisasi: SA, OM (dan peran V1 ADMIN/OPS yang setara)."""
    return user.has_role(SystemRole.SUPER_ADMIN, SystemRole.OPERATIONAL_MANAGER, "ADMIN", "OPS")


def viewer_params(user: CurrentUser) -> dict[str, Any]:
    """Parameter terikat yang dipakai predikat SQL di bawah."""
    return {"viewer_emp": user.employee_id or None, "pm": is_pm(user)}


# ── Karyawan ────────────────────────────────────────────────────────────────────

def employee_visible_sql(emp: str) -> str:
    """Karyawan `emp` terlihat oleh pengguna: dirinya, sesama divisi, sesama tim (ketua/anggota), atau jangkauan PM."""
    return f"""(
        {emp} = {_VIEWER}
        OR EXISTS (
            SELECT 1 FROM employee ve
            WHERE ve.employee_id = {_VIEWER} AND ve.division_id IS NOT NULL
              AND ve.division_id = (SELECT x.division_id FROM employee x WHERE x.employee_id = {emp})
        )
        OR EXISTS (
            SELECT 1 FROM team tm
            WHERE (tm.leader_employee_id = {_VIEWER} OR EXISTS (
                      SELECT 1 FROM member mv WHERE mv.team_id = tm.team_id AND mv.employee_id = {_VIEWER}
                        AND mv.is_active AND mv.delete_at IS NULL))
              AND (tm.leader_employee_id = {emp} OR EXISTS (
                      SELECT 1 FROM member mt WHERE mt.team_id = tm.team_id AND mt.employee_id = {emp}
                        AND mt.is_active AND mt.delete_at IS NULL))
        )
        OR (CAST(:pm AS boolean) AND {pm_reaches_employee(_VIEWER, emp)})
    )"""


def employee_sensitive_sql(emp: str) -> str:
    """Kolom sensitif karyawan `emp` boleh dilihat: SA/OM/HR (`:sens_all`), dirinya, atau PM yang menjangkaunya."""
    return f"""(
        CAST(:sens_all AS boolean) OR {emp} = {_VIEWER}
        OR (SELECT x.office_id FROM employee x WHERE x.employee_id = {emp}) = ANY(CAST(:sens_offices AS uuid[]))
        OR (CAST(:pm AS boolean) AND {pm_reaches_employee(_VIEWER, emp)})
    )"""


def employee_params(user: CurrentUser) -> dict[str, Any]:
    return {
        **viewer_params(user),
        "dir_all": sees_all_employees(user),
        "sens_all": sees_sensitive_employee_fields(user),
    }


async def employee_params_scoped(db: AsyncSession, user: CurrentUser) -> dict[str, Any]:
    """`employee_params` + pembatasan kantor HR/Finance atas kolom sensitif (ADR 0002): izin sensitif yang hanya
    datang dari peran HR berlaku untuk kantor jangkauannya; SA/OM tetap semua. Flag mati = `employee_params`."""
    params = {**employee_params(user), "sens_offices": []}
    if params["sens_all"] and not user.has_role(SystemRole.SUPER_ADMIN, SystemRole.OPERATIONAL_MANAGER):
        restriction = await office_restriction(db, user, Permission.MANAGE_USERS)
        if restriction is not None:
            params["sens_all"] = False
            params["sens_offices"] = offices_param(restriction)
    return params


async def employee_directory_visible(db: AsyncSession, user: CurrentUser, employee_id: UUID | str) -> bool:
    """Apakah satu karyawan terlihat di direktori pengguna (dasar akses foto profil)."""
    if sees_all_employees(user):
        return True
    row = await BaseRepository(db).scalar(
        f"SELECT EXISTS (SELECT 1 FROM employee e WHERE e.employee_id = CAST(:target AS uuid) "
        f"AND {employee_visible_sql('e.employee_id')})",
        {**viewer_params(user), "target": str(employee_id)},
    )
    return bool(row)


# ── Aset (alat & kendaraan) ─────────────────────────────────────────────────────

def asset_visible_sql(div: str, office: str, holder: str) -> str:
    """Aset terlihat: dipegang pengguna, divisinya dipimpin/dikelola pengguna (PM/OM), di divisi pengguna,
    aset umum (tanpa divisi) di kantor pengguna, atau dipegang karyawan yang dijangkau PM."""
    return f"""(
        {holder} = {_VIEWER}
        OR {div} IN (SELECT d.division_id FROM division d
                     WHERE d.delete_at IS NULL AND (d.pm_id = {_VIEWER} OR d.om_id = {_VIEWER}))
        OR ({div} IS NOT NULL AND {div} = (SELECT x.division_id FROM employee x WHERE x.employee_id = {_VIEWER}))
        OR ({div} IS NULL AND {office} = (SELECT x.office_id FROM employee x WHERE x.employee_id = {_VIEWER}))
        OR (CAST(:pm AS boolean) AND {holder} IS NOT NULL AND {pm_reaches_employee(_VIEWER, holder)})
    )"""


def open_holder_sql(asset_col: str, asset_ref: str) -> str:
    """Pemegang saat ini (peminjaman berjalan) untuk aset `asset_ref` pada kolom `asset_col` (tool_id/vehicle_id)."""
    return (
        f"(SELECT x.employee_id FROM asset_assignment x WHERE x.{asset_col} = {asset_ref} "
        f"AND x.returned_at IS NULL AND x.delete_at IS NULL ORDER BY x.loaned_at DESC LIMIT 1)"
    )


def asset_viewer(user: CurrentUser) -> dict[str, Any] | None:
    """Parameter cakupan aset; None = seluruh inventaris (SA/OM/pengelola aset)."""
    return None if sees_all_assets(user) else viewer_params(user)


def vehicle_scope_sql(alias: str = "v") -> str:
    """Predikat kendaraan `alias` terlihat (dipakai ulang di daftar ketersediaan)."""
    holder = open_holder_sql("vehicle_id", f"{alias}.vehicle_id")
    return asset_visible_sql(f"{alias}.division_id", f"{alias}.office_id", holder)


def tool_scope_sql(alias: str = "t") -> str:
    """Predikat alat `alias` terlihat (dipakai ulang di daftar ketersediaan)."""
    holder = open_holder_sql("tool_id", f"{alias}.tool_id")
    return asset_visible_sql(f"{alias}.division_id", f"{alias}.office_id", holder)


async def vehicle_visible(db: AsyncSession, user: CurrentUser, vehicle_id: UUID | str) -> bool:
    """Kendaraan terlihat oleh pengguna (dasar berkas & riwayat inspeksi kendaraan)."""
    if sees_all_assets(user):
        return True
    row = await BaseRepository(db).scalar(
        f"SELECT EXISTS (SELECT 1 FROM vehicle v WHERE v.vehicle_id = CAST(:vid AS uuid) AND v.delete_at IS NULL "
        f"AND {vehicle_scope_sql('v')})",
        {**viewer_params(user), "vid": str(vehicle_id)},
    )
    return bool(row)


async def asset_file_visible(db: AsyncSession, storage_key: str, user: CurrentUser) -> bool:
    """Berkas aset (foto alat/kendaraan, berkas & inspeksi kendaraan, foto serah terima) terlihat bila aset
    induknya terlihat oleh pengguna. Foto serah terima juga terlihat untuk pemegangnya sendiri."""
    if sees_all_assets(user):
        return True
    tool_holder = open_holder_sql("tool_id", "t.tool_id")
    veh_holder = open_holder_sql("vehicle_id", "v.vehicle_id")
    tool_ok = asset_visible_sql("t.division_id", "t.office_id", tool_holder)
    veh_ok = asset_visible_sql("v.division_id", "v.office_id", veh_holder)
    tool_by_holder = asset_visible_sql("t.division_id", "t.office_id", "aa.employee_id")
    veh_by_holder = asset_visible_sql("v.division_id", "v.office_id", "aa.employee_id")
    row = await BaseRepository(db).scalar(
        f"""
        SELECT (
            EXISTS (SELECT 1 FROM tool t WHERE t.photo_path = :key AND t.delete_at IS NULL AND {tool_ok})
            OR EXISTS (SELECT 1 FROM vehicle v WHERE v.photo_path = :key AND v.delete_at IS NULL AND {veh_ok})
            OR EXISTS (SELECT 1 FROM vehicle_file vf JOIN vehicle v ON v.vehicle_id = vf.vehicle_id
                       WHERE vf.path_file = :key AND {veh_ok})
            OR EXISTS (SELECT 1 FROM vehicle_inspection vi JOIN vehicle v ON v.vehicle_id = vi.vehicle_id
                       WHERE vi.path_file = :key AND {veh_ok})
            OR EXISTS (SELECT 1 FROM asset_assignment aa
                       WHERE aa.handover_photo_path = :key AND aa.employee_id = {_VIEWER})
            OR EXISTS (SELECT 1 FROM asset_assignment aa JOIN tool t ON t.tool_id = aa.tool_id
                       WHERE aa.handover_photo_path = :key AND {tool_by_holder})
            OR EXISTS (SELECT 1 FROM asset_assignment aa JOIN vehicle v ON v.vehicle_id = aa.vehicle_id
                       WHERE aa.handover_photo_path = :key AND {veh_by_holder})
        )
        """,
        {**viewer_params(user), "key": storage_key},
    )
    return bool(row)


# ── Work order ──────────────────────────────────────────────────────────────────

def work_order_team_sql(wo: str = "wo") -> str:
    """Pengguna ketua atau anggota aktif tim yang ditugaskan ke WO (`lead_team_id`)."""
    return f"""(
        EXISTS (
            SELECT 1 FROM team tm
            WHERE tm.team_id = {wo}.lead_team_id
              AND (tm.leader_employee_id = {_VIEWER} OR EXISTS (
                      SELECT 1 FROM member mv WHERE mv.team_id = tm.team_id AND mv.employee_id = {_VIEWER}
                        AND mv.is_active AND mv.delete_at IS NULL))
        )
    )"""


def work_order_leader_sql(wo: str = "wo") -> str:
    """Pengguna ketua tim yang ditugaskan ke WO (penandatangan BAST di lapangan)."""
    return f"""(
        EXISTS (
            SELECT 1 FROM team tm
            WHERE tm.team_id = {wo}.lead_team_id AND tm.leader_employee_id = {_VIEWER}
        )
    )"""


def work_order_manage_sql(wo: str = "wo") -> str:
    """Pengelola WO: PM yang mengelola WO itu atau memimpin divisinya (`:pm` = pengguna berperan PM)."""
    return f"""(CAST(:pm AS boolean) AND (
        {wo}.pm_id = {_VIEWER}
        OR {wo}.division_id IN (SELECT d.division_id FROM division d
                                WHERE d.pm_id = {_VIEWER} AND d.delete_at IS NULL)
    ))"""


def work_order_visible_sql(wo: str = "wo") -> str:
    """WO terlihat: tim pengguna (ketua/anggota) ditugaskan ke WO itu; PM (`:pm`) untuk WO yang ia kelola
    atau WO di divisi yang dipimpinnya."""
    return f"({work_order_team_sql(wo)} OR {work_order_manage_sql(wo)})"
