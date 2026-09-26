"""
T-03 · Satu sumber peran + peta izin (dok 03 §1, dok 08).
Kode peran Python harus identik dengan enum `vms.role_code`; izin per peran mengikuti dok 03,
kecuali OPS yang mengikuti `prototype/js/domain.js` `permissions.OPS` (V-07, dok 10 Bagian C).
"""
from __future__ import annotations

import uuid

import pytest

from app.core.permissions import BASE_PERMISSIONS, NO_GLOBAL_ROLE, Permission, RoleCode, get_role_permissions
from tests.conftest import login_headers, requires_db, sync_query

P = Permission

EXPECTED_EXTRA: dict[RoleCode, set[Permission]] = {
    # R-10: PM/OPS memeriksa absensi unitnya; Finance/Admin seluruh organisasi.
    RoleCode.PM: {P.CREATE_PLAN, P.PUBLISH_PLAN, P.VIEW_TIMELINE, P.REVIEW_UNIT_ATTENDANCE},
    RoleCode.HR: {P.MANAGE_USERS, P.VERIFY_DOCUMENTS, P.MANAGE_EMPLOYEE_DOCUMENTS},
    RoleCode.FINANCE: {P.REVIEW_ATTENDANCE, P.REVIEW_UNIT_ATTENDANCE, P.REVIEW_OVERTIME},
    RoleCode.ASSET: {P.MANAGE_ASSETS},
    # OPS memegang kewenangan PM lintas unit (domain.js permissions.OPS) di samping pemantauan.
    RoleCode.OPS: {P.CREATE_PLAN, P.PUBLISH_PLAN, P.REVIEW_OVERTIME, P.VIEW_TIMELINE, P.VIEW_AUDIT,
                   P.REVIEW_UNIT_ATTENDANCE},
    # Ketua/anggota berasal dari SK (is_plan_leader/is_plan_member), bukan peran global.
    RoleCode.LEADER: set(),
    RoleCode.MEMBER: set(),
}


@requires_db
def test_role_codes_match_database_enum():
    (labels,) = sync_query("SELECT enum_range(NULL::vms.role_code)::text[]")[0]

    assert {r.value for r in RoleCode} == set(labels)


def test_admin_has_every_permission():
    assert set(get_role_permissions(RoleCode.ADMIN)) == {p.value for p in Permission}


@pytest.mark.parametrize("role", list(EXPECTED_EXTRA))
def test_role_permissions_follow_doc_03(role: RoleCode):
    expected = {p.value for p in BASE_PERMISSIONS | EXPECTED_EXTRA[role]}

    assert set(get_role_permissions(role)) == expected


def test_user_without_global_role_gets_base_permissions_only():
    assert set(get_role_permissions(NO_GLOBAL_ROLE)) == {p.value for p in BASE_PERMISSIONS}


@pytest.mark.parametrize("role", ["admin", "hr", "SUPERADMIN", ""])
def test_unknown_role_gets_no_permissions(role: str):
    assert get_role_permissions(role) == []


def test_only_hr_and_admin_may_touch_other_peoples_documents():
    holders = {r for r in RoleCode if P.MANAGE_EMPLOYEE_DOCUMENTS.value in get_role_permissions(r)}

    assert holders == {RoleCode.HR, RoleCode.ADMIN}


@requires_db
def test_admin_reaches_permission_protected_endpoint(client, make_user):
    response = client.get("/audit-events", headers=login_headers(client, make_user("ADMIN")))

    assert response.status_code == 200, response.text


@requires_db
@pytest.mark.parametrize("role", ["PM", "OPS", "FINANCE", "ASSET", None])
def test_other_peoples_documents_are_hidden_as_404(client, make_user, role):
    """Dok 08: dokumen pribadi hanya pemilik & HR; yang lain 404, bukan 403."""
    response = client.get(
        f"/employees/{uuid.uuid4()}/documents", headers=login_headers(client, make_user(role))
    )

    assert response.status_code == 404, response.text


@requires_db
def test_hr_may_list_any_employee_documents(client, make_user):
    response = client.get(f"/employees/{uuid.uuid4()}/documents", headers=login_headers(client, make_user("HR")))

    assert response.status_code == 200, response.text
