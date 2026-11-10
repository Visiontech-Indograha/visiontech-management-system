"""Wajib ganti sandi: akun baru/reset admin -> 403 MUST_CHANGE_PASSWORD (klien opt-in via X-App-Capabilities) sampai
pengguna mengganti sandinya sendiri. Klien lama (tanpa header) tidak terkunci. /auth/me melaporkan bendera."""
from __future__ import annotations

from tests.conftest import World, requires_db

pytestmark = requires_db

CAP = {"X-App-Capabilities": "must-change-password"}
NEW_PW = "KataSandiBaru-456!"


def _employee(client, world: World, no: str) -> str:
    r = client.post("/employees", headers=world.headers(client, "hr"), json={
        "employee_no": no, "full_name": f"Karyawan {no}", "office_id": world.org_id,
        "division_id": world.unit_id or None, "join_date": "2026-01-05"})
    assert r.status_code == 201, r.text
    return r.json()["employee_id"]


def _login(client, login: str, pw: str) -> dict[str, str]:
    r = client.post("/auth/login", json={"email": login, "password": pw, "platform": "mobile"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _make(client, world: World, tag: str) -> tuple[str, str, str]:
    emp = _employee(client, world, f"MC-{world.tag}-{tag}")
    login = f"mc.{tag}.{world.tag}@contoh.id"
    temp = client.post(f"/employees/{emp}/account", headers=world.headers(client, "hr"),
                       json={"login": login}).json()["temporary_password"]
    return emp, login, temp


def test_created_account_must_change_then_free(client, world: World):
    _, login, temp = _make(client, world, "a")
    h = _login(client, login, temp)
    me = client.get("/auth/me", headers={**h, **CAP})
    assert me.status_code == 200 and me.json()["must_change_password"] is True
    blocked = client.get("/attendance/me/recap", headers={**h, **CAP})
    assert blocked.status_code == 403 and blocked.json()["error"]["code"] == "MUST_CHANGE_PASSWORD"
    assert client.get("/version").status_code == 200
    same = client.post("/auth/change-password", headers={**h, **CAP},
                       json={"current_password": temp, "new_password": temp})
    assert same.status_code == 422
    ok = client.post("/auth/change-password", headers={**h, **CAP},
                     json={"current_password": temp, "new_password": NEW_PW})
    assert ok.status_code == 200, ok.text
    h2 = {"Authorization": f"Bearer {ok.json()['access_token']}"}
    assert client.get("/auth/me", headers={**h2, **CAP}).json()["must_change_password"] is False
    assert client.get("/attendance/me/recap", headers={**h2, **CAP}).status_code != 403


def test_old_client_without_header_is_not_locked(client, world: World):
    _, login, temp = _make(client, world, "b")
    h = _login(client, login, temp)
    assert client.get("/auth/me", headers=h).json()["must_change_password"] is True
    assert client.get("/attendance/me/recap", headers=h).status_code != 403


def test_admin_reset_requires_change_again(client, world: World):
    emp, login, temp = _make(client, world, "c")
    h = _login(client, login, temp)
    client.post("/auth/change-password", headers=h, json={"current_password": temp, "new_password": NEW_PW})
    reset = client.post(f"/employees/{emp}/account/reset-password", headers=world.headers(client, "hr"))
    assert reset.status_code == 200, reset.text
    h3 = _login(client, login, reset.json()["temporary_password"])
    blocked = client.get("/attendance/me/recap", headers={**h3, **CAP})
    assert blocked.status_code == 403 and blocked.json()["error"]["code"] == "MUST_CHANGE_PASSWORD"


def test_seeded_users_are_not_forced(client, world: World):
    h = world.headers(client, "member")
    assert client.get("/auth/me", headers={**h, **CAP}).json()["must_change_password"] is False
