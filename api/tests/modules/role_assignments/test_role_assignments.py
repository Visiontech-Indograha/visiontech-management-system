"""
Peran ganda dan penugasan kantor (ADR 0002 fase 1): aturan kelola penugasan, audit, token lama,
paritas flag mati, dan matriks peran x kantor x endpoint absensi (daftar, rekap, ekspor, swafoto /files).
"""
from __future__ import annotations

import pytest

from app.core.config import settings
from app.core.permissions import Permission, permissions_for_roles
from app.core.time import jakarta_now
from app.modules.role_assignments.services import role_assignment_service as svc
from tests.concurrency import dua_bersamaan
from tests.conftest import World, requires_db, sync_query
from tests.modules.attendance.test_attendance_list import _check_in

pytestmark = requires_db

HR, FIN, OM = "ADMIN_HR_GA", "FINANCE", "OPERATIONAL_MANAGER"


@pytest.fixture
def flag_on(monkeypatch):
    monkeypatch.setattr(settings, "ROLE_ASSIGNMENT_ENABLED", True)


@pytest.fixture
def flag_off(monkeypatch):
    monkeypatch.setattr(settings, "ROLE_ASSIGNMENT_ENABLED", False)


def _assign(client, world: World, who: str, role: str, office: str | None, by: str = "admin",
            extra: dict | None = None):
    return client.post(f"/users/{world.users[who]}/role-assignments",
                       headers={**world.headers(client, by), **(extra or {})},
                       json={"role": role, "office_id": office})


def _sees(client, viewer_world: World, viewer: str, emp_id: str) -> bool:
    r = client.get("/attendance", headers=viewer_world.headers(client, viewer), params={"employee_id": emp_id})
    assert r.status_code == 200, r.text
    return len(r.json()["items"]) > 0


@pytest.fixture
def two(client, world: World, other_world: World, fake_storage):
    """Absensi satu anggota di kantor A (world) dan satu di kantor B (other_world)."""
    _check_in(client, world, "member")
    _check_in(client, other_world, "member")
    return world, other_world


def _vis(client, two, who):
    a, b = two
    return (_sees(client, a, who, a.employees["member"]), _sees(client, a, who, b.employees["member"]))


# ── Kelola penugasan ──────────────────────────────────────────────────────────
def test_permission_only_super_admin():
    assert Permission.MANAGE_ROLE_ASSIGNMENTS.value in permissions_for_roles(["SUPER_ADMIN"])
    for role in (HR, FIN, OM, "PROJECT_MANAGER", "EMPLOYEE"):
        assert Permission.MANAGE_ROLE_ASSIGNMENTS.value not in permissions_for_roles([role])


def test_only_super_admin_can_manage(client, world: World):
    world.add_person("x", None)
    for who in ("hr", "ops", "pm", "member"):
        assert _assign(client, world, "x", HR, world.org_id, by=who).status_code == 403
        r = client.get(f"/users/{world.users['x']}/role-assignments", headers=world.headers(client, who))
        assert r.status_code == 403


def test_add_list_revoke_and_audit(client, world: World):
    world.add_person("x", None)
    r = _assign(client, world, "x", HR, world.org_id)
    assert r.status_code == 201, r.text
    aid = r.json()["assignment_id"]
    assert r.json()["office_id"] == world.org_id and r.json()["role"] == HR
    listed = client.get(f"/users/{world.users['x']}/role-assignments", headers=world.headers(client, "admin"))
    assert [a["assignment_id"] for a in listed.json()] == [aid]
    assert listed.headers.get("X-Total-Count") is None or listed.headers["X-Total-Count"] == "1"
    d = client.delete(f"/users/{world.users['x']}/role-assignments/{aid}", headers=world.headers(client, "admin"))
    assert d.status_code == 204
    assert client.get(f"/users/{world.users['x']}/role-assignments",
                      headers=world.headers(client, "admin")).json() == []
    # cabut dua kali: 404; soft delete lalu tambah ulang boleh
    assert client.delete(f"/users/{world.users['x']}/role-assignments/{aid}",
                         headers=world.headers(client, "admin")).status_code == 404
    assert _assign(client, world, "x", HR, world.org_id).status_code == 201
    actions = [r[0] for r in sync_query(
        "SELECT action FROM app_activity_logs WHERE entity_table = 'users' AND entity_id = %s "
        "AND action LIKE 'ROLE_ASSIGNMENT%%' ORDER BY action", (world.users["x"],))]
    assert actions == ["ROLE_ASSIGNMENT_ADD", "ROLE_ASSIGNMENT_ADD", "ROLE_ASSIGNMENT_REVOKE"]
    row = sync_query("SELECT delete_at, delete_by FROM user_role_assignment WHERE assignment_id = %s", (aid,))[0]
    assert row[0] is not None and str(row[1]) == world.users["admin"]


@pytest.mark.parametrize(("role", "office", "ok"), [
    (HR, None, False),            # HR wajib kantor
    (FIN, None, False),
    (OM, "OFFICE", False),        # OM tanpa kantor
    (OM, None, True),
    ("PROJECT_MANAGER", None, False),   # peran fase 1 saja (ditolak skema/validasi)
])
def test_office_rules(client, world: World, role, office, ok):
    world.add_person("x", None)
    office = world.org_id if office == "OFFICE" else office
    r = _assign(client, world, "x", role, office)
    assert r.status_code == (201 if ok else 422), r.text


def test_forbidden_combinations_and_self(client, world: World):
    world.add_person("hrx", "HR")
    world.add_person("emp", None)
    world.add_person("sa2", "ADMIN")
    r = _assign(client, world, "hrx", FIN, world.org_id)  # HR + Finance dilarang
    assert r.status_code == 422 and "Finance" in r.json()["error"]["message"]
    assert _assign(client, world, "sa2", HR, world.org_id).status_code == 422  # SA tidak digabung
    assert _assign(client, world, "emp", HR, world.org_id).status_code == 201
    assert _assign(client, world, "emp", FIN, world.org_id).status_code == 422  # HR lalu Finance
    assert _assign(client, world, "emp", HR, world.org_id).status_code == 422   # duplikat
    # tidak bisa mengubah diri sendiri
    assert _assign(client, world, "admin", HR, world.org_id).status_code == 422
    assert client.delete(f"/users/{world.users['admin']}/role-assignments/{world.users['admin']}",
                         headers=world.headers(client, "admin")).status_code == 422
    assert _assign(client, world, "emp", HR, "bukan-uuid").status_code == 422
    assert client.get(f"/users/{world.users['admin']}/role-assignments",
                      headers=world.headers(client, "admin")).status_code == 200


def test_max_two_extra_roles(client, world: World, monkeypatch):
    monkeypatch.setattr(svc, "MAX_EXTRA_ROLES", 1)
    world.add_person("x", "PM")
    assert _assign(client, world, "x", OM, None).status_code == 201
    r = _assign(client, world, "x", HR, world.org_id)
    assert r.status_code == 422 and "peran tambahan" in r.json()["error"]["message"]


def test_idempotency_key_replays_without_second_row(client, world: World):
    world.add_person("x", None)
    h = {"Idempotency-Key": "kunci-uji-peran-0001"}
    a = _assign(client, world, "x", HR, world.org_id, extra=h)
    b = _assign(client, world, "x", HR, world.org_id, extra=h)
    assert a.status_code == b.status_code == 201 and a.json() == b.json()
    assert sync_query("SELECT count(*) FROM user_role_assignment WHERE user_id = %s AND delete_at IS NULL",
                      (world.users["x"],))[0][0] == 1


def test_concurrent_conflicting_assignments_only_one_wins(client, world: World):
    """HR dan Finance serentak untuk akun yang sama: kunci baris pengguna membuat tepat satu yang lolos."""
    world.add_person("x", None)
    headers = world.headers(client, "admin")
    role_of = [HR, FIN]

    def aksi(i: int):
        return client.post(f"/users/{world.users['x']}/role-assignments", headers=headers,
                           json={"role": role_of[i], "office_id": world.org_id})

    codes = sorted(r.status_code for r in dua_bersamaan(aksi))
    assert codes == [201, 422]
    assert sync_query("SELECT count(*) FROM user_role_assignment WHERE user_id = %s AND delete_at IS NULL",
                      (world.users["x"],))[0][0] == 1


# ── Izin efektif dan token lama ───────────────────────────────────────────────
def test_flag_off_assignment_changes_nothing(client, world: World, flag_off):
    world.add_person("x", None)
    assert _assign(client, world, "x", OM, None).status_code == 201
    me = client.get("/auth/me", headers=world.headers(client, "x")).json()
    assert Permission.EXPORT_ATTENDANCE.value not in me["permissions"]
    assert me["effective_roles"] == ["EMPLOYEE"] and me["role_scopes"] == []


def test_flag_on_union_permissions_same_token(client, world: World, flag_on):
    world.add_person("x", None)
    headers = world.headers(client, "x")  # token diterbitkan SEBELUM penugasan
    assert client.get("/auth/me", headers=headers).json()["effective_roles"] == ["EMPLOYEE"]
    r = _assign(client, world, "x", OM, None)
    assert r.status_code == 201
    me = client.get("/auth/me", headers=headers).json()
    assert me["role"] == "EMPLOYEE"  # field lama tidak berubah
    assert me["effective_roles"] == ["EMPLOYEE", OM]
    assert Permission.EXPORT_ATTENDANCE.value in me["permissions"]
    assert me["role_scopes"][0]["primary"] is True and me["role_scopes"][1]["role"] == OM
    client.delete(f"/users/{world.users['x']}/role-assignments/{r.json()['assignment_id']}",
                  headers=world.headers(client, "admin"))
    me = client.get("/auth/me", headers=headers).json()  # pencabutan berlaku seketika pada token yang sama
    assert me["effective_roles"] == ["EMPLOYEE"]
    assert Permission.EXPORT_ATTENDANCE.value not in me["permissions"]


# ── Matriks cakupan kantor ────────────────────────────────────────────────────
def test_matrix_primary_roles_no_assignment(client, two, flag_on):
    a, _ = two
    a.add_person("fin", FIN)
    assert _vis(client, two, "hr") == (True, False)
    assert _vis(client, two, "fin") == (True, False)
    assert _vis(client, two, "ops") == (True, True)
    assert _vis(client, two, "admin") == (True, True)
    assert _vis(client, two, "member") == (True, False)  # karyawan: hanya miliknya
    assert _sees(client, a, "member", a.employees["leader"]) is False


@pytest.mark.parametrize("flag", [False, True])
def test_hr_second_office_requires_flag(client, two, monkeypatch, flag):
    monkeypatch.setattr(settings, "ROLE_ASSIGNMENT_ENABLED", flag)
    a, b = two
    assert _assign(client, a, "hr", HR, b.org_id).status_code == 201
    assert _vis(client, two, "hr") == (True, flag)  # flag mati = paritas persis dengan perilaku lama


def test_finance_two_offices_and_revoke_is_immediate(client, two, flag_on):
    a, b = two
    a.add_person("fin", FIN)
    assert _vis(client, two, "fin") == (True, False)
    r = _assign(client, a, "fin", FIN, b.org_id)
    assert r.status_code == 201
    assert _vis(client, two, "fin") == (True, True)
    client.delete(f"/users/{a.users['fin']}/role-assignments/{r.json()['assignment_id']}",
                  headers=a.headers(client, "admin"))
    assert _vis(client, two, "fin") == (True, False)


def test_om_plus_hr_and_employee_plus_hr(client, two, flag_on):
    a, b = two
    a.add_person("omhr", "OPERATIONAL_MANAGER")
    assert _assign(client, a, "omhr", HR, a.org_id).status_code == 201
    assert _vis(client, two, "omhr") == (True, True)  # OM = semua kantor
    a.add_person("emp", None)
    assert _assign(client, a, "emp", HR, b.org_id).status_code == 201
    assert _sees(client, a, "emp", b.employees["member"]) is True
    a.add_person("pmhr", "PM")
    assert _assign(client, a, "pmhr", HR, b.org_id).status_code == 201
    assert _sees(client, a, "pmhr", b.employees["member"]) is True


@pytest.mark.parametrize("flag", [False, True])
def test_acting_om_plus_hr_keeps_current_behaviour(client, two, monkeypatch, flag):
    monkeypatch.setattr(settings, "ROLE_ASSIGNMENT_ENABLED", flag)
    a, _ = two
    sync_query("UPDATE division SET om_id = %s WHERE division_id = %s", (a.employees["hr"], a.unit_id))
    assert _vis(client, two, "hr") == (True, True)


def test_assignment_ignored_when_office_deleted(client, two, flag_on):
    a, b = two
    assert _assign(client, a, "hr", HR, b.org_id).status_code == 201
    sync_query("UPDATE office SET delete_at = now() WHERE office_id = %s", (b.org_id,))
    try:
        assert _sees(client, a, "hr", b.employees["member"]) is False
    finally:
        sync_query("UPDATE office SET delete_at = NULL WHERE office_id = %s", (b.org_id,))


# ── Ekspor, rekap uang makan, swafoto ─────────────────────────────────────────
def _csv(client, who_world: World, who: str):
    today = jakarta_now().date().isoformat()
    return client.get("/attendance/export", headers=who_world.headers(client, who),
                      params={"start_date": today, "end_date": today})


def _emp_no(emp_id: str) -> str:
    return str(sync_query("SELECT employee_no FROM employee WHERE employee_id = %s", (emp_id,))[0][0])


def test_export_meal_recap_and_selfie_follow_scope(client, two, flag_on):
    a, b = two
    a.add_person("fin", FIN)
    no_b = _emp_no(b.employees["member"])
    today = jakarta_now().date().isoformat()
    file_b = sync_query(
        "SELECT f.id::text FROM attendance x JOIN file_object f ON f.storage_key = x.face_photo_path "
        "WHERE x.employee_id = %s", (b.employees["member"],))[0][0]

    fin = a.headers(client, "fin")
    assert no_b not in _csv(client, a, "fin").text
    assert client.get(f"/files/{file_b}/url", headers=fin).status_code == 404

    assert _assign(client, a, "fin", FIN, b.org_id).status_code == 201
    assert no_b in _csv(client, a, "fin").text
    assert client.get(f"/files/{file_b}/url", headers=fin).status_code == 200
    rec = client.get("/attendance/meal-allowance", headers=fin, params={"start_date": today, "end_date": today})
    assert rec.status_code == 200 and no_b in {r["employee_no"] for r in rec.json()}


def test_om_assignment_grants_export_only_with_flag(client, two, monkeypatch):
    a, b = two
    a.add_person("emp", None)
    assert _assign(client, a, "emp", OM, None).status_code == 201
    monkeypatch.setattr(settings, "ROLE_ASSIGNMENT_ENABLED", False)
    assert _csv(client, a, "emp").status_code == 403
    monkeypatch.setattr(settings, "ROLE_ASSIGNMENT_ENABLED", True)
    r = _csv(client, a, "emp")
    assert r.status_code == 200 and _emp_no(b.employees["member"]) in r.text


def test_hr_primary_cannot_export_even_with_second_office(client, two, flag_on):
    a, b = two
    assert _assign(client, a, "hr", HR, b.org_id).status_code == 201
    assert _csv(client, a, "hr").status_code == 403
