"""
/auth/me mengirim employee_id — dibutuhkan web untuk "Berkas saya" (GET /employees/{employee_id}/documents);
akun tanpa data karyawan (mis. admin awal) → null.
"""
from __future__ import annotations

from tests.conftest import World, requires_db

pytestmark = requires_db


def test_me_carries_the_employee_id_of_the_account(client, world: World):
    me = client.get("/auth/me", headers=world.headers(client, "member"))

    assert me.status_code == 200, me.text
    assert me.json()["employee_id"] == world.employees["member"]


def test_me_employee_id_is_null_without_employee(client, seeded_user):
    access = client.post("/auth/login", json={"email": seeded_user.login, "password": seeded_user.password}).json()
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {access['access_token']}"})

    assert me.status_code == 200, me.text
    assert "employee_id" in me.json()


def test_me_carries_the_home_office_of_the_employee(client, world: World):
    me = client.get("/auth/me", headers=world.headers(client, "member")).json()

    assert me["office_id"] == world.org_id
    assert me["office_name"]


def test_me_office_is_null_without_employee(client, seeded_user):
    from tests.conftest import sync_query

    access = client.post("/auth/login", json={"email": seeded_user.login, "password": seeded_user.password}).json()
    sync_query("UPDATE users SET employee_id = NULL WHERE user_id = %s", (seeded_user.user_id,))
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {access['access_token']}"}).json()

    assert me["office_id"] is None
    assert me["office_name"] is None
