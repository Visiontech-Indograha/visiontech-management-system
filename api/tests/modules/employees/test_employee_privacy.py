"""
R-20 · M2-01 — kontak pribadi (telepon, email, alamat) hanya untuk pemiliknya dan HR/admin
(dok 08 ancaman "mengintip data rekan"). V2 sempat membuka semuanya ke setiap akun lewat direktori.
"""
from __future__ import annotations

from tests.conftest import World, requires_db, sync_query

pytestmark = requires_db

PRIVATE = ("phone_number", "email", "city")


def _fill(world: World, who: str) -> str:
    emp = world.employees[who]
    sync_query("UPDATE employee SET phone_number = '0812' WHERE employee_id = %s RETURNING 1", (emp,))
    return emp


def _detail(client, world: World, who: str, emp: str) -> dict:
    r = client.get(f"/employees/{emp}", headers=world.headers(client, who))
    assert r.status_code == 200, r.text
    return r.json()


def _listed(client, world: World, who: str, emp: str) -> dict:
    r = client.get("/employees", headers=world.headers(client, who),
                   params={"size": 100, "office_id": world.org_id})
    assert r.status_code == 200, r.text
    return next(e for e in r.json()["items"] if e["employee_id"] == emp)


def test_colleague_sees_no_private_fields(client, world: World):
    emp = _fill(world, "member")
    detail = _detail(client, world, "leader", emp)
    assert detail["addresses"] == []
    for view in (detail, _listed(client, world, "leader", emp)):
        assert all(view[f] is None for f in PRIVATE), view
        assert view["full_name"] and view["office_name"]   # data kerja tetap terlihat


def test_owner_and_hr_see_private_fields(client, world: World):
    emp = _fill(world, "member")
    for who in ("member", "hr", "admin"):
        view = _detail(client, world, who, emp)
        assert view["phone_number"] == "0812" and view["email"] == world.logins["member"], who
        assert _listed(client, world, who, emp)["phone_number"] == "0812", who
