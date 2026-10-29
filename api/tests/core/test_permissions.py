"""
T-03 · Satu sumber peran + peta izin (Master Schema V2, docs/35 §1–§2).
Kode peran Python (`SystemRole`) harus identik dengan enum `system_role_enum`; izin per peran tetap.
"""
from __future__ import annotations

import uuid

import pytest

from app.core.permissions import BASE_PERMISSIONS, NO_GLOBAL_ROLE, Permission, SystemRole, get_role_permissions
from tests.conftest import login_headers, requires_db, sync_query

P = Permission

EXPECTED_EXTRA: dict[SystemRole, set[Permission]] = {
    # OM membawahi divisi & PM: kelola master kantor dan divisi, lihat & tinjau semua absensi.
    SystemRole.OPERATIONAL_MANAGER: {
        P.CREATE_PLAN, P.PUBLISH_PLAN, P.REVIEW_OVERTIME, P.VIEW_ALL_ATTENDANCE, P.REVIEW_ATTENDANCE,
        P.VIEW_TIMELINE, P.VIEW_AUDIT, P.VIEW_TEAMS, P.VIEW_MESS, P.REVIEW_MESS, P.VIEW_OFFBOARDING, P.MANAGE_SITES,
        P.MANAGE_DIVISIONS,
    },
    # Lokasi proyek PM ada di jadwal harian (bukan master kantor) — tanpa MANAGE_SITES.
    SystemRole.PROJECT_MANAGER: {
        P.CREATE_PLAN, P.PUBLISH_PLAN, P.VIEW_TIMELINE, P.REVIEW_ATTENDANCE, P.MANAGE_TEAMS, P.VIEW_TEAMS,
        P.VIEW_MESS, P.REVIEW_MESS, P.VIEW_OFFBOARDING, P.MANAGE_IMAGE_REQUIREMENTS,
    },
    # Admin HR/GA = HR + aset + mess + proses keluar (FINANCE/ASSET V1 digabung ke sini).
    SystemRole.ADMIN_HR_GA: {
        P.MANAGE_USERS, P.VERIFY_DOCUMENTS, P.MANAGE_EMPLOYEE_DOCUMENTS, P.MANAGE_ASSETS, P.MANAGE_MESS,
        P.VIEW_MESS, P.REVIEW_MESS, P.MANAGE_OFFBOARDING, P.VIEW_OFFBOARDING, P.VIEW_TEAMS, P.VIEW_ALL_ATTENDANCE,
    },
    # Finance melihat, meninjau, dan mengekspor absensi seluruh karyawan; lembur; kelola kantor (sama V1).
    SystemRole.FINANCE: {
        P.VIEW_ALL_ATTENDANCE, P.REVIEW_ATTENDANCE, P.EXPORT_ATTENDANCE, P.REVIEW_OVERTIME, P.MANAGE_SITES,
    },
    # Ketua/anggota tim mendapat wewenangnya dari keanggotaan tim, bukan peran global.
    SystemRole.TEAM_LEADER: set(),
    SystemRole.EMPLOYEE: set(),
}


@requires_db
def test_system_roles_match_database_enum():
    (labels,) = sync_query("SELECT enum_range(NULL::system_role_enum)::text[]")[0]

    assert [r.value for r in SystemRole] == list(labels)


def test_super_admin_has_every_permission():
    assert set(get_role_permissions(SystemRole.SUPER_ADMIN)) == {p.value for p in Permission}


@pytest.mark.parametrize("role", list(EXPECTED_EXTRA))
def test_role_permissions_are_fixed(role: SystemRole):
    expected = {p.value for p in BASE_PERMISSIONS | EXPECTED_EXTRA[role]}

    assert set(get_role_permissions(role)) == expected


def test_user_without_global_role_gets_base_permissions_only():
    assert set(get_role_permissions(NO_GLOBAL_ROLE)) == {p.value for p in BASE_PERMISSIONS}


@pytest.mark.parametrize("role", ["admin", "hr", "SUPERADMIN", ""])
def test_unknown_role_gets_no_permissions(role: str):
    assert get_role_permissions(role) == []


def test_finance_may_export_attendance_but_hr_may_not():
    assert P.EXPORT_ATTENDANCE.value in get_role_permissions(SystemRole.FINANCE)
    assert P.EXPORT_ATTENDANCE.value not in get_role_permissions(SystemRole.ADMIN_HR_GA)


def test_only_hr_and_admin_may_touch_other_peoples_documents():
    holders = {r for r in SystemRole if P.MANAGE_EMPLOYEE_DOCUMENTS.value in get_role_permissions(r)}

    assert holders == {SystemRole.ADMIN_HR_GA, SystemRole.SUPER_ADMIN}


@requires_db
def test_admin_reaches_permission_protected_endpoint(client, make_user):
    response = client.get("/audit-events", headers=login_headers(client, make_user("ADMIN")))

    assert response.status_code == 200, response.text


@requires_db
@pytest.mark.parametrize("role", ["PM", "OPS", "LEADER", None])
def test_other_peoples_documents_are_hidden_as_404(client, make_user, role):
    """Dokumen pribadi hanya pemilik & HR; yang lain 404, bukan 403."""
    response = client.get(
        f"/employees/{uuid.uuid4()}/documents", headers=login_headers(client, make_user(role))
    )

    assert response.status_code == 404, response.text


@requires_db
def test_hr_gets_404_for_an_unknown_employee(client, make_user):
    response = client.get(f"/employees/{uuid.uuid4()}/documents", headers=login_headers(client, make_user("HR")))

    assert response.status_code == 404, response.text
