"""
Peran lapangan akun karyawan: HR (ADMIN_HR_GA) dan SUPER_ADMIN memilih EMPLOYEE atau TEAM_LEADER saat membuat akun
dan saat mengubah peran akun lapangan. Nilai lain → 422; peran lain → 403; akun kantor → 409; ketua tim aktif tidak
boleh diturunkan (409). Setiap perubahan tercatat di audit (app_activity_logs).
"""
from __future__ import annotations

import pytest

from tests.conftest import World, requires_db, sync_query

pytestmark = requires_db


def _new_employee(client, world: World, no: str) -> str:
    r = client.post("/employees", headers=world.headers(client, "hr"), json={
        "employee_no": no, "full_name": f"Karyawan {no}", "office_id": world.org_id,
        "division_id": world.unit_id or None, "join_date": "2026-01-05"})
    assert r.status_code == 201, r.text
    return r.json()["employee_id"]


def _create(client, world: World, who: str, emp: str, role: str | None):
    body: dict[str, object] = {"login": f"{who}.{emp[:8]}.{world.tag}@contoh.id"}
    if role is not None:
        body["system_role"] = role
    return client.post(f"/employees/{emp}/account", headers=world.headers(client, who), json=body)


def _set_role(client, world: World, who: str, emp: str, role: str):
    return client.post(f"/employees/{emp}/account/role", headers=world.headers(client, who),
                       json={"system_role": role})


def _role_of(emp: str) -> str:
    return sync_query("SELECT system_role::text FROM users WHERE employee_id = %s", (emp,))[0][0]


@pytest.mark.parametrize("who", ["hr", "admin"])
def test_hr_and_super_admin_create_account_with_field_role(client, world: World, who: str):
    emp = _new_employee(client, world, f"PR-{world.tag}-{who}")
    made = _create(client, world, who, emp, "TEAM_LEADER")
    assert made.status_code == 201, made.text
    assert made.json()["system_role"] == "TEAM_LEADER"
    assert _role_of(emp) == "TEAM_LEADER"
    assert client.get(f"/employees/{emp}/account", headers=world.headers(client, "hr")).json()["system_role"] \
        == "TEAM_LEADER"


def test_account_defaults_to_employee_role(client, world: World):
    emp = _new_employee(client, world, f"PR-{world.tag}-def")
    made = _create(client, world, "hr", emp, None)
    assert made.status_code == 201, made.text
    assert _role_of(emp) == "EMPLOYEE"


@pytest.mark.parametrize("who", ["pm", "ops", "leader", "member"])
def test_other_roles_cannot_create_or_change_field_role(client, world: World, who: str):
    emp = _new_employee(client, world, f"PR-{world.tag}-403-{who}")
    assert _create(client, world, who, emp, "TEAM_LEADER").status_code == 403
    assert sync_query("SELECT count(*) FROM users WHERE employee_id = %s", (emp,)) == [(0,)]

    emp2 = _new_employee(client, world, f"PR-{world.tag}-403b-{who}")
    assert _create(client, world, "hr", emp2, None).status_code == 201
    assert _set_role(client, world, who, emp2, "TEAM_LEADER").status_code == 403
    assert _role_of(emp2) == "EMPLOYEE"


@pytest.mark.parametrize("role", ["PROJECT_MANAGER", "OPERATIONAL_MANAGER", "ADMIN_HR_GA", "FINANCE",
                                  "SUPER_ADMIN", "field", "employee", ""])
def test_only_employee_and_team_leader_are_accepted(client, world: World, role: str):
    emp = _new_employee(client, world, f"PR-{world.tag}-422-{len(role)}")
    assert _create(client, world, "hr", emp, role).status_code == 422
    assert sync_query("SELECT count(*) FROM users WHERE employee_id = %s", (emp,)) == [(0,)]

    emp2 = _new_employee(client, world, f"PR-{world.tag}-422b-{len(role)}")
    assert _create(client, world, "hr", emp2, None).status_code == 201
    assert _set_role(client, world, "hr", emp2, role).status_code == 422
    assert _role_of(emp2) == "EMPLOYEE"


def test_hr_changes_field_role_and_audit_records_it(client, world: World):
    emp = _new_employee(client, world, f"PR-{world.tag}-ubah")
    _create(client, world, "hr", emp, None)
    changed = _set_role(client, world, "hr", emp, "TEAM_LEADER")
    assert changed.status_code == 200, changed.text
    assert changed.json()["system_role"] == "TEAM_LEADER"
    assert _role_of(emp) == "TEAM_LEADER"
    uid = sync_query("SELECT user_id FROM users WHERE employee_id = %s", (emp,))[0][0]
    logs = sync_query(
        "SELECT count(*) FROM app_activity_logs WHERE action = 'ROLE_CHANGE' AND entity_id = %s", (uid,))
    assert logs == [(1,)]


def test_office_account_role_cannot_be_changed_here(client, world: World):
    """Akun peran kantor (mis. PROJECT_MANAGER) bukan peran lapangan: tidak bisa diturunkan/dinaikkan lewat sini."""
    pm_emp = world.employees["pm"]
    assert _set_role(client, world, "hr", pm_emp, "EMPLOYEE").status_code == 409
    assert _set_role(client, world, "hr", pm_emp, "TEAM_LEADER").status_code == 409
    assert _role_of(pm_emp) == "PROJECT_MANAGER"


def test_active_team_leader_cannot_be_demoted(client, world: World):
    leader = world.employees["leader"]
    blocked = _set_role(client, world, "hr", leader, "EMPLOYEE")
    assert blocked.status_code == 409 and blocked.json()["error"]["code"] == "LEADER_ACTIVE_TEAM"
    assert _role_of(leader) == "TEAM_LEADER"
