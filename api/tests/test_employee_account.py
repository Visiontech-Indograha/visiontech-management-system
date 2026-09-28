"""
R-20 · M1-01 — akun login karyawan dikelola dari aplikasi (dulu hanya lewat CLI create-admin).
HR/admin (manage:users): buat akun (password sementara ditampilkan sekali), reset password,
nonaktifkan (sesi dicabut) & aktifkan kembali. Karyawan organisasi lain → 404.
"""
from __future__ import annotations

from tests.conftest import World, requires_db, sync_query

pytestmark = requires_db


def _new_employee(client, world: World, no: str) -> str:
    r = client.post("/employees", headers=world.headers(client, "hr"), json={
        "employee_no": no, "full_name": f"Karyawan {no}", "position": "Teknisi",
        "unit_id": world.unit_id, "join_date": "2026-01-05"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_hr_creates_account_and_employee_can_log_in(client, world: World):
    hr = world.headers(client, "hr")
    emp = _new_employee(client, world, f"AK-{world.tag}-1")
    assert client.get(f"/employees/{emp}/account", headers=hr).json()["exists"] is False

    login = f"akun.{world.tag}@contoh.id"
    made = client.post(f"/employees/{emp}/account", headers=hr, json={"login": login})
    assert made.status_code == 201, made.text
    temp = made.json()["temporary_password"]
    assert len(temp) >= 10

    state = client.get(f"/employees/{emp}/account", headers=hr).json()
    assert (state["exists"], state["login"], state["is_active"]) == (True, login, True)
    assert client.post("/auth/login", json={"email": login, "password": temp}).status_code == 200

    again = client.post(f"/employees/{emp}/account", headers=hr, json={"login": f"lain.{world.tag}@contoh.id"})
    assert again.status_code == 409 and again.json()["error"]["code"] == "ACCOUNT_EXISTS"


def test_login_must_be_unique_and_valid(client, world: World):
    hr = world.headers(client, "hr")
    taken = world.logins["member"]
    emp = _new_employee(client, world, f"AK-{world.tag}-2")
    dup = client.post(f"/employees/{emp}/account", headers=hr, json={"login": taken})
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "LOGIN_TAKEN"
    assert client.post(f"/employees/{emp}/account", headers=hr, json={"login": "bukan-email"}).status_code == 422


def test_deactivate_revokes_access_and_reset_issues_new_password(client, world: World):
    hr = world.headers(client, "hr")
    emp = _new_employee(client, world, f"AK-{world.tag}-3")
    login = f"nonaktif.{world.tag}@contoh.id"
    temp = client.post(f"/employees/{emp}/account", headers=hr, json={"login": login}).json()["temporary_password"]
    token = client.post("/auth/login", json={"email": login, "password": temp}).json()["access_token"]

    assert client.post(f"/employees/{emp}/account/deactivate", headers=hr).status_code == 200
    assert client.post("/auth/login", json={"email": login, "password": temp}).status_code == 403
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    uid = sync_query("SELECT id FROM vms.app_user WHERE employee_id = %s", (emp,))[0][0]
    assert sync_query("SELECT count(*) FROM vms.user_session WHERE user_id = %s AND revoked_at IS NULL", (uid,)) == [(0,)]

    assert client.post(f"/employees/{emp}/account/activate", headers=hr).status_code == 200
    fresh = client.post(f"/employees/{emp}/account/reset-password", headers=hr)
    assert fresh.status_code == 200, fresh.text
    new = fresh.json()["temporary_password"]
    assert client.post("/auth/login", json={"email": login, "password": temp}).status_code != 200
    assert client.post("/auth/login", json={"email": login, "password": new}).status_code == 200


def test_only_account_managers_in_the_same_organisation(client, world: World, other_world: World):
    emp = _new_employee(client, world, f"AK-{world.tag}-4")
    assert client.get(f"/employees/{emp}/account", headers=world.headers(client, "leader")).status_code == 403
    outsider = other_world.headers(client, "hr")
    assert client.get(f"/employees/{emp}/account", headers=outsider).status_code == 404
    assert client.post(f"/employees/{emp}/account", headers=outsider,
                       json={"login": f"x.{world.tag}@contoh.id"}).status_code == 404


def test_account_shows_failed_logins_and_lock(client, world: World):
    """R-21: HR melihat penanda akun yang gagal login & kapan kuncinya lepas."""
    hr = world.headers(client, "hr")
    emp = _new_employee(client, world, f"AK-{world.tag}-5")
    login = f"gagal.{world.tag}@contoh.id"
    client.post(f"/employees/{emp}/account", headers=hr, json={"login": login})

    for _ in range(2):
        client.post("/auth/login", json={"email": login, "password": "salah-sekali"})
    state = client.get(f"/employees/{emp}/account", headers=hr).json()
    assert (state["failed_logins"], state["locked_until"]) == (2, None)

    for _ in range(3):
        client.post("/auth/login", json={"email": login, "password": "salah-sekali"})
    state = client.get(f"/employees/{emp}/account", headers=hr).json()
    assert state["failed_logins"] == 5 and state["locked_until"] is not None
