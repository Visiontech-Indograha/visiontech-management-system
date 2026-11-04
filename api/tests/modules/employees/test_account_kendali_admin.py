"""
Kendali admin atas akun karyawan (HR/admin, izin manage:users): daftar & cabut sesi perangkat, paksa keluar
semua, reset slot perangkat, buka kunci akun terkunci, ganti email login. Setiap aksi tercatat di audit.
Karyawan biasa (tanpa manage:users) → 403.
"""
from __future__ import annotations

import uuid

from tests.conftest import World, requires_db, sync_query

pytestmark = requires_db


def _new_employee(client, world: World, no: str) -> str:
    r = client.post("/employees", headers=world.headers(client, "hr"), json={
        "employee_no": no, "full_name": f"Karyawan {no}", "office_id": world.org_id,
        "division_id": world.unit_id or None, "join_date": "2026-01-05"})
    assert r.status_code == 201, r.text
    return r.json()["employee_id"]


def _audit_count(action: str, entity_id: str) -> int:
    return int(sync_query(
        "SELECT count(*) FROM app_activity_logs WHERE entity_id = %s AND action = %s", (entity_id, action))[0][0])


def _user_id(client, hr: dict, emp: str) -> str:
    """Audit aksi akun memakai entity_type `users` dengan id akun (user_id), bukan id karyawan."""
    return client.get(f"/employees/{emp}/account", headers=hr).json()["user_id"]


def test_field_account_sessions_can_be_listed_revoked_and_reset_by_hr(client, world: World):
    hr = world.headers(client, "hr")
    emp = _new_employee(client, world, f"KA-{world.tag}-1")
    login = f"sesi.{world.tag}@contoh.id"
    temp = client.post(f"/employees/{emp}/account", headers=hr, json={"login": login}).json()["temporary_password"]
    assert client.post("/auth/login", json={"email": login, "password": temp, "platform": "mobile"}).status_code == 200

    sessions = client.get(f"/employees/{emp}/account/sessions", headers=hr)
    assert sessions.status_code == 200, sessions.text
    rows = sessions.json()
    assert len(rows) >= 1 and all(row["current"] is False for row in rows)

    uid = _user_id(client, hr, emp)
    one = client.post(f"/employees/{emp}/account/sessions/{rows[0]['id']}/revoke", headers=hr)
    assert one.status_code == 200 and one.json() == {"revoked": 1}
    assert _audit_count("SESSION_REVOKE", uid) == 1

    assert client.post(f"/employees/{emp}/account/device-slots/reset", headers=hr).status_code == 200
    assert client.get(f"/employees/{emp}/account/sessions", headers=hr).json() == []
    assert _audit_count("DEVICE_SLOTS_RESET", uid) == 1


def test_revoke_all_and_unknown_session_is_404(client, world: World):
    hr = world.headers(client, "hr")
    emp = _new_employee(client, world, f"KA-{world.tag}-2")
    assert client.post(f"/employees/{emp}/account/sessions/revoke-all", headers=hr).status_code == 404  # tanpa akun

    client.post(f"/employees/{emp}/account", headers=hr, json={"login": f"kosong.{world.tag}@contoh.id"})
    stray = str(uuid.uuid4())
    assert client.post(f"/employees/{emp}/account/sessions/{stray}/revoke", headers=hr).status_code == 404
    everyone = client.post(f"/employees/{emp}/account/sessions/revoke-all", headers=hr)
    assert everyone.status_code == 200 and everyone.json()["revoked"] == 0


def test_hr_unlocks_locked_account(client, world: World):
    hr = world.headers(client, "hr")
    emp = _new_employee(client, world, f"KA-{world.tag}-3")
    login = f"kunci.{world.tag}@contoh.id"
    client.post(f"/employees/{emp}/account", headers=hr, json={"login": login})
    for _ in range(5):
        client.post("/auth/login", json={"email": login, "password": "salah-sekali"})
    assert client.get(f"/employees/{emp}/account", headers=hr).json()["locked_until"] is not None

    unlocked = client.post(f"/employees/{emp}/account/unlock", headers=hr)
    assert unlocked.status_code == 200, unlocked.text
    body = unlocked.json()
    assert body["locked_until"] is None and body["failed_logins"] == 0
    assert _audit_count("ACCOUNT_UNLOCK", _user_id(client, hr, emp)) == 1


def test_hr_changes_login_email_unique_and_revokes_old_sessions(client, world: World):
    hr = world.headers(client, "hr")
    emp = _new_employee(client, world, f"KA-{world.tag}-4")
    old = f"lama.{world.tag}@contoh.id"
    new = f"baru.{world.tag}@contoh.id"
    temp = client.post(f"/employees/{emp}/account", headers=hr, json={"login": old}).json()["temporary_password"]
    assert client.post("/auth/login", json={"email": old, "password": temp, "platform": "mobile"}).status_code == 200

    taken = client.post(f"/employees/{emp}/account/login", headers=hr, json={"login": world.logins["member"]})
    assert taken.status_code == 409 and taken.json()["error"]["code"] == "LOGIN_TAKEN"
    assert client.post(f"/employees/{emp}/account/login", headers=hr, json={"login": "bukan-email"}).status_code == 422

    changed = client.post(f"/employees/{emp}/account/login", headers=hr, json={"login": new})
    assert changed.status_code == 200, changed.text
    assert changed.json()["login"] == new
    assert client.get(f"/employees/{emp}/account/sessions", headers=hr).json() == []
    assert client.post("/auth/login", json={"email": old, "password": temp, "platform": "mobile"}).status_code == 400
    assert _audit_count("ACCOUNT_LOGIN_CHANGE", _user_id(client, hr, emp)) == 1


def test_face_status_and_reset_are_audited(client, world: World):
    hr = world.headers(client, "hr")
    emp = _new_employee(client, world, f"KA-{world.tag}-5")
    status = client.get(f"/face/enrollments/{emp}/status", headers=hr)
    assert status.status_code == 200, status.text
    assert status.json()["enrolled"] is False

    reset = client.delete(f"/face/enrollments/{emp}", headers=hr)
    assert reset.status_code == 200, reset.text
    assert _audit_count("FACE_RESET", emp) == 1


def test_regular_employee_cannot_manage_sessions_or_unlock(client, world: World):
    member = world.headers(client, "member")
    emp = _new_employee(client, world, f"KA-{world.tag}-6")
    assert client.get(f"/employees/{emp}/account/sessions", headers=member).status_code == 403
    assert client.post(f"/employees/{emp}/account/unlock", headers=member).status_code == 403
    assert client.get(f"/face/enrollments/{emp}/status", headers=member).status_code == 403
